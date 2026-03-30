#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════
#  Mesa Virtual — Servidor local  (multi-campanha)
#
#  Endpoints:
#  ── Auth do Mestre ──────────────────────────────────────
#    GET  /api/gm/status            → {hasPassword, authenticated}
#    POST /api/gm/setup             → cria senha (1º uso)
#    POST /api/gm/login             → valida senha → token
#    POST /api/gm/logout            → invalida token
#    POST /api/gm/change            → troca senha
#  ── Campanhas (requer GM token) ─────────────────────────
#    GET  /api/campaigns            → lista todas as campanhas
#    POST /api/campaigns            → cria campanha
#    POST /api/campaigns/{id}/delete  → apaga campanha
#    POST /api/campaigns/{id}/activate → ativa campanha na sessão
#    POST /api/campaigns/{id}/player/add      → adiciona jogador
#    POST /api/campaigns/{id}/player/remove   → remove jogador
#    POST /api/campaigns/{id}/player/password → define senha do jogador
#  ── Lobby público ───────────────────────────────────────
#    GET  /api/lobby/{code}         → info pública da sala (sem senhas)
#  ── Auth do Jogador ─────────────────────────────────────
#    POST /api/player/login         → valida senha → player token
#  ── Dados do jogo ───────────────────────────────────────
#    GET  /api/load                 → game.json da campanha ativa
#    POST /api/save                 → grava game.json da campanha ativa
#    GET  /api/info                 → IPs, túnel, plataforma
#  ── Fichas (armazenadas no servidor) ────────────────────
#    GET  /api/room/{code}/char/{charId}      → lê ficha do disco
#    POST /api/room/{code}/char/{charId}      → salva ficha no disco + broadcast WS
#    GET  /api/room/{code}/charlist/{pid}     → lê lista de fichas
#    POST /api/room/{code}/charlist/{pid}     → salva lista de fichas
#    GET  /api/room/{code}/chat               → histórico de chat (últimas 300 msgs)
# ═══════════════════════════════════════════════════════════

import base64
import hashlib
import http.server
import json
import re
import secrets
import shutil
import socket
import socketserver
import struct
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlparse


_WS_MAGIC='258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
_ws_room_state={};_ws_room_clients={};_ws_hub_lock=threading.Lock()
def _ws_ensure_room(c):
    if c not in _ws_room_state:
        # Tenta carregar estado persistido do disco (funções definidas após este bloco)
        try:
            saved = _read_json(_room_state_file(c))
        except Exception:
            saved = None
        if saved and isinstance(saved, dict):
            tokens_list = saved.get('tokens', [])
            tokens_dict = {t['id']: t for t in tokens_list if isinstance(t, dict) and 'id' in t}
            _ws_room_state[c] = {
                'map':        saved.get('map', {}),
                'tokens':     tokens_dict,
                'init':       saved.get('init', []),
                'init_turn':  saved.get('init_turn', 0),
                'blind_roll': saved.get('blind_roll', False),
            }
        else:
            _ws_room_state[c]={'map':{},'tokens':{},'init':[],'init_turn':0,'blind_roll':False}
        _ws_room_clients[c]=[]
def _ws_send(client,text):
    try:
        p=text.encode();n=len(p)
        h=bytes([0x81,n]) if n<=125 else struct.pack('>BBH',0x81,126,n) if n<=65535 else struct.pack('>BBQ',0x81,127,n)
        with client['lock']:client['sock'].sendall(h+p)
        return True
    except:return False
def _ws_broadcast(code,msg,exclude=None):
    with _ws_hub_lock:targets=list(_ws_room_clients.get(code,[]))
    [_ws_send(c,msg) for c in targets if c is not exclude]
def _ws_recv_frame(sock):
    def rx(n):
        buf=b''
        while len(buf)<n:
            c=sock.recv(n-len(buf))
            if not c:raise ConnectionError()
            buf+=c
        return buf
    h=rx(2);op=h[0]&0x0F;masked=(h[1]>>7)&1;ln=h[1]&0x7F
    if ln==126:ln=struct.unpack('>H',rx(2))[0]
    elif ln==127:ln=struct.unpack('>Q',rx(8))[0]
    mask=rx(4) if masked else b'\x00\x00\x00\x00'
    payload=rx(ln) if ln else b''
    if masked:payload=bytes(b^mask[i%4] for i,b in enumerate(payload))
    return op,payload
PORT = 30000

if getattr(sys, 'frozen', False):
    PROJECT_DIR  = Path(sys.executable).parent.resolve()
    APP_DIR      = PROJECT_DIR / 'app'
    STATIC_CORE_DIR = PROJECT_DIR / 'core'
else:
    PROJECT_DIR  = Path(__file__).parent.parent.resolve()
    APP_DIR      = PROJECT_DIR / 'app'
    STATIC_CORE_DIR = PROJECT_DIR / 'core'

import platform
import os

# ── Configuração de Diretórios (Smart Portable Mode) ────────────────
if getattr(sys, 'frozen', False):
    # Caso empacotado (ex: PyInstaller)
    _base_dir = Path(sys.executable).parent.resolve()
else:
    # Caso rodando via script/AppImage
    _base_dir = PROJECT_DIR

# TARTANTIS_APP_DIR é injetado pelo AppRun no Linux
env_app_dir = os.environ.get('TARTANTIS_APP_DIR')
if env_app_dir:
    PORTABLE_DIR = Path(env_app_dir).resolve()
else:
    PORTABLE_DIR = PROJECT_DIR

def _get_persistent_data_dir():
    # 1. Tenta usar pasta 'data' no diretório do executável/AppImage (Portátil)
    local_data = PORTABLE_DIR / 'data'
    try:
        # Se a pasta já existe ou se podemos criar, usamos ela
        if not local_data.exists():
            local_data.mkdir(parents=True, exist_ok=True)
        # Testa escrita simples
        test_file = local_data / '.write_test'
        test_file.touch()
        test_file.unlink()
        return local_data
    except Exception:
        # 2. Fallback para pasta do usuário (~/.TartantisVTT/data)
        if platform.system() == 'Linux':
            return Path.home() / '.TartantisVTT' / 'data'
        return PROJECT_DIR / 'data'

DATA_DIR = _get_persistent_data_dir()
print(f"[*] Diretório de dados: {DATA_DIR}")

GM_PASS_FILE  = DATA_DIR / 'gm-password.txt'
CAMPAIGNS_DIR = DATA_DIR / 'campaigns'
IMAGES_DIR    = DATA_DIR / 'images'
ROOMS_DIR     = DATA_DIR / 'rooms'
ALLOWED_IMG_TYPES = {'bg', 'tokens', 'avatars'}
ALLOWED_IMG_EXTS  = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif'}

# ══════════════════════════════════════════════════════════
#  Helpers — Fichas e estado da sala no disco
# ══════════════════════════════════════════════════════════
def _char_file(code: str, char_id: str) -> Path:
    return ROOMS_DIR / code / 'chars' / f'{char_id}.json'

def _charlist_file(code: str, pid: str) -> Path:
    return ROOMS_DIR / code / 'charslist' / f'{pid}.json'

def _room_state_file(code: str) -> Path:
    return ROOMS_DIR / code / 'state.json'

def _chat_file(code: str) -> Path:
    return ROOMS_DIR / code / 'chat.json'

def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def _read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text('utf-8')) if path.exists() else default
    except Exception:
        return default

def _persist_room_state(code: str, st: dict) -> None:
    """Salva estado da sala (mapa, tokens, init, turno, blind) no disco."""
    try:
        _write_json(_room_state_file(code), {
            'map':        st.get('map', {}),
            'tokens':     list(st.get('tokens', {}).values()),
            'init':       st.get('init', []),
            'init_turn':  st.get('init_turn', 0),
            'blind_roll': st.get('blind_roll', False),
        })
    except Exception:
        pass

def _append_chat(code: str, entry: dict) -> None:
    """Acrescenta mensagem ao arquivo de chat da sala."""
    try:
        path = _chat_file(code)
        log = _read_json(path, [])
        if not isinstance(log, list):
            log = []
        log.append(entry)
        if len(log) > 300:
            log = log[-300:]
        _write_json(path, log)
    except Exception:
        pass

# ══════════════════════════════════════════════════════════
#  Estado em memória
# ══════════════════════════════════════════════════════════
_gm_token: str | None = None
_player_tokens: dict[str, str] = {}   # {player_id: token}
_active_campaign_id: str | None = None

# ══════════════════════════════════════════════════════════
#  Helpers — GM Auth
# ══════════════════════════════════════════════════════════
def _hash(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def _gm_has_password() -> bool:
    return GM_PASS_FILE.exists() and GM_PASS_FILE.read_text('utf-8').strip() != ''

def _gm_check_password(pwd: str) -> bool:
    if not _gm_has_password():
        return False
    return secrets.compare_digest(GM_PASS_FILE.read_text('utf-8').strip(), _hash(pwd))

def _gm_save_password(pwd: str):
    GM_PASS_FILE.parent.mkdir(parents=True, exist_ok=True)
    GM_PASS_FILE.write_text(_hash(pwd), encoding='utf-8')

def _gm_new_token() -> str:
    global _gm_token
    _gm_token = secrets.token_hex(32)
    return _gm_token

def _gm_valid(token: str) -> bool:
    return bool(_gm_token and token and secrets.compare_digest(_gm_token, token))

# ══════════════════════════════════════════════════════════
#  Helpers — Campanhas
# ══════════════════════════════════════════════════════════
_ROOM_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'

def _gen_id() -> str:
    return secrets.token_hex(8)

def _gen_code() -> str:
    return 'MB' + ''.join(secrets.choice(_ROOM_CHARS) for _ in range(5))

def _list_campaigns() -> list[dict]:
    out = []
    if CAMPAIGNS_DIR.exists():
        for d in CAMPAIGNS_DIR.iterdir():
            if d.is_dir():
                f = d / 'info.json'
                if f.exists():
                    try:
                        out.append(json.loads(f.read_text('utf-8')))
                    except Exception:
                        pass
    return sorted(out, key=lambda c: c.get('name', '').lower())

def _get_campaign(cid: str) -> dict | None:
    f = CAMPAIGNS_DIR / cid / 'info.json'
    return json.loads(f.read_text('utf-8')) if f.exists() else None

def _save_campaign(c: dict):
    d = CAMPAIGNS_DIR / c['id']
    d.mkdir(parents=True, exist_ok=True)
    (d / 'info.json').write_text(
        json.dumps(c, ensure_ascii=False, indent=2), encoding='utf-8')

def _get_by_code(code: str) -> dict | None:
    for c in _list_campaigns():
        if c.get('code') == code:
            return c
    return None

def _game_file(cid: str) -> Path:
    return CAMPAIGNS_DIR / cid / 'game.json'

def _public_lobby(c: dict) -> dict:
    """Remove hashes de senha antes de enviar ao cliente."""
    players = []
    for p in c.get('players', []):
        players.append({
            'id':          p['id'],
            'name':        p['name'],
            'color':       p.get('color', '#C8712A'),
            'hasPassword': bool(p.get('passwordHash')),
        })
    return {
        'id':      c['id'],
        'name':    c['name'],
        'code':    c['code'],
        'players': players,
    }

# ══════════════════════════════════════════════════════════
#  Helpers — Players
# ══════════════════════════════════════════════════════════
def _player_new_token(pid: str) -> str:
    tok = secrets.token_hex(32)
    _player_tokens[pid] = tok
    return tok

def _player_valid(pid: str, token: str) -> bool:
    stored = _player_tokens.get(pid)
    return bool(stored and token and secrets.compare_digest(stored, token))

# ══════════════════════════════════════════════════════════
#  Helpers — Rede
# ══════════════════════════════════════════════════════════
public_ip  = None
tunnel_url = None

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

_PUBLIC_IP_SERVICES = [
    'https://api.ipify.org',
    'https://ifconfig.me/ip',
    'https://checkip.amazonaws.com',
    'https://ipecho.net/plain',
]

def _fetch_public_ip():
    global public_ip
    for url in _PUBLIC_IP_SERVICES:
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                ip = r.read().decode().strip()
                parts = ip.split('.')
                if len(parts) == 4 and all(p.isdigit() for p in parts):
                    public_ip = ip
                    return
        except Exception:
            continue

def _start_cloudflared():
    global tunnel_url
    if not shutil.which('cloudflared'):
        return
    try:
        proc = subprocess.Popen(
            ['cloudflared', 'tunnel', '--url', f'http://localhost:{PORT}'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            m = re.search(r'https://[a-z0-9\-]+\.trycloudflare\.com', line)
            if m:
                tunnel_url = m.group(0)
                break
    except Exception:
        pass

LOCAL_IP = get_local_ip()
threading.Thread(target=_fetch_public_ip,   daemon=True).start()
threading.Thread(target=_start_cloudflared, daemon=True).start()


# ══════════════════════════════════════════════════════════
#  Handler HTTP
# ══════════════════════════════════════════════════════════
class MesaHandler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_DIR), **kwargs)

    # ── roteamento ────────────────────────────────────────
    def do_GET(self):
        if self.headers.get('Upgrade','').lower()=='websocket':
            self._ws_serve();return
        p = self.path.split('?')[0]
        if p == '/api/gm/status':           self._gm_status()
        elif p == '/api/campaigns':         self._campaigns_list()
        elif p == '/api/info':              self._info()
        elif p == '/api/load':              self._load()
        elif p == '/api/images/list':       self._images_list()
        elif p.startswith('/api/images/'): self._serve_image_file(p)
        elif p.startswith('/api/lobby/'):   self._lobby_public(p)
        elif p.startswith('/api/room/'):    self._room_get(p)
        elif p.startswith('/core/'):        self._serve_static(STATIC_CORE_DIR / p.replace('/core/', '', 1), base_dir=STATIC_CORE_DIR)
        elif p in ('/', ''):
            qs = ('?' + self.path.split('?', 1)[1]) if '?' in self.path else ''
            self._redirect('/portal.html' + qs)
        elif p == '/index.html':
            qs = ('?' + self.path.split('?', 1)[1]) if '?' in self.path else ''
            self._redirect('/portal.html' + qs)
        else:                               super().do_GET()

    def do_OPTIONS(self):
        self._cors_headers(200)
        self.end_headers()

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    # ── Helpers base ──────────────────────────────────────
    def _body(self) -> dict:
        n   = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(n).decode('utf-8')
        return json.loads(raw) if raw else {}

    def _gm_token(self) -> str:
        return self.headers.get('X-GM-Token', '')

    def _require_gm(self) -> bool:
        if not _gm_valid(self._gm_token()):
            self._json_error(401, 'Autenticação de Mestre necessária.')
            return False
        return True

    def _serve_static(self, file_path, base_dir=None):
        try:
            if base_dir is None:
                base_dir = PROJECT_DIR
            file_path = file_path.resolve()
            file_path.relative_to(base_dir)
            if not file_path.is_file():
                self.send_error(404)
                return
            mime = {'.css':'text/css','.js':'application/javascript',
                    '.json':'application/json'}.get(file_path.suffix.lower(),
                                                     'application/octet-stream')
            data = file_path.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception:
            self.send_error(403)

    # ── GM Auth ───────────────────────────────────────────
    def _gm_status(self):
        self._json_ok({'hasPassword': _gm_has_password(),
                       'authenticated': _gm_valid(self._gm_token())})

    def _gm_setup(self):
        if _gm_has_password():
            self._json_error(403, 'Senha já criada. Use /api/gm/change.'); return
        b = self._body()
        pwd = b.get('password', '')
        if len(pwd) < 4:
            self._json_error(400, 'Mínimo 4 caracteres.'); return
        _gm_save_password(pwd)
        self._json_ok({'token': _gm_new_token()})

    def _gm_login(self):
        b = self._body()
        if _gm_check_password(b.get('password', '')):
            self._json_ok({'token': _gm_new_token()})
        else:
            self._json_error(401, 'Senha incorreta.')

    def _gm_logout(self):
        global _gm_token
        _gm_token = None
        self._json_ok({})

    def _gm_change(self):
        b = self._body()
        tok = self._gm_token()
        if not (_gm_valid(tok) or _gm_check_password(b.get('oldPassword', ''))):
            self._json_error(401, 'Senha atual incorreta.'); return
        new = b.get('newPassword', '')
        if len(new) < 4:
            self._json_error(400, 'Mínimo 4 caracteres.'); return
        _gm_save_password(new)
        self._json_ok({})

    # ── Campanhas ─────────────────────────────────────────
    def _campaigns_list(self):
        if not self._require_gm(): return
        camps = _list_campaigns()
        # injeta se é a ativa
        out = []
        for c in camps:
            entry = _public_lobby(c)
            entry['active'] = (c['id'] == _active_campaign_id)
            out.append(entry)
        self._json_ok({'campaigns': out})

    def _campaign_create(self):
        if not self._require_gm(): return
        b = self._body()
        name = b.get('name', '').strip()
        if not name:
            self._json_error(400, 'Nome obrigatório.'); return
        c = {'id': _gen_id(), 'name': name, 'code': _gen_code(), 'players': []}
        _save_campaign(c)
        self._json_ok({'campaign': _public_lobby(c)})

    def _campaign_delete(self, cid: str):
        global _active_campaign_id
        if not self._require_gm(): return
        d = CAMPAIGNS_DIR / cid
        if d.exists():
            import shutil as _sh
            _sh.rmtree(d)
        if _active_campaign_id == cid:
            _active_campaign_id = None
        self._json_ok({})

    def _campaign_activate(self, cid: str):
        global _active_campaign_id
        if not self._require_gm(): return
        if not _get_campaign(cid):
            self._json_error(404, 'Campanha não encontrada.'); return
        _active_campaign_id = cid
        self._json_ok({})

    # ── Gerenciar jogadores ───────────────────────────────
    def _player_add(self, cid: str):
        if not self._require_gm(): return
        c = _get_campaign(cid)
        if not c:
            self._json_error(404, 'Campanha não encontrada.'); return
        b = self._body()
        name = b.get('name', '').strip()
        if not name:
            self._json_error(400, 'Nome obrigatório.'); return
        player = {
            'id':           _gen_id(),
            'name':         name,
            'color':        b.get('color', '#C8712A'),
            'passwordHash': '',
        }
        c.setdefault('players', []).append(player)
        _save_campaign(c)
        self._json_ok({'player': {k: v for k, v in player.items() if k != 'passwordHash'},
                       'hasPassword': False})

    def _player_remove(self, cid: str):
        if not self._require_gm(): return
        c = _get_campaign(cid)
        if not c:
            self._json_error(404, 'Campanha não encontrada.'); return
        b = self._body()
        pid = b.get('playerId', '')
        c['players'] = [p for p in c.get('players', []) if p['id'] != pid]
        _save_campaign(c)
        _player_tokens.pop(pid, None)
        self._json_ok({})

    def _player_set_password(self, cid: str):
        if not self._require_gm(): return
        c = _get_campaign(cid)
        if not c:
            self._json_error(404, 'Campanha não encontrada.'); return
        b    = self._body()
        pid  = b.get('playerId', '')
        pwd  = b.get('password', '')
        for p in c.get('players', []):
            if p['id'] == pid:
                p['passwordHash'] = _hash(pwd) if pwd else ''
                _save_campaign(c)
                self._json_ok({'hasPassword': bool(pwd)})
                return
        self._json_error(404, 'Jogador não encontrado.')

    # ── Lobby público ─────────────────────────────────────
    def _lobby_public(self, path: str):
        # path = /api/lobby/{code}
        parts = path.strip('/').split('/')
        code  = parts[-1].upper() if parts else ''
        c = _get_by_code(code)
        if not c:
            self._json_error(404, 'Sala não encontrada.'); return
        self._json_ok(_public_lobby(c))

    # ── Auth do Jogador ───────────────────────────────────
    def _player_login(self):
        b    = self._body()
        code = b.get('code', '').upper()
        pid  = b.get('playerId', '')
        pwd  = b.get('password', '')
        c = _get_by_code(code)
        if not c:
            self._json_error(404, 'Sala não encontrada.'); return
        for p in c.get('players', []):
            if p['id'] == pid:
                stored = p.get('passwordHash', '')
                if not stored:
                    # Slot aberto (sem senha)
                    tok = _player_new_token(pid)
                    _active_campaign_id  # garante que a campanha está mapeada
                    self._json_ok({'token': tok, 'campaignId': c['id']})
                    return
                if secrets.compare_digest(stored, _hash(pwd)):
                    tok = _player_new_token(pid)
                    self._json_ok({'token': tok, 'campaignId': c['id']})
                    return
                else:
                    self._json_error(401, 'Senha incorreta.')
                    return
        self._json_error(404, 'Jogador não encontrado.')

    # ── Load / Save (campanha ativa) ──────────────────────
    def _load(self):
        if not _active_campaign_id:
            self._json_response(404, 'null'); return
        f = _game_file(_active_campaign_id)
        if f.exists():
            try:
                data = f.read_text('utf-8')
                json.loads(data)
                self._json_response(200, data)
            except Exception:
                self._json_error(500, 'arquivo corrompido')
        else:
            self._json_response(404, 'null')

    def _save(self):
        try:
            b      = self._body()
            length = int(self.headers.get('Content-Length', 0))
            body   = self.rfile.read(0).decode('utf-8')  # já lido em _body
        except Exception:
            pass
        # Re-lê body bruto (já consumido, usa b)
        try:
            raw = json.dumps(self._body() if False else b)
        except Exception:
            pass

        # Leitura direta sem usar _body() (que já consumiu o stream)
        try:
            length = int(self.headers.get('Content-Length', 0))
        except Exception:
            length = 0

        # Se chegou aqui via _body já lido, precisa reprocessar
        # Workaround: _body é chamado apenas no POST handler que chama _save
        # então vamos ler diretamente aqui sem chamar _body
        self._json_error(500, 'use _save_direct')

    def _save_direct(self, raw_body: str):
        try:
            parsed = json.loads(raw_body)
            cid = _active_campaign_id
            if not cid:
                self._json_error(400, 'Nenhuma campanha ativa.'); return
            if parsed is None:
                f = _game_file(cid)
                if f.exists():
                    f.unlink()
                self._json_ok({}); return
            f = _game_file(cid)
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(raw_body, encoding='utf-8')
            self._json_ok({})
        except json.JSONDecodeError:
            self._json_error(400, 'JSON inválido')
        except Exception as e:
            self._json_error(500, str(e))

    # ── Info ──────────────────────────────────────────────
    def _info(self):
        self._json_ok({
            'port':                 PORT,
            'platform':             sys.platform,
            'localIp':              LOCAL_IP,
            'localUrl':             f'http://{LOCAL_IP}:{PORT}',
            'publicIp':             public_ip,
            'publicUrl':            f'http://{public_ip}:{PORT}' if public_ip else None,
            'publicIpReady':        public_ip is not None,
            'tunnelUrl':            tunnel_url,
            'hasTunnel':            tunnel_url is not None,
            'cloudflaredAvailable': shutil.which('cloudflared') is not None,
            'activeCampaignId':     _active_campaign_id,
            'dataDir':              str(DATA_DIR.resolve()),
        })

    # ── Resposta HTTP ─────────────────────────────────────
    def _redirect(self, location):
        self.send_response(302)
        self.send_header('Location', location)
        self.end_headers()

    def _cors_headers(self, code):
        self.send_response(code)
        self.send_header('Access-Control-Allow-Origin',  '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-GM-Token, X-Player-Token')

    def _json_response(self, code, body):
        enc = body.encode('utf-8')
        self._cors_headers(code)
        self.send_header('Content-Type',   'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(enc)))
        self.end_headers()
        self.wfile.write(enc)

    def _json_ok(self, data: dict):
        data['ok'] = True
        self._json_response(200, json.dumps(data, ensure_ascii=False))

    def _json_error(self, code, msg):
        self._json_response(code, json.dumps({'ok': False, 'error': msg}))

    def log_message(self, fmt, *args):
        pass  # silencioso

    # ── Imagens ────────────────────────────────────────────
    def _images_list(self):
        """GET /api/images/list?type=bg|tokens|avatars
           Retorna todas as imagens (root + subpastas) e lista de pastas.
           Cada imagem inclui campo 'folder' ('' para root).
        """
        qs    = parse_qs(urlparse(self.path).query)
        itype = qs.get('type', ['bg'])[0]
        if itype not in ALLOWED_IMG_TYPES:
            self._json_error(400, 'Tipo inválido.'); return
        base   = IMAGES_DIR / itype
        images = []
        folders = []
        if base.exists():
            entries = sorted(base.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
            for f in entries:
                if f.is_file() and f.suffix.lower() in ALLOWED_IMG_EXTS:
                    images.append({'filename': f.name, 'folder': '',
                                   'url': f'/api/images/{itype}/{f.name}',
                                   'sizeKB': round(f.stat().st_size / 1024)})
                elif f.is_dir() and not f.name.startswith('.'):
                    folders.append(f.name)
                    for sf in sorted(f.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                        if sf.is_file() and sf.suffix.lower() in ALLOWED_IMG_EXTS:
                            images.append({'filename': sf.name, 'folder': f.name,
                                           'url': f'/api/images/{itype}/{f.name}/{sf.name}',
                                           'sizeKB': round(sf.stat().st_size / 1024)})
        self._json_ok({'images': images, 'folders': sorted(folders)})

    def _serve_image_file(self, path):
        """GET /api/images/{type}/{filename}
              /api/images/{type}/{folder}/{filename}
        """
        parts = path.strip('/').split('/')  # ['api','images',type,...,filename]
        if len(parts) == 4:
            itype, fname = parts[2], parts[3]
            fpath = IMAGES_DIR / itype / fname
        elif len(parts) == 5:
            itype, folder, fname = parts[2], parts[3], parts[4]
            if '..' in folder or '/' in folder:
                self.send_error(403); return
            fpath = IMAGES_DIR / itype / folder / fname
        else:
            self.send_error(404); return
        if itype not in ALLOWED_IMG_TYPES or '..' in fname:
            self.send_error(403); return
        if not fpath.is_file():
            self.send_error(404); return
        ext  = fpath.suffix.lower()
        mime = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
                '.gif': 'image/gif', '.webp': 'image/webp', '.bmp': 'image/bmp',
                '.tiff': 'image/tiff', '.tif': 'image/tiff'}.get(ext, 'application/octet-stream')
        data = fpath.read_bytes()
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'public, max-age=86400')
        self.end_headers()
        self.wfile.write(data)

    def _upload_image(self):
        """POST /api/images/upload?type=bg|tokens|avatars&name=filename[&folder=name]"""
        qs          = parse_qs(urlparse(self.path).query)
        itype       = qs.get('type',   ['bg'])[0]
        name        = qs.get('name',   ['image'])[0]
        folder_name = qs.get('folder', [''])[0]
        if itype not in ALLOWED_IMG_TYPES:
            self._json_error(400, 'Tipo inválido.'); return
        if folder_name and ('..' in folder_name or '/' in folder_name):
            self._json_error(400, 'Pasta inválida.'); return
        # avatars aceitam jogadores; bg e tokens exigem GM
        if itype == 'avatars':
            ptok = self.headers.get('X-Player-Token', '')
            pid  = self.headers.get('X-Player-Id', '')
            gm_ok = _gm_valid(self._gm_token())
            plr_ok = _player_valid(pid, ptok)
            if not (gm_ok or plr_ok):
                self._json_error(401, 'Autenticação necessária.'); return
        else:
            if not self._require_gm(): return
        # Sanitiza nome e gera nome único
        name = re.sub(r'[^a-zA-Z0-9._-]', '_', name)[:80]
        ext  = ('.' + name.rsplit('.', 1)[-1].lower()) if '.' in name else '.bin'
        if ext not in ALLOWED_IMG_EXTS:
            ext = '.jpg'
        ts       = str(int(time.time() * 1000))
        filename = f"{ts}_{name}"
        dest_dir = (IMAGES_DIR / itype / folder_name) if folder_name else (IMAGES_DIR / itype)
        dest_dir.mkdir(parents=True, exist_ok=True)
        length = int(self.headers.get('Content-Length', 0))
        data   = self.rfile.read(length)
        (dest_dir / filename).write_bytes(data)
        url = f'/api/images/{itype}/{(folder_name + "/") if folder_name else ""}{filename}'
        self._json_ok({'url': url, 'filename': filename, 'folder': folder_name,
                       'sizeKB': round(len(data) / 1024)})

    def _delete_image(self):
        """POST /api/images/delete?type=...&name=...[&folder=name]"""
        if not self._require_gm(): return
        qs          = parse_qs(urlparse(self.path).query)
        itype       = qs.get('type',   ['bg'])[0]
        fname       = qs.get('name',   [''])[0]
        folder_name = qs.get('folder', [''])[0]
        if itype not in ALLOWED_IMG_TYPES or not fname or '..' in fname:
            self._json_error(400, 'Inválido.'); return
        if folder_name and ('..' in folder_name or '/' in folder_name):
            self._json_error(400, 'Pasta inválida.'); return
        fpath = (IMAGES_DIR / itype / folder_name / fname) if folder_name \
                else (IMAGES_DIR / itype / fname)
        if fpath.exists():
            fpath.unlink()
        self._json_ok({})

    def _folder_create(self, body):
        """POST /api/images/folder/create  {type, folder}"""
        if not self._require_gm(): return
        itype = body.get('type', 'tokens')
        name  = body.get('folder', '').strip()
        if itype not in ALLOWED_IMG_TYPES or not name:
            self._json_error(400, 'Inválido.'); return
        name = re.sub(r'[^a-zA-Z0-9_\- ]', '_', name)[:40].strip()
        if not name or '..' in name or '/' in name:
            self._json_error(400, 'Nome de pasta inválido.'); return
        (IMAGES_DIR / itype / name).mkdir(parents=True, exist_ok=True)
        self._json_ok({'folder': name})

    def _folder_delete(self, body):
        """POST /api/images/folder/delete  {type, folder}
           Só apaga se a pasta estiver vazia.
        """
        if not self._require_gm(): return
        itype = body.get('type', 'tokens')
        name  = body.get('folder', '').strip()
        if itype not in ALLOWED_IMG_TYPES or not name or '..' in name or '/' in name:
            self._json_error(400, 'Inválido.'); return
        path = IMAGES_DIR / itype / name
        if path.exists() and path.is_dir():
            remaining = [f for f in path.iterdir() if f.is_file()]
            if remaining:
                self._json_error(400, f'Pasta contém {len(remaining)} imagem(ns). Mova-as antes de apagar.'); return
            path.rmdir()
        self._json_ok({})

    def _move_image(self, body):
        """POST /api/images/move  {type, filename, from_folder, to_folder}"""
        if not self._require_gm(): return
        itype       = body.get('type', 'tokens')
        filename    = body.get('filename', '')
        from_folder = body.get('from_folder', '')
        to_folder   = body.get('to_folder', '')
        if itype not in ALLOWED_IMG_TYPES or not filename or '..' in filename:
            self._json_error(400, 'Inválido.'); return
        for fo in [from_folder, to_folder]:
            if fo and ('..' in fo or '/' in fo):
                self._json_error(400, 'Pasta inválida.'); return
        src = (IMAGES_DIR / itype / from_folder / filename) if from_folder \
              else (IMAGES_DIR / itype / filename)
        if not src.exists():
            self._json_error(404, 'Arquivo não encontrado.'); return
        dst_dir = (IMAGES_DIR / itype / to_folder) if to_folder else (IMAGES_DIR / itype)
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / filename
        if dst.exists():  # evita sobrescrever
            stem = filename.rsplit('.', 1)[0] if '.' in filename else filename
            ext  = ('.' + filename.rsplit('.', 1)[1]) if '.' in filename else ''
            dst  = dst_dir / f"{stem}_{int(time.time())}{ext}"
        src.rename(dst)
        new_url = f'/api/images/{itype}/{(to_folder + "/") if to_folder else ""}{dst.name}'
        self._json_ok({'url': new_url, 'filename': dst.name, 'folder': to_folder})


    def _ws_serve(self):
        key=self.headers.get('Sec-WebSocket-Key','')
        accept=base64.b64encode(hashlib.sha1((key+_WS_MAGIC).encode()).digest()).decode()
        self.wfile.write(('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: '+accept+'\r\n\r\n').encode())
        self.wfile.flush()
        client={'sock':self.connection,'lock':threading.Lock()}
        room=None
        try:
            while True:
                op,payload=_ws_recv_frame(self.connection)
                if op==8:break
                if op==9:self.connection.sendall(bytes([0x8A,0]));continue
                if op!=1:continue
                try:msg=json.loads(payload.decode('utf-8'))
                except:continue
                mt=msg.get('type','');mr=msg.get('room','');data=msg.get('data')
                if mt=='join' and mr:
                    with _ws_hub_lock:
                        if room and room in _ws_room_clients:
                            try:_ws_room_clients[room].remove(client)
                            except ValueError:pass
                        room=mr;_ws_ensure_room(room)
                        if client not in _ws_room_clients[room]:_ws_room_clients[room].append(client)
                    st=_ws_room_state[room]
                    _ws_send(client,json.dumps({'type':'state','room':room,'data':{'map':st['map'],'tokens':list(st['tokens'].values()),'init':st['init'],'init_turn':st['init_turn'],'blind_roll':st['blind_roll']}}))
                    continue
                if not mr:continue
                persist = False
                with _ws_hub_lock:
                    _ws_ensure_room(mr);st=_ws_room_state[mr]
                    if mt=='map' and data:st['map']=data;persist=True
                    elif mt=='token_set' and data and data.get('id'):st['tokens'][data['id']]=data;persist=True
                    elif mt=='token_remove' and isinstance(data,dict) and data.get('id'):st['tokens'].pop(data['id'],None);persist=True
                    elif mt=='init':st['init']=data if isinstance(data,list) else [];persist=True
                    elif mt=='init_turn':st['init_turn']=int(data) if isinstance(data,(int,float)) else 0;persist=True
                    elif mt=='blind_roll':st['blind_roll']=bool(data);persist=True
                    elif mt=='chat' and data:_append_chat(mr,data)
                # Persiste estado da sala no disco (fora do lock para não bloquear)
                if persist:
                    _persist_room_state(mr,_ws_room_state[mr])
                _ws_broadcast(mr,json.dumps(msg),exclude=client)
        except:pass
        finally:
            if room:
                with _ws_hub_lock:
                    lst=_ws_room_clients.get(room,[])
                    try:lst.remove(client)
                    except ValueError:pass
    # ── Override do POST para capturar body bruto ─────────
    def do_POST(self):
        global _active_campaign_id
        p = self.path.split('?')[0]

        # Rotas binárias — antes de tentar ler body JSON
        if p == '/api/images/upload':
            self._upload_image()
            return
        if p == '/api/images/delete':
            self._delete_image()
            return

        # Lê body uma única vez
        try:
            length   = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(length).decode('utf-8')
            body     = json.loads(raw_body) if raw_body else {}
        except Exception:
            raw_body = ''
            body     = {}

        self._current_body = body

        # Roteamento
        if   p == '/api/gm/setup':              self._gm_setup2(body)
        elif p == '/api/gm/login':              self._gm_login2(body)
        elif p == '/api/gm/logout':             self._gm_logout()
        elif p == '/api/gm/change':             self._gm_change2(body)
        elif p == '/api/campaigns':             self._campaign_create2(body)
        elif p == '/api/player/login':          self._player_login2(body)
        elif p == '/api/save':                  self._save_direct(raw_body)
        elif p.startswith('/api/room/'):        self._room_post(p, raw_body)
        elif p == '/api/images/folder/create':  self._folder_create(body)
        elif p == '/api/images/folder/delete':  self._folder_delete(body)
        elif p == '/api/images/move':           self._move_image(body)
        else:
            parts = p.strip('/').split('/')
            if len(parts) == 4 and parts[:2] == ['api','campaigns']:
                cid, action = parts[2], parts[3]
                if   action == 'delete':   self._campaign_delete(cid)
                elif action == 'activate':
                    if not self._require_gm(): return
                    if not _get_campaign(cid):
                        self._json_error(404, 'Campanha não encontrada.'); return
                    _active_campaign_id = cid
                    self._json_ok({})
                else: self._json_error(404, 'not found')
            elif len(parts) == 5 and parts[:2] == ['api','campaigns'] and parts[3] == 'player':
                cid, action = parts[2], parts[4]
                if   action == 'add':      self._player_add2(cid, body)
                elif action == 'remove':   self._player_remove2(cid, body)
                elif action == 'password': self._player_set_password2(cid, body)
                else: self._json_error(404, 'not found')
            else:
                self._json_error(404, 'not found')

    # ── Versões "2" que recebem body já parseado ──────────
    def _gm_setup2(self, b):
        if _gm_has_password():
            self._json_error(403, 'Senha já criada.'); return
        pwd = b.get('password', '')
        if len(pwd) < 4:
            self._json_error(400, 'Mínimo 4 caracteres.'); return
        _gm_save_password(pwd)
        self._json_ok({'token': _gm_new_token()})

    def _gm_login2(self, b):
        if _gm_check_password(b.get('password', '')):
            self._json_ok({'token': _gm_new_token()})
        else:
            self._json_error(401, 'Senha incorreta.')

    def _gm_change2(self, b):
        tok = self._gm_token()
        if not (_gm_valid(tok) or _gm_check_password(b.get('oldPassword', ''))):
            self._json_error(401, 'Senha atual incorreta.'); return
        new = b.get('newPassword', '')
        if len(new) < 4:
            self._json_error(400, 'Mínimo 4 caracteres.'); return
        _gm_save_password(new)
        self._json_ok({})

    def _campaign_create2(self, b):
        if not self._require_gm(): return
        name = b.get('name', '').strip()
        if not name:
            self._json_error(400, 'Nome obrigatório.'); return
        c = {'id': _gen_id(), 'name': name, 'code': _gen_code(), 'players': []}
        _save_campaign(c)
        self._json_ok({'campaign': _public_lobby(c)})

    def _player_add2(self, cid, b):
        if not self._require_gm(): return
        c = _get_campaign(cid)
        if not c:
            self._json_error(404, 'Campanha não encontrada.'); return
        name = b.get('name', '').strip()
        if not name:
            self._json_error(400, 'Nome obrigatório.'); return
        player = {'id': _gen_id(), 'name': name,
                  'color': b.get('color', '#C8712A'), 'passwordHash': ''}
        c.setdefault('players', []).append(player)
        _save_campaign(c)

        room_code = c.get('code')
        if room_code:
            pid = player['id']
            try:
                charlist_data = [{"id": f"char_{pid}", "label": "Principal"}]
                _write_json(_charlist_file(room_code, pid), charlist_data)

                char_data = {
                    "id": f"char_{pid}", "nome": name, "jogador": name,
                    "raca": "", "classe": "", "nivel": 1, "xp": 0, "origem": "",
                    "forca_raca": 0, "agi_raca": 0, "intel_raca": 0, "von_raca": 0,
                    "pv": 20, "pvMax": 20, "pm": 10, "pmMax": 10,
                    "defesa": 10, "iniciativa": 0, "velocidade": 9,
                    "ataqueCac": "+0", "danoCac": "1d6", "ataqueDist": "+0", "danoDist": "1d6",
                    "pericias": "", "equipamentos": "", "poderes": "", "notas": ""
                }
                _write_json(_char_file(room_code, f"char_{pid}"), char_data)
            except Exception as e:
                self.log_message("Erro ao criar fichas iniciais: %s", e)

        self._json_ok({'player': {k:v for k,v in player.items() if k != 'passwordHash'},
                       'hasPassword': False})

    def _player_remove2(self, cid, b):
        if not self._require_gm(): return
        c = _get_campaign(cid)
        if not c:
            self._json_error(404, 'Campanha não encontrada.'); return
        pid = b.get('playerId', '')
        c['players'] = [p for p in c.get('players', []) if p['id'] != pid]
        _save_campaign(c)
        _player_tokens.pop(pid, None)
        self._json_ok({})

    def _player_set_password2(self, cid, b):
        if not self._require_gm(): return
        c = _get_campaign(cid)
        if not c:
            self._json_error(404, 'Campanha não encontrada.'); return
        pid, pwd = b.get('playerId',''), b.get('password','')
        for p in c.get('players', []):
            if p['id'] == pid:
                p['passwordHash'] = _hash(pwd) if pwd else ''
                _save_campaign(c)
                self._json_ok({'hasPassword': bool(pwd)}); return
        self._json_error(404, 'Jogador não encontrado.')

    # ── Fichas / estado da sala ────────────────────────────
    def _room_get(self, path: str):
        """
        GET /api/room/{code}/char/{charId}   → ficha JSON
        GET /api/room/{code}/charlist/{pid}  → lista de fichas
        GET /api/room/{code}/chat            → histórico de chat
        """
        parts = path.strip('/').split('/')   # ['api','room',code, resource, ...]
        if len(parts) < 4:
            self._json_error(400, 'Rota inválida'); return
        code = parts[2]
        if not re.match(r'^[A-Za-z0-9_\-]+$', code):
            self._json_error(400, 'Código de sala inválido'); return
        resource = parts[3]

        if resource == 'char' and len(parts) == 5:
            char_id = parts[4]
            if not re.match(r'^[A-Za-z0-9_\-]+$', char_id):
                self._json_error(400, 'charId inválido'); return
            data = _read_json(_char_file(code, char_id))
            if data is None:
                self._json_response(404, 'null')
            else:
                self._json_response(200, json.dumps(data, ensure_ascii=False))

        elif resource == 'charlist' and len(parts) == 5:
            pid = parts[4]
            if not re.match(r'^[A-Za-z0-9_\-]+$', pid):
                self._json_error(400, 'pid inválido'); return
            data = _read_json(_charlist_file(code, pid), [])
            self._json_response(200, json.dumps(data, ensure_ascii=False))

        elif resource == 'chat':
            data = _read_json(_chat_file(code), [])
            self._json_response(200, json.dumps(data, ensure_ascii=False))

        else:
            self._json_error(404, 'not found')

    def _room_post(self, path: str, raw_body: str):
        """
        POST /api/room/{code}/char/{charId}   → salva ficha + broadcast WS
        POST /api/room/{code}/charlist/{pid}  → salva lista de fichas
        """
        parts = path.strip('/').split('/')
        if len(parts) < 4:
            self._json_error(400, 'Rota inválida'); return
        code = parts[2]
        if not re.match(r'^[A-Za-z0-9_\-]+$', code):
            self._json_error(400, 'Código de sala inválido'); return
        resource = parts[3]

        try:
            data = json.loads(raw_body) if raw_body else None
        except json.JSONDecodeError:
            self._json_error(400, 'JSON inválido'); return

        if resource == 'char' and len(parts) == 5:
            char_id = parts[4]
            if not re.match(r'^[A-Za-z0-9_\-]+$', char_id):
                self._json_error(400, 'charId inválido'); return
            if data is None:
                self._json_error(400, 'body vazio'); return
            _write_json(_char_file(code, char_id), data)
            # Broadcast para todos os clientes da sala verem a ficha atualizada
            _ws_broadcast(code, json.dumps({'type': 'char_update', 'room': code, 'data': data}))
            self._json_ok({})

        elif resource == 'charlist' and len(parts) == 5:
            pid = parts[4]
            if not re.match(r'^[A-Za-z0-9_\-]+$', pid):
                self._json_error(400, 'pid inválido'); return
            if not isinstance(data, list):
                self._json_error(400, 'body deve ser array'); return
            _write_json(_charlist_file(code, pid), data)
            self._json_ok({})

        else:
            self._json_error(404, 'not found')

    def _player_login2(self, b):
        code = b.get('code', '').upper()
        pid  = b.get('playerId', '')
        pwd  = b.get('password', '')
        c = _get_by_code(code)
        if not c:
            self._json_error(404, 'Sala não encontrada.'); return
        for p in c.get('players', []):
            if p['id'] == pid:
                stored = p.get('passwordHash', '')
                ok = (not stored) or (pwd and secrets.compare_digest(stored, _hash(pwd)))
                if ok:
                    self._json_ok({'token': _player_new_token(pid), 'campaignId': c['id']})
                else:
                    self._json_error(401, 'Senha incorreta.')
                return
        self._json_error(404, 'Jogador não encontrado.')


class _ThreadedHTTPServer(socketserver.ThreadingMixIn,http.server.HTTPServer):
    daemon_threads=True
if __name__=='__main__':
    server=_ThreadedHTTPServer(('0.0.0.0',PORT),MesaHandler)
    print(f'[MB] Servidor rodando em http://localhost:{PORT} (WebSocket ativo)')
    server.serve_forever()
