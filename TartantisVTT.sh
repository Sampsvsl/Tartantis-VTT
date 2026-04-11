#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
#  Tartantis VTT — Launcher Linux
#  Abre a porta 30000, inicia o servidor e abre o browser.
#  Funciona tanto pelo terminal quanto pelo ícone do sistema.
# ═══════════════════════════════════════════════════════════

PORT=30000
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDFILE="$DIR/.server.pid"
LOGFILE="$DIR/.server.log"

# ── Mata servidor anterior se existir ─────────────────────
if [ -f "$PIDFILE" ]; then
  OLD_PID=$(cat "$PIDFILE")
  kill "$OLD_PID" 2>/dev/null
  rm -f "$PIDFILE"
fi

# ── Verifica Python3 ──────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  notify-send "Tartantis VTT" "Python3 não encontrado.\nInstale: sudo pacman -S python" 2>/dev/null \
    || zenity --error --text="Python3 não encontrado. Instale com: sudo pacman -S python" 2>/dev/null \
    || echo "Erro: Python3 não encontrado."
  exit 1
fi

# ── Abre a porta 30000 no firewall (como o Foundry faz) ────
_open_port() {
  local port=$1
  # Tenta via pkexec (diálogo gráfico) primeiro, depois sudo silencioso
  if command -v ufw &>/dev/null; then
    pkexec ufw allow ${port}/tcp 2>/dev/null || sudo ufw allow ${port}/tcp 2>/dev/null || true
  elif command -v firewall-cmd &>/dev/null; then
    pkexec firewall-cmd --permanent --add-port=${port}/tcp 2>/dev/null && \
    pkexec firewall-cmd --reload 2>/dev/null || \
    sudo firewall-cmd --permanent --add-port=${port}/tcp 2>/dev/null && sudo firewall-cmd --reload 2>/dev/null || true
  elif command -v iptables &>/dev/null; then
    pkexec iptables -I INPUT -p tcp --dport ${port} -j ACCEPT 2>/dev/null || \
    sudo iptables -I INPUT -p tcp --dport ${port} -j ACCEPT 2>/dev/null || true
  fi
}

# Tenta abrir a porta em background (não bloqueia o lançamento)
_open_port $PORT &

# ── Inicia servidor customizado em background ──────────────
cd "$DIR"
nohup python3 core/server.py >"$LOGFILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PIDFILE"

# ── Aguarda o servidor estar pronto (retry com nc/curl) ───
MAX_WAIT=10
READY=0
for i in $(seq 1 $MAX_WAIT); do
  if nc -z 127.0.0.1 $PORT 2>/dev/null; then
    READY=1
    break
  elif curl -sf "http://127.0.0.1:${PORT}/api/info" -o /dev/null 2>/dev/null; then
    READY=1
    break
  fi
  sleep 0.5
done

# Verifica se o processo ainda está vivo
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
  MSG="Falha ao iniciar servidor local.\nVeja o log: $LOGFILE"
  notify-send "Tartantis VTT" "$MSG" 2>/dev/null \
    || zenity --error --text="$MSG" 2>/dev/null \
    || echo "Erro: $MSG"
  rm -f "$PIDFILE"
  exit 1
fi

# ── Obtém o IP local para a URL que os jogadores usarão ───
LOCAL_IP=$(python3 -c "
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    print(s.getsockname()[0])
    s.close()
except:
    print('127.0.0.1')
" 2>/dev/null || echo "127.0.0.1")

OPEN_URL="http://${LOCAL_IP}:${PORT}/portal.html"

# ── Abre no navegador padrão ───
if command -v xdg-open &>/dev/null; then
  xdg-open "$OPEN_URL" >/dev/null 2>&1 &
fi

# ── Checa por updates em background ───
(
  UPDATE_INFO=$(python3 -c "from core import updater; from pathlib import Path; available, ver, url = updater.check_for_updates(Path('$DIR')); print(f'{available}|{ver}|{url}')" 2>/dev/null)
  if [[ "$UPDATE_INFO" == "True|"* ]]; then
    VER=$(echo "$UPDATE_INFO" | cut -d'|' -f2)
    URL=$(echo "$UPDATE_INFO" | cut -d'|' -f3)
    MSG="Nova versão disponível: v$VER\nClique para baixar."
    if command -v notify-send &>/dev/null; then
      notify-send "Tartantis VTT - Update" "$MSG" --icon=info
    fi
  fi
) &

# ── Mantém processo vivo: ícone na bandeja ou janela estilizada ───
python3 - "$OPEN_URL" <<'PYEOF'
import sys, subprocess
url = sys.argv[1]
def open_browser():
    subprocess.Popen(['xdg-open', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
def try_pystray(url):
    try:
        import pystray
        from PIL import Image, ImageDraw
    except ImportError:
        return False
    sz = 64
    img = Image.new('RGBA', (sz, sz), (18, 14, 9, 255))
    d = ImageDraw.Draw(img)
    d.ellipse([1, 1, sz-2, sz-2], outline='#c8a84b', width=2)
    d.rectangle([30, 8, 34, 56], fill='#c8a84b')
    d.rectangle([16, 26, 48, 30], fill='#c8a84b')
    def on_open(icon, item): open_browser()
    def on_stop(icon, item): icon.stop()
    menu = pystray.Menu(
        pystray.MenuItem('Abrir no Navegador', on_open),
        pystray.MenuItem('Desligar Servidor',  on_stop),
    )
    icon = pystray.Icon('tartantis', img, 'Tartantis VTT — Rodando', menu)
    icon.run()
    return True
def try_tkinter(url):
    try:
        import tkinter as tk
    except ImportError:
        return False
    BG, GOLD, EMBER, FG, DIM = '#12100e', '#c8a84b', '#e07b39', '#e8ddc8', '#666655'
    root = tk.Tk()
    root.title('Tartantis VTT')
    root.geometry('320x170')
    root.resizable(False, False)
    root.configure(bg=BG)
    tk.Frame(root, bg=GOLD, height=3).pack(fill='x', side='top')
    tk.Label(root, text='⚔  TARTANTIS VTT  ⚔', fg=GOLD, bg=BG,
             font=('Georgia', 12, 'bold')).pack(pady=(14, 4))
    tk.Label(root, text='Servidor rodando · porta 30000', fg=FG, bg=BG,
             font=('', 9)).pack()
    tk.Label(root, text=url, fg=DIM, bg=BG,
             font=('', 8)).pack(pady=(2, 14))
    btns = tk.Frame(root, bg=BG)
    btns.pack()
    tk.Button(btns, text='Abrir Navegador', command=open_browser,
              bg='#2a1f08', fg=GOLD, relief='flat', cursor='hand2',
              font=('', 9), padx=12, pady=5,
              activebackground='#3a2f10', activeforeground=GOLD
             ).pack(side='left', padx=6)
    tk.Button(btns, text='Desligar', command=root.destroy,
              bg='#3a1208', fg=EMBER, relief='flat', cursor='hand2',
              font=('', 9, 'bold'), padx=12, pady=5,
              activebackground='#5a2010', activeforeground=EMBER
             ).pack(side='left', padx=6)
    root.protocol('WM_DELETE_WINDOW', root.destroy)
    tk.Frame(root, bg=GOLD, height=3).pack(fill='x', side='bottom')
    root.mainloop()
    return True
if not try_pystray(url):
    if not try_tkinter(url):
        import time
        while True: time.sleep(60)
PYEOF

[ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE")" 2>/dev/null
rm -f "$PIDFILE"
exit 0
