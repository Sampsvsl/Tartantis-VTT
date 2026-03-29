#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
#  Tartantis VTT — Launcher Linux
#  Abre a porta 3000, inicia o servidor e abre o browser.
#  Funciona tanto pelo terminal quanto pelo ícone do sistema.
# ═══════════════════════════════════════════════════════════

PORT=3000
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

# ── Abre a porta 3000 no firewall (como o Foundry faz) ────
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

# ── Aguarda o usuário fechar para matar o processo ───
if command -v zenity &>/dev/null; then
  zenity --info --title="Tartantis VTT" --text="O Servidor do Tartantis VTT está rodando!\nO jogo foi aberto no seu navegador padrão.\n\nFeche esta janela (ou clique OK) para desligar o servidor." 
else
  python3 -c "import tkinter as tk; root=tk.Tk(); root.title('Tartantis VTT'); root.geometry('350x120'); tk.Label(root, text='O Servidor do Tartantis VTT está rodando!\nO jogo foi aberto no navegador.\n\nFeche esta janela para desligar.', justify='center').pack(expand=True); root.mainloop()" 2>/dev/null
fi

[ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE")" 2>/dev/null
rm -f "$PIDFILE"
exit 0
