#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  Tartantis VTT — Instalador Universal
#
#  Funciona em: Linux, macOS
#  Para Windows: execute windows/build.bat
#
#  Uso:
#    bash install.sh          → executa direto (dev / teste)
#    bash install.sh --build  → gera TartantisVTT-x86_64.AppImage
#    bash install.sh --run    → só inicia o servidor (sem build)
# ═══════════════════════════════════════════════════════════════════

set -e

BOLD="\033[1m"; GOLD="\033[33m"; GREEN="\033[32m"; RED="\033[31m"; DIM="\033[2m"; RESET="\033[0m"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=3000
MODE="${1:-}"

_header() {
  echo ""
  echo -e "${GOLD}${BOLD}  ⚔  Tartantis VTT${RESET}"
  echo -e "${DIM}  ─────────────────────────────────────${RESET}"
}

_ok()   { echo -e "${GREEN}  ✓ $1${RESET}"; }
_err()  { echo -e "${RED}  ✗ $1${RESET}"; exit 1; }
_info() { echo -e "${DIM}  → $1${RESET}"; }

_header

# ── Verifica Python3 ──────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  _err "Python3 não encontrado. Instale com:\n  Ubuntu/Debian: sudo apt install python3\n  Arch: sudo pacman -S python\n  macOS: brew install python3"
fi
PY_VER=$(python3 -c "import sys;print(f'{sys.version_info.major}.{sys.version_info.minor}')")
_ok "Python $PY_VER encontrado"

# ── Garante que a pasta data existe ──────────────────────────────
mkdir -p "$DIR/data"
_ok "Pasta data/ pronta"

# ── Modo --build: gera AppImage ───────────────────────────────────
if [ "$MODE" = "--build" ]; then
  _info "Iniciando build do AppImage..."
  if [ ! -f "$DIR/build-linux.sh" ]; then
    _err "build-linux.sh não encontrado. Rode install.sh a partir da pasta TartantisVTT/."
  fi
  bash "$DIR/build-linux.sh"
  exit 0
fi

# ── Modo --run ou padrão: inicia o servidor ───────────────────────
PIDFILE="$DIR/.tvtt.pid"
LOGFILE="$DIR/.tvtt.log"

# Mata instância anterior
if [ -f "$PIDFILE" ]; then
  OLD=$(cat "$PIDFILE")
  kill "$OLD" 2>/dev/null || true
  rm -f "$PIDFILE"
fi

# Abre porta no firewall em background
_open_firewall() {
  if command -v ufw &>/dev/null; then
    sudo ufw allow ${PORT}/tcp 2>/dev/null || true
  elif command -v firewall-cmd &>/dev/null; then
    sudo firewall-cmd --permanent --add-port=${PORT}/tcp 2>/dev/null && sudo firewall-cmd --reload 2>/dev/null || true
  elif command -v iptables &>/dev/null; then
    sudo iptables -I INPUT -p tcp --dport ${PORT} -j ACCEPT 2>/dev/null || true
  fi
}
_open_firewall &

# Inicia servidor
cd "$DIR"
nohup python3 core/server.py >"$LOGFILE" 2>&1 &
SRV_PID=$!
echo "$SRV_PID" > "$PIDFILE"
_info "Servidor iniciado (PID $SRV_PID)"

# Aguarda servidor
for i in $(seq 1 20); do
  if nc -z 127.0.0.1 $PORT 2>/dev/null || curl -sf "http://127.0.0.1:${PORT}/api/info" -o /dev/null 2>/dev/null; then
    break
  fi
  sleep 0.4
done

if ! kill -0 "$SRV_PID" 2>/dev/null; then
  _err "Falha ao iniciar servidor. Log: $LOGFILE"
fi

# Obtém IP local
LOCAL_IP=$(python3 -c "
import socket
try:
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(('8.8.8.8',80))
    print(s.getsockname()[0]); s.close()
except: print('127.0.0.1')
" 2>/dev/null || echo "127.0.0.1")

URL="http://${LOCAL_IP}:${PORT}"
_ok "Servidor rodando em ${URL}"
echo ""
echo -e "${GOLD}${BOLD}  Jogadores acessam: ${URL}${RESET}"
echo ""

# Abre browser (modo app)
for cmd in chromium chromium-browser google-chrome google-chrome-stable; do
  if command -v "$cmd" &>/dev/null; then
    "$cmd" --app="${URL}/portal.html" --window-size=1280,820 >/dev/null 2>&1 &
    exit 0
  fi
done
if command -v firefox &>/dev/null; then firefox "${URL}/portal.html" >/dev/null 2>&1 & exit 0; fi
if command -v open &>/dev/null;    then open    "${URL}/portal.html" >/dev/null 2>&1 & exit 0; fi
if command -v xdg-open &>/dev/null; then xdg-open "${URL}/portal.html" >/dev/null 2>&1 & exit 0; fi

echo -e "${DIM}  Nenhum browser encontrado. Acesse manualmente: ${URL}/portal.html${RESET}"
