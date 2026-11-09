"""Run with .desktop-venv/Scripts/python.exe after npm run build."""
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parent
subprocess.run([
    sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
    '--onefile', '--windowed', '--name', 'Syntaxia',
    '--icon', str(root / 'assets' / 'workshop-app.ico'),
    '--distpath', str(root / 'desktop-build' / 'output'),
    '--workpath', str(root / 'desktop-build' / 'work'),
    '--specpath', str(root / 'desktop-build'),
    '--add-data', f'{root / "dist"};dist',
    '--add-data', f'{root / "assets"};assets', str(root / 'desktop.py'),
], cwd=root, check=True)
shutil.copy2(root / 'desktop-build' / 'output' / 'Syntaxia.exe', root / 'Syntaxia.exe')
print('Built Syntaxia.exe. Content and progress remain external.')
