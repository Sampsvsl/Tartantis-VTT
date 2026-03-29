import os
import sys
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import subprocess

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
        subprocess.run(['cscript', '//Nologo', str(vbs_path)], creationflags=subprocess.CREATE_NO_WINDOW)
    except:
        pass
    finally:
        try:
            os.remove(str(vbs_path))
        except:
            pass

def main():
    root = tk.Tk()
    root.withdraw() 
    
    if not getattr(sys, 'frozen', False):
        messagebox.showerror("Erro", "Instalador deve ser rodado empacotado.")
        return
        
    meipass = Path(sys._MEIPASS)
    payload_zip = meipass / 'payload.zip'
    
    if not payload_zip.exists():
        messagebox.showerror("Erro", "Arquivo payload.zip não encontrado no instalador.")
        return
        
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
        with zipfile.ZipFile(payload_zip, 'r') as zf:
            zf.extractall(dest_path)
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
