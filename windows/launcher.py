"""
Tartantis VTT — Windows Launcher
Abre a porta 3000 no firewall, inicia o servidor Python e abre o browser.
"""
import os
import sys
import subprocess
import socket
import time
import webbrowser
import threading
import runpy
import http.server
import socketserver
import urllib.request
import urllib.parse
import shutil
import struct
import hashlib
import sqlite3
import secrets
import json
import base64
import mimetypes
from pathlib import Path

PORT = 3000

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent

SERVER_SCRIPT = BASE_DIR / 'core' / 'server.py'
APP_DIR       = BASE_DIR / 'app'
LOG_FILE      = BASE_DIR / '.server.log'


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

    if is_frozen:
        f_log = open(LOG_FILE, 'w', encoding='utf-8')
        sys.stdout = f_log
        sys.stderr = f_log
        
        sys.path.insert(0, str(BASE_DIR))
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
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )

    if not wait_for_server(PORT, timeout=12):
        if sys.platform == 'win32':
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, f"Falha ao iniciar o servidor na porta {PORT}.\nVerifique: {LOG_FILE}", "Tartantis VTT", 0x10)
        else:
            print(f"Falha ao iniciar o servidor. Log: {LOG_FILE}")
        if not is_frozen:
            server_proc.terminate()
        sys.exit(1)

    local_ip = get_local_ip()
    url = f"http://{local_ip}:{PORT}/portal.html"

    webbrowser.open(url)

    if is_frozen:
        while True:
            time.sleep(1)
    else:
        server_proc.wait()


if __name__ == '__main__':
    main()


if __name__ == '__main__':
    main()
