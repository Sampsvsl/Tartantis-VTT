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

if command -v zenity &>/dev/null; then
  zenity --info --title="Tartantis VTT" --text="O Servidor do Tartantis VTT está rodando!\nO jogo foi aberto no seu navegador padrão.\n\nFeche esta janela (ou clique OK) para desligar o servidor."
else
  python3 -c "import tkinter as tk; root=tk.Tk(); root.title('Tartantis VTT'); root.geometry('350x120'); tk.Label(root, text='O Servidor do Tartantis VTT está rodando!\nO jogo foi aberto no navegador.\n\nFeche esta janela para desligar.', justify='center').pack(expand=True); root.mainloop()" 2>/dev/null
fi

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
ARCH=x86_64 "$TOOL" "$APPDIR" "$OUTPUT" 2>/dev/null
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
