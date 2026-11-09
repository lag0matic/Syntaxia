"""Build a Rust/Tauri window with the existing isolated local Python service."""
from pathlib import Path
import shutil,subprocess,sys
r=Path(__file__).resolve().parent
subprocess.run(['npm.cmd','run','build'],cwd=r,check=True)
subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onefile','--console',
 '--name','Syntaxia Service','--distpath',str(r/'desktop-build/service'),
 '--workpath',str(r/'desktop-build/service-work'),'--specpath',str(r/'desktop-build'),
 '--add-data',f'{r/"dist"};dist',str(r/'rust_service.py')],cwd=r,check=True)
subprocess.run(['cargo','build','--release','--manifest-path','src-tauri/Cargo.toml'],cwd=r,check=True)
shutil.copy2(r/'desktop-build/service/Syntaxia Service.exe',r/'Syntaxia Service.exe')
shutil.copy2(r/'src-tauri/target/release/python-workshop.exe',r/'Syntaxia.exe')
print('Installed Rust launcher and local service. External content/data unchanged.')
