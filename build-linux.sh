#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  Tartantis VTT — Build AppImage (Linux x86_64)
#
#  Gera TartantisVTT-x86_64.AppImage pronto para distribuição.
#  Não requer instalação — basta dar duplo clique ou executar.
#
#  Dependências: appimagetool (baixado automaticamente)
#  Uso: bash build-linux.sh
# ═══════════════════════════════════════════════════════════════════

set -e

BOLD="\033[1m"; GOLD="\033[33m"; GREEN="\033[32m"; DIM="\033[2m"; RESET="\033[0m"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPDIR="$DIR/.appdir-build"
OUTPUT="$DIR/TartantisVTT-x86_64.AppImage"
TOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
TOOL="$DIR/.appimagetool"

echo ""
echo -e "${GOLD}${BOLD}  ⚔  Tartantis VTT — Build AppImage${RESET}"
echo -e "${DIM}  ─────────────────────────────────────${RESET}"

# ── Baixa appimagetool se necessário ─────────────────────────────
if [ ! -f "$TOOL" ]; then
  echo -e "${DIM}  → Baixando appimagetool…${RESET}"
  wget -q --show-progress -O "$TOOL" "$TOOL_URL"
  chmod +x "$TOOL"
fi

# ── Monta AppDir limpo ───────────────────────────────────────────
rm -rf "$APPDIR"
SHARE="$APPDIR/usr/share/tartantis"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$SHARE"

echo -e "${DIM}  → Copiando arquivos…${RESET}"
cp -r "$DIR/app"  "$SHARE/"
cp -r "$DIR/core" "$SHARE/"
cp -r "$DIR/assets" "$SHARE/" 2>/dev/null || true
mkdir -p "$SHARE/data"

# ── AppRun ───────────────────────────────────────────────────────
cat > "$APPDIR/AppRun" << 'APPRUN'
#!/usr/bin/env bash
PORT=30000
SELF="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
APP="$SELF/usr/share/tartantis"
PIDFILE="$HOME/.tvtt.pid"
LOGFILE="$HOME/.tvtt.log"

[ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE")" 2>/dev/null; rm -f "$PIDFILE"

command -v python3 &>/dev/null || {
  notify-send "Tartantis VTT" "Python3 não encontrado." 2>/dev/null || echo "Erro: Python3 não encontrado."
  exit 1
}

# Firewall em background
{ command -v ufw       &>/dev/null && (pkexec ufw allow ${PORT}/tcp 2>/dev/null || sudo ufw allow ${PORT}/tcp 2>/dev/null) ; } &
{ command -v firewall-cmd &>/dev/null && (sudo firewall-cmd --permanent --add-port=${PORT}/tcp && sudo firewall-cmd --reload) 2>/dev/null ; } &

# Detecta diretório original do AppImage (para modo portátil)
if [ -n "$APPIMAGE" ]; then
  export TARTANTIS_APP_DIR="$(dirname "$APPIMAGE")"
else
  export TARTANTIS_APP_DIR="$(pwd)"
fi

cd "$APP"
nohup python3 core/server.py >"$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"

for i in $(seq 1 20); do
  nc -z 127.0.0.1 $PORT 2>/dev/null && break
  curl -sf "http://127.0.0.1:${PORT}/api/info" -o /dev/null 2>/dev/null && break
  sleep 0.4
done

kill -0 "$(cat "$PIDFILE")" 2>/dev/null || {
  notify-send "Tartantis VTT" "Falha ao iniciar servidor." 2>/dev/null || echo "Erro. Log: $LOGFILE"
  exit 1
}

LOCAL_IP=$(python3 -c "
import socket
try:
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(('8.8.8.8',80)); print(s.getsockname()[0]); s.close()
except: print('127.0.0.1')
")
URL="http://${LOCAL_IP}:${PORT}/portal.html"

command -v xdg-open &>/dev/null && { xdg-open "$URL" >/dev/null 2>&1 & }

python3 - "$URL" <<'PYEOF'
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
    pystray.Icon('tartantis', img, 'Tartantis VTT — Rodando', menu).run()
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
APPRUN
chmod +x "$APPDIR/AppRun"

# ── .desktop ─────────────────────────────────────────────────────
cat > "$APPDIR/tartantis.desktop" << 'DESK'
[Desktop Entry]
Version=1.0
Type=Application
Name=Tartantis VTT
GenericName=Tartantis VTT — Mesa Virtual de RPG
Comment=Tartantis VTT — Mesa Virtual de RPG Gratuita
Exec=AppRun
Icon=tartantis
Terminal=false
Categories=Game;RolePlaying;
Keywords=rpg;mesa;virtual;tartantis;vtt;
StartupNotify=true
DESK

# ── Ícone ─────────────────────────────────────────────────────────
if [ -f "$DIR/assets/icon.png" ]; then
  cp "$DIR/assets/icon.png" "$APPDIR/tartantis.png"
  cp "$DIR/assets/icon.png" "$APPDIR/.DirIcon"
else
  cat > "$APPDIR/tartantis.svg" << 'SVG'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" fill="#1c1712" rx="10"/>
  <text x="32" y="46" font-size="38" text-anchor="middle" fill="#d4a843">⚔</text>
</svg>
SVG
  command -v convert &>/dev/null && convert "$APPDIR/tartantis.svg" "$APPDIR/tartantis.png" 2>/dev/null || true
fi

# ── Gera AppImage ────────────────────────────────────────────────
echo -e "${DIM}  → Gerando AppImage…${RESET}"
# appimagetool também é AppImage — extrai para rodar sem FUSE no CI/sandbox
TOOL_SQUASH="$DIR/.appimagetool-squashfs"
if [ ! -d "$TOOL_SQUASH" ]; then
  _TMP="$(mktemp -d)"
  pushd "$_TMP" > /dev/null
  "$TOOL" --appimage-extract 2>/dev/null
  mv squashfs-root "$TOOL_SQUASH"
  popd > /dev/null
  rm -rf "$_TMP"
fi
ARCH=x86_64 "$TOOL_SQUASH/AppRun" "$(realpath "$APPDIR")" "$(realpath "$OUTPUT")" 2>/dev/null
rm -rf "$APPDIR"

if [ -f "$OUTPUT" ]; then
  chmod +x "$OUTPUT"
  echo -e "${GREEN}${BOLD}  ✓ Gerado: $(basename "$OUTPUT")${RESET}"
  echo -e "${DIM}  → Distribua apenas este arquivo .AppImage${RESET}"
else
  echo "Erro ao gerar AppImage."
  exit 1
fi
echo ""
