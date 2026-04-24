"""
Tartantis VTT — Windows Launcher
Abre a porta 30000 no firewall, inicia o servidor Python e abre o browser.
"""
import os
import sys
import subprocess
import socket
import time
import webbrowser
import threading
import runpy
import base64
import hashlib
import json
import re
import secrets
import shutil
import struct
import urllib.request
import urllib.parse
import platform
import http.server
import socketserver
import xmlrpc.server
import tempfile
from pathlib import Path

# --- Configuração de Caminhos ---
if getattr(sys, 'frozen', False):
    # PyInstaller --onefile: os arquivos extraídos estão junto do .exe
    EXE_DIR  = Path(sys.executable).parent
    BASE_DIR = EXE_DIR
else:
    BASE_DIR = Path(__file__).parent.parent
    EXE_DIR  = BASE_DIR

# Adiciona BASE_DIR ao path para que o pacote 'core' seja encontrado
sys.path.insert(0, str(BASE_DIR))

# Agora podemos importar o updater (mesmo que o linter reclame do caminho dinâmico)
try:
    from core import updater # type: ignore
except ImportError:
    updater = None

PORT = 30000
SERVER_SCRIPT = BASE_DIR / 'core' / 'server.py'
APP_DIR       = BASE_DIR / 'app'
LOG_FILE      = EXE_DIR / '.server.log'


def open_firewall_port(port: int):
    rule_name = f"TartantisVTT-TCP{port}"
    subprocess.run(['netsh', 'advfirewall', 'firewall', 'delete', 'rule', f'name={rule_name}'], capture_output=True)
    subprocess.run(['netsh', 'advfirewall', 'firewall', 'add', 'rule', f'name={rule_name}', 'dir=in', 'action=allow', 'protocol=TCP', f'localport={port}', 'profile=any', 'description=Tartantis VTT'], capture_output=True)


def wait_for_server(port: int, timeout: float = 12.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.5):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.3)
    return False


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


def main():
    threading.Thread(target=open_firewall_port, args=(PORT,), daemon=True).start()

    is_frozen = getattr(sys, 'frozen', False)

    if not SERVER_SCRIPT.exists():
        if sys.platform == 'win32':
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, f"Arquivo do servidor nao encontrado:\n{SERVER_SCRIPT}", "Tartantis VTT - Erro", 0x10)
        else:
            print(f"Erro: Arquivo {SERVER_SCRIPT} nao encontrado.")
        sys.exit(1)

    server_proc = None

    if is_frozen:
        f_log = open(LOG_FILE, 'w', encoding='utf-8')
        sys.stdout = f_log
        sys.stderr = f_log
        
        def run_srv():
            try:
                runpy.run_path(str(SERVER_SCRIPT), run_name='__main__')
            except Exception as e:
                import traceback
                traceback.print_exc(file=f_log)
                f_log.flush()
                
        threading.Thread(target=run_srv, daemon=True).start()
    else:
        server_proc = subprocess.Popen(
            ['python', str(SERVER_SCRIPT)],
            stderr=subprocess.STDOUT,
            stdout=open(LOG_FILE, 'w', encoding='utf-8'),
            creationflags=0x08000000 if sys.platform == 'win32' else 0
        )

    if not wait_for_server(PORT, timeout=12):
        if sys.platform == 'win32':
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, f"Falha ao iniciar o servidor na porta {PORT}.\nVerifique: {LOG_FILE}", "Tartantis VTT", 0x10)
        else:
            print(f"Falha ao iniciar o servidor. Log: {LOG_FILE}")
        
        if server_proc:
            server_proc.terminate()
        sys.exit(1)

    local_ip = get_local_ip()
    url = f"http://{local_ip}:{PORT}/portal.html"

    webbrowser.open(url)

    def open_browser_again():
        webbrowser.open(url)

    def try_pystray_gui():
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
        def on_open(icon, item): open_browser_again()
        def on_stop(icon, item): icon.stop()
        menu = pystray.Menu(
            pystray.MenuItem('Abrir no Navegador', on_open),
            pystray.MenuItem('Desligar Servidor',  on_stop),
        )
        icon = pystray.Icon('tartantis', img, 'Tartantis VTT — Rodando', menu)
        icon.run()
        return True

    def run_gui():
        import tkinter as tk
        from tkinter import messagebox
        BG, GOLD, EMBER, FG, DIM = '#12100e', '#c8a84b', '#e07b39', '#e8ddc8', '#666655'
        root = tk.Tk()
        root.title("Tartantis VTT")
        root.geometry("320x200")
        root.resizable(False, False)
        root.configure(bg=BG)

        icon_path = BASE_DIR / 'assets' / 'icon.ico'
        if icon_path.exists():
            try:
                root.iconbitmap(str(icon_path))
            except: pass

        tk.Frame(root, bg=GOLD, height=3).pack(fill='x', side='top')
        tk.Label(root, text='⚔  TARTANTIS VTT  ⚔', fg=GOLD, bg=BG,
                 font=('Georgia', 12, 'bold')).pack(pady=(14, 4))
        tk.Label(root, text='Servidor rodando · porta 30000', fg=FG, bg=BG,
                 font=('', 9)).pack()
        tk.Label(root, text=url, fg=DIM, bg=BG,
                 font=('', 8)).pack(pady=(2, 6))

        update_label = tk.Label(root, text='', fg=GOLD, bg=BG, cursor='hand2', font=('', 8, 'underline'))
        update_label.pack(pady=(0, 8))

        def _download_with_progress(url: str, out_path: Path):
            def _hook(blocks, block_size, total_size):
                if total_size <= 0:
                    return
                pct = int(min(100, (blocks * block_size * 100) / total_size))
                root.after(0, lambda: update_label.config(text=f'Baixando atualização... {pct}%'))
            urllib.request.urlretrieve(url, str(out_path), reporthook=_hook)

        def _start_auto_update(ver: str, url: str):
            try:
                if not url or not url.lower().endswith('.exe'):
                    webbrowser.open(url)
                    return
                update_label.config(text='Preparando atualização automática...')
                tmp_dir = Path(tempfile.gettempdir()) / 'TartantisVTT-updater'
                tmp_dir.mkdir(parents=True, exist_ok=True)
                installer_path = tmp_dir / f'Instalador_TartantisVTT_v{ver}.exe'
                _download_with_progress(url, installer_path)
                update_label.config(text='Atualizando... fechando app atual')
                subprocess.Popen([
                    str(installer_path),
                    '--update-dir', str(EXE_DIR),
                    '--wait-pid', str(os.getpid()),
                ], creationflags=0x08000000)
                root.after(150, root.destroy)
            except Exception:
                update_label.config(text='Falha no auto-update. Abrindo página do release...')
                try:
                    webbrowser.open('https://github.com/Sampsvsl/Tartantis-VTT/releases/latest')
                except Exception:
                    pass

        def check_updates_task():
            if not updater:
                return
            try:
                available, ver, uurl = updater.check_for_updates(BASE_DIR, platform_hint='windows')
                if available:
                    def _ask_and_handle():
                        update_label.config(text=f'Nova versão: v{ver} disponível')
                        ok = messagebox.askyesno(
                            'Atualização disponível',
                            f'Nova versão v{ver} encontrada.\n\nDeseja atualizar agora automaticamente?'
                        )
                        if ok:
                            threading.Thread(target=_start_auto_update, args=(ver, uurl), daemon=True).start()
                        else:
                            update_label.config(text=f'Nova versão: v{ver} — Clique para baixar')
                            update_label.bind('<Button-1>', lambda e: webbrowser.open(uurl))
                    root.after(0, _ask_and_handle)
            except:
                pass

        threading.Thread(target=check_updates_task, daemon=True).start()

        btns = tk.Frame(root, bg=BG)
        btns.pack()
        tk.Button(btns, text='Abrir Navegador', command=open_browser_again,
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

    if not try_pystray_gui():
        run_gui()
    os._exit(0)


if __name__ == '__main__':
    main()
