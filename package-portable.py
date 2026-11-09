"""Build and smoke-test a clean Windows x64 Syntaxia archive."""
from contextlib import closing
from datetime import date, datetime
from pathlib import Path
import argparse
import hashlib
import json
import os
from queue import Queue
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import threading
import tomllib
from urllib.request import Request, ProxyHandler, build_opener
from zipfile import ZipFile, ZIP_DEFLATED

from course_files import course_content, open_course, load_catalog

ROOT = Path(__file__).resolve().parent
START_HERE = """Syntaxia - portable Windows edition

1. Right-click the ZIP and choose Extract All. Open the extracted Syntaxia folder.
2. Double-click Syntaxia.exe. Keep Syntaxia Service.exe and content beside it.
3. Start with Your first Python program. Run shows output, Test checks examples,
   and Submit records completion. The Grimoire opens from the top bar.

This build is for 64-bit Windows on Intel/AMD PCs. No Python, Rust, or Node
installation is required. The app uses Microsoft Edge WebView2, normally
already installed on Windows 11. If Windows reports it missing, get the
Evergreen Runtime from Microsoft:
https://developer.microsoft.com/microsoft-edge/webview2/

Lessons, grading and the Grimoire work offline. For the optional AI tutor,
enter your own API key under Settings > Tutor and test the connection.
Choose palettes and text sizes under Settings > Appearance. Journey shows
your XP, badges, and completed lessons. Failed checks show the sample input.

Updating an existing copy

1. Close Syntaxia. You can copy its data folder elsewhere for a backup.
2. Extract this ZIP to a temporary folder. Copy the contents of the new
   Syntaxia folder into your existing Syntaxia folder and replace matching
   files. Keep the existing data folder in place.
3. Open Syntaxia.exe under the same Windows account. Your progress, drafts,
   tutor chats, and saved key stay in data. Windows encrypts the saved key
   for that account on that PC.

This ZIP contains no learner data or API keys. Keep the app in a writable
folder, such as Documents, and launch it after extraction.
This is an unsigned personal build.
"""

def assert_x64(path):
    with path.open('rb') as handle:
        handle.seek(0x3C)
        offset, = struct.unpack('<I', handle.read(4))
        handle.seek(offset)
        if handle.read(4) != b'PE\0\0' or handle.read(2) != b'\x64\x86':
            raise ValueError(f'Not an x64 Windows executable: {path.name}')

def notices(archive):
    """Carry the locally available distribution notices, not development files."""
    known = {
        'Python-LICENSE.txt': Path(sys.base_prefix) / 'LICENSE.txt',
        'Editor-licenses.txt': ROOT / 'dist/app.js.LEGAL.txt',
        'Pyodide-notice.txt': ROOT / 'dist/vendor/README.txt',
    }
    for name, path in known.items():
        if path.is_file():
            archive.write(path, 'Syntaxia/Notices/' + name)
    for path in (ROOT / 'node_modules/pyodide').glob('LICENSE*'):
        if path.is_file():
            archive.write(path, 'Syntaxia/Notices/Pyodide-' + path.name)
    lock = ROOT / 'src-tauri/Cargo.lock'
    if not lock.is_file():
        return
    crates = tomllib.loads(lock.read_text(encoding='utf-8'))['package']
    roots = list((Path.home() / '.cargo/registry/src').glob('index.crates.io-*'))
    for crate in crates:
        if not crate.get('source', '').startswith('registry+'):
            continue
        name = crate['name'] + '-' + crate['version']
        for registry in roots:
            folder = registry / name
            if folder.is_dir():
                paths = {p for pattern in ('LICENSE*', 'COPYING*', 'NOTICE*') for p in folder.glob(pattern)}
                for path in sorted(paths):
                    if path.is_file() and path.stat().st_size <= 1_000_000:
                        archive.write(path, f'Syntaxia/Notices/Rust/{name}/{path.name}')
                break

def clean_env():
    env = os.environ.copy()
    for key in list(env):
        if key.upper().startswith(('OPENAI_', 'PYTHON')):
            env.pop(key)
    env['PATH'] = str(Path(env.get('SystemRoot', r'C:\Windows')) / 'System32')
    return env

def verify(archive_path, test_dir, expected):
    with ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        assert not any(name.startswith('Syntaxia/data/') for name in archive.namelist())
        archive.extractall(test_dir)
    app = test_dir / 'Syntaxia'
    env = clean_env()
    report = test_dir / 'launcher-report.json'
    subprocess.run([str(app/'Syntaxia.exe'), '--check-report', str(report)],
                   cwd=test_dir, env=env, check=True, timeout=30,
                   creationflags=subprocess.CREATE_NO_WINDOW)
    assert json.loads(report.read_text(encoding='utf-8'))['missions'] == expected
    assert not (app/'data').exists()
    with subprocess.Popen([str(app/'Syntaxia Service.exe'), '--course', str(app/'workshop.course.json')],
                          cwd=test_dir, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW) as service:
        try:
            line = Queue()
            threading.Thread(target=lambda: line.put(service.stdout.readline()), daemon=True).start()
            ready = json.loads(line.get(timeout=30))
            assert ready['kind'] == 'ready', ready
            base = f"http://127.0.0.1:{ready['port']}"
            opener = build_opener(ProxyHandler({}))
            def get(path, token=None):
                req = Request(base + path, headers={'X-Workshop-Token':token} if token else {})
                with opener.open(req, timeout=10) as response:
                    return response.read()
            loaded = json.loads(get('/api/bootstrap'))
            assert loaded['state']['completions'] == {} and loaded['state']['drafts'] == {}
            assert len(loaded['course']['missions']) == expected
            assert loaded['course']['missions'][0]['id'] == 'py-orientation-first-run'
            assert loaded['course']['missions'][0]['orientation'] is True
            html = get('/')
            assert b'<title>Syntaxia</title>' in html
            assert b'id="open-settings"' in html and b'id="open-journey"' in html
            app_js = get('/app.js')
            assert b'inline-code' in app_js and b'Sample input' in app_js
            assert b'Individual colors' in app_js
            assert get('/vendor/pyodide/pyodide.asm.wasm').startswith(b'\0asm')
            settings = json.loads(get('/api/tutor/settings', loaded['token']))
            assert settings['has_key'] is False and 'encrypted_key' not in settings
            assert len(json.loads(get('/api/grimoire'))['entries']) > 0
            for chapter in loaded['course']['chapters']:
                assert get('/api/badges/' + chapter['id']).startswith(b'\x89PNG\r\n\x1a\n')
            service.stdin.write(b'quit\n'); service.stdin.flush()
            assert service.wait(timeout=10) == 0
        finally:
            if service.poll() is None:
                service.stdin.close()
                try: service.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    service.kill()
                    service.wait(timeout=3)
    with closing(sqlite3.connect(app/'data/workshop.sqlite3')) as db:
        assert db.execute('SELECT COUNT(*) FROM completions').fetchone()[0] == 0
    print('Clean extraction passed: launcher, local service, 0 progress, no key, offline runtime, graceful service exit.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--releases', type=Path, default=ROOT.parent/'releases')
    args = parser.parse_args()
    course = open_course(ROOT/'workshop.course.json')
    expected = len(load_catalog(course.catalog)['missions'])
    files = {'Syntaxia.exe':ROOT/'Syntaxia.exe', 'Syntaxia Service.exe':ROOT/'Syntaxia Service.exe'}
    for path in files.values():
        assert_x64(path)
    for name in course_content(course.catalog):
        files['content/' + name] = course.catalog.parent / name
    args.releases.mkdir(parents=True, exist_ok=True)
    output = args.releases / f'Syntaxia-Windows-x64-{date.today():%Y%m%d}.zip'
    if output.exists():
        output = args.releases / f'Syntaxia-Windows-x64-{datetime.now():%Y%m%d-%H%M%S}.zip'
    with tempfile.TemporaryDirectory(prefix='syntaxia-package-', dir=args.releases) as temp:
        temp = Path(temp)
        candidate = temp/'portable.zip'
        with ZipFile(candidate,'x',compression=ZIP_DEFLATED,compresslevel=9,strict_timestamps=False) as archive:
            archive.writestr('Syntaxia/README.txt', START_HERE)
            archive.writestr('Syntaxia/workshop.course.json', json.dumps({
                'format':'python-workshop-course','version':1,
                'catalog':'content/catalog.json','progress':'data/workshop.sqlite3',
            },indent=2)+'\n')
            for name,path in files.items():
                archive.write(path,'Syntaxia/'+name)
            notices(archive)
        verify(candidate,temp/'Fresh Syntaxia package',expected)
        with candidate.open('rb') as source, output.open('xb') as destination:
            shutil.copyfileobj(source,destination)
    print('Archive:', output)
    print('Size:', f'{output.stat().st_size/1_000_000:.1f} MB')
    with output.open('rb') as stream:
        print('SHA256:', hashlib.file_digest(stream,'sha256').hexdigest())

if __name__ == '__main__':
    main()

