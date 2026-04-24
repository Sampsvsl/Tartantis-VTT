import os
import sys
import zipfile
import time
import argparse
from pathlib import Path
import subprocess

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
except Exception:
    tk = None
    filedialog = None
    messagebox = None


def _show_error(msg: str):
    if tk and messagebox:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Erro", msg)
        return
    print(msg)

def create_shortcut(target, shortcut_path, icon_path=None):
    vbs = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{shortcut_path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{target}"
oLink.WorkingDirectory = "{Path(target).parent}"
'''
    if icon_path:
        vbs += f'oLink.IconLocation = "{icon_path}"\n'
    vbs += 'oLink.Save\n'
    vbs_path = Path(os.environ.get('TEMP', '.')) / 'createshortcut.vbs'
    with open(vbs_path, 'w', encoding='utf-8') as f:
        f.write(vbs)
    try:
        subprocess.run(['cscript', '//Nologo', str(vbs_path)], creationflags=0x08000000)
    except:
        pass
    finally:
        try:
            os.remove(str(vbs_path))
        except:
            pass


def _wait_pid_exit(pid: int, timeout_sec: int = 60):
    if pid <= 0:
        return
    deadline = time.time() + max(1, timeout_sec)
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
            time.sleep(0.35)
        except OSError:
            return


def _extract_payload(payload_zip: Path, dest_path: Path):
    last_err = None
    for _ in range(20):
        try:
            with zipfile.ZipFile(payload_zip, 'r') as zf:
                zf.extractall(dest_path)
            return
        except Exception as e:
            last_err = e
            time.sleep(0.4)
    raise RuntimeError(f"Falha ao extrair arquivos: {last_err}")


def _run_auto_update(payload_zip: Path, install_dir: Path, wait_pid: int = 0, restart: bool = True):
    install_dir.mkdir(parents=True, exist_ok=True)
    _wait_pid_exit(wait_pid)
    _extract_payload(payload_zip, install_dir)
    target_exe = install_dir / 'TartantisVTT.exe'
    if restart and target_exe.exists():
        subprocess.Popen([str(target_exe)], creationflags=0x08000000)

def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--update-dir', default='')
    parser.add_argument('--wait-pid', type=int, default=0)
    parser.add_argument('--no-restart', action='store_true')
    args, _ = parser.parse_known_args()
    
    if not getattr(sys, 'frozen', False):
        _show_error("Instalador deve ser rodado empacotado.")
        return
        
        
    meipass = Path(getattr(sys, '_MEIPASS', '.'))
    payload_zip = meipass / 'payload.zip'
    
    if not payload_zip.exists():
        _show_error("Arquivo payload.zip não encontrado no instalador.")
        return

    # Modo atualização silenciosa (usado pelo launcher)
    if args.update_dir:
        try:
            _run_auto_update(
                payload_zip,
                Path(args.update_dir),
                wait_pid=args.wait_pid,
                restart=not args.no_restart,
            )
        except Exception:
            # Fallback para modo interativo com mensagem de erro
            _show_error("Falha na atualização automática. Tente instalar manualmente.")
        return

    if not (tk and filedialog and messagebox):
        _show_error("Tkinter não disponível para modo instalador interativo.")
        return

    root = tk.Tk()
    root.withdraw()
        
    desktop_dir = Path(os.path.expanduser('~')) / 'Desktop'
    
    install_dir = filedialog.askdirectory(
        title="Selecione a pasta para instalar o Tartantis VTT",
        initialdir=str(desktop_dir.parent)
    )
    
    if not install_dir:
        return 
        
    dest_path = Path(install_dir) / 'Tartantis VTT'
    try:
        dest_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível criar a pasta:\n{e}")
        return
        
    try:
        _extract_payload(payload_zip, dest_path)
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao extrair os arquivos:\n{e}")
        return
        
    target_exe = dest_path / 'TartantisVTT.exe'
    icon_ico = dest_path / 'assets' / 'icon.ico'
    shortcut_path = desktop_dir / 'Tartantis VTT.lnk'
    
    if target_exe.exists():
        create_shortcut(str(target_exe), str(shortcut_path), str(icon_ico) if icon_ico.exists() else None)
            
    messagebox.showinfo("Sucesso", f"O Tartantis VTT foi instalado com sucesso em:\n{dest_path}")
    
if __name__ == '__main__':
    main()
