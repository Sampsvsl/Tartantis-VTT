import zipfile, os, sys

def main():
    if len(sys.argv) < 4:
        print("Uso: zipper.py <root_dir> <exe_file> <out_zip>")
        sys.exit(1)
        
    root_dir = sys.argv[1]
    exe_file = sys.argv[2]
    out_zip = sys.argv[3]
    
    with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Adiciona as pastas principais (exceto data que tem dados do usuário)
        for d in ['app', 'core', 'assets']:
            abs_d = os.path.join(root_dir, d)
            if os.path.exists(abs_d):
                for root, dirs, files in os.walk(abs_d):
                    for file in files:
                        if file.endswith('.pyc') or '__pycache__' in root:
                            continue
                        ap = os.path.join(root, file)
                        # Caminho relativo para dentro do zip
                        rp = os.path.relpath(ap, root_dir)
                        zipf.write(ap, rp)
        
        # Adiciona o executável do engine na raiz do zip
        zipf.write(exe_file, 'TartantisVTT.exe')

if __name__ == '__main__':
    main()
