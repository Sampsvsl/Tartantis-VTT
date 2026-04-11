#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  Tartantis VTT — Build macOS .app
#
#  Gera TartantisVTT.app pronto para distribuição no macOS.
#  O .app é empacotado como TartantisVTT-macOS.zip para o release.
#
#  Dependências: python3, zip
#  Uso: bash build-macos.sh
# ═══════════════════════════════════════════════════════════════════

set -e

BOLD="\033[1m"; GOLD="\033[33m"; GREEN="\033[32m"; DIM="\033[2m"; RESET="\033[0m"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="TartantisVTT"
APP_DIR="$DIR/${APP_NAME}.app"
OUTPUT="$DIR/${APP_NAME}-macOS.zip"

echo ""
echo -e "${GOLD}${BOLD}  ⚔  Tartantis VTT — Build macOS .app${RESET}"
echo -e "${DIM}  ─────────────────────────────────────${RESET}"

# ── Verifica Python3 ──────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo "Erro: python3 não encontrado."; exit 1
fi

# ── Limpa build anterior ──────────────────────────────────────────
rm -rf "$APP_DIR" "$OUTPUT"

# ── Estrutura do .app ─────────────────────────────────────────────
echo -e "${DIM}  → Montando estrutura do .app…${RESET}"
CONTENTS="$APP_DIR/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"
SHARE="$RESOURCES/tartantis"

mkdir -p "$MACOS" "$RESOURCES" "$SHARE"

# ── Copia arquivos do projeto ─────────────────────────────────────
cp -r "$DIR/app"  "$SHARE/"
cp -r "$DIR/core" "$SHARE/"
cp -r "$DIR/assets" "$SHARE/" 2>/dev/null || true
mkdir -p "$SHARE/data"

# ── Executável principal ──────────────────────────────────────────
cat > "$MACOS/${APP_NAME}" << 'EXEC'
#!/usr/bin/env bash
PORT=30000
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$SELF/../Resources/tartantis"
PIDFILE="$HOME/.tvtt.pid"
LOGFILE="$HOME/.tvtt.log"

[ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE")" 2>/dev/null; rm -f "$PIDFILE"

command -v python3 &>/dev/null || {
  osascript -e 'display alert "Tartantis VTT" message "Python3 não encontrado. Instale em python.org."'
  exit 1
}

cd "$APP"
nohup python3 core/server.py >"$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"

for i in $(seq 1 25); do
  curl -sf "http://127.0.0.1:${PORT}/api/info" -o /dev/null 2>/dev/null && break
  sleep 0.4
done

kill -0 "$(cat "$PIDFILE")" 2>/dev/null || {
  osascript -e "display alert \"Tartantis VTT\" message \"Falha ao iniciar o servidor. Log: $LOGFILE\""
  exit 1
}

LOCAL_IP=$(python3 -c "
import socket
try:
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(('8.8.8.8',80)); print(s.getsockname()[0]); s.close()
except: print('127.0.0.1')
")

URL="http://${LOCAL_IP}:${PORT}/portal.html"
open "$URL"

python3 - "$URL" <<'PYEOF'
import sys, subprocess
url = sys.argv[1]
def open_browser():
    subprocess.Popen(['open', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
if not try_tkinter(url):
    subprocess.run(['osascript', '-e',
        f'display dialog "Servidor rodando em {url}\\n\\nFeche para desligar." '
        f'buttons {{"Desligar"}} default button "Desligar" with title "Tartantis VTT"'])
PYEOF

[ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE")" 2>/dev/null
rm -f "$PIDFILE"
EXEC
chmod +x "$MACOS/${APP_NAME}"

# ── Info.plist ────────────────────────────────────────────────────
cat > "$CONTENTS/Info.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>TartantisVTT</string>
  <key>CFBundleDisplayName</key>
  <string>Tartantis VTT</string>
  <key>CFBundleIdentifier</key>
  <string>com.tartantis.vtt</string>
  <key>CFBundleVersion</key>
  <string>1.0</string>
  <key>CFBundleExecutable</key>
  <string>TartantisVTT</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleIconFile</key>
  <string>icon</string>
  <key>LSMinimumSystemVersion</key>
  <string>10.14</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
PLIST

# ── Ícone ─────────────────────────────────────────────────────────
if [ -f "$DIR/assets/icon.png" ]; then
  # Converte PNG para icns se possível (macOS tem o sips)
  if command -v sips &>/dev/null && command -v iconutil &>/dev/null; then
    ICONSET="$DIR/.iconset"
    mkdir -p "$ICONSET"
    for size in 16 32 64 128 256 512; do
      sips -z $size $size "$DIR/assets/icon.png" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null 2>&1
      sips -z $((size*2)) $((size*2)) "$DIR/assets/icon.png" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null 2>&1
    done
    iconutil -c icns "$ICONSET" -o "$RESOURCES/icon.icns" 2>/dev/null && rm -rf "$ICONSET" || true
  else
    cp "$DIR/assets/icon.png" "$RESOURCES/icon.png" 2>/dev/null || true
  fi
fi

# ── Empacota como .zip ────────────────────────────────────────────
echo -e "${DIM}  → Empacotando…${RESET}"
cd "$DIR"
zip -qr "$OUTPUT" "${APP_NAME}.app"
rm -rf "$APP_DIR"

if [ -f "$OUTPUT" ]; then
  echo -e "${GREEN}${BOLD}  ✓ Gerado: $(basename "$OUTPUT")${RESET}"
  echo -e "${DIM}  → Distribua o .zip — usuário extrai e abre o .app${RESET}"
  echo -e "${DIM}  → Primeira vez: clique com botão direito → Abrir (bypass Gatekeeper)${RESET}"
else
  echo "Erro ao gerar .zip."; exit 1
fi
echo ""
