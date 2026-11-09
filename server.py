"""Single-learner classroom. Serves files and saves work; never executes learner code."""
import argparse
import hashlib
import json
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from course_files import CourseError, badge_path, load_catalog
from tutor import Tutor, TutorError
from lesson_updates import LessonUpdates

ROOT = Path(__file__).resolve().parent
DEFAULT_APPEARANCE = {'theme': 'amethyst', 'reading_size': 16, 'editor_size': 15}
CUSTOM_COLORS = {'accent', 'inline', 'keyword', 'string', 'number', 'comment'}
APPEARANCE_CHOICES = {
    'theme': ('amethyst', 'forest', 'ember', 'slate'),
    'reading_size': (14, 16, 18, 20),
    'editor_size': (13, 15, 17, 19),
}


def timestamp():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()


def initialize(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS appearance (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                theme TEXT NOT NULL, reading_size INTEGER NOT NULL, editor_size INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS appearance_colors (
                id INTEGER PRIMARY KEY CHECK (id = 1), colors TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS lesson_updates (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                checked TEXT NOT NULL, pending TEXT NOT NULL, successful INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS drafts (
                mission TEXT PRIMARY KEY, code TEXT NOT NULL,
                revision INTEGER NOT NULL, updated TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS completions (
                mission TEXT PRIMARY KEY, code TEXT NOT NULL,
                completed TEXT NOT NULL, version INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY, mission TEXT NOT NULL,
                code TEXT NOT NULL, reason TEXT NOT NULL, created TEXT NOT NULL);
        ''')


def catalog(path=None):
    return load_catalog(path or ROOT / 'content' / 'catalog.json')


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        server = args[2]
        super().__init__(*args, directory=str(server.assets), **kwargs)

    def log_message(self, format, *args):
        # A windowed executable has no stderr console.
        import logging
        logging.getLogger('workshop.http').info(format, *args)

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'same-origin')
        self.send_header('Cache-Control', 'no-store' if self.path.startswith('/api/') else 'no-cache')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; worker-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; object-src 'none'")
        super().end_headers()

    def respond(self, value, status=200):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def allowed(self):
        host = urlsplit('http://' + self.headers.get('Host', '')).hostname
        if host not in self.server.allowed_hosts:
            self.respond({'error': 'This hostname is not enabled for this classroom.'}, 403)
            return False
        return True

    def state(self):
        with connect(self.server.database) as db:
            return {
                'drafts': {r['mission']: dict(r) for r in db.execute('SELECT * FROM drafts')},
                'completions': {r['mission']: dict(r) for r in db.execute('SELECT * FROM completions')},
            }

    def appearance(self):
        with connect(self.server.database) as db:
            row = db.execute('''
                SELECT theme, reading_size, editor_size, colors FROM appearance
                LEFT JOIN appearance_colors USING (id) WHERE appearance.id = 1
            ''').fetchone()
        if not row:
            return {**DEFAULT_APPEARANCE, 'colors': {}}
        return {**row, 'colors': json.loads(row['colors'] or '{}')}

    def save_appearance(self, values):
        if set(values) - {'colors'} != set(DEFAULT_APPEARANCE) or any(
            type(values[name]) is not type(default) or values[name] not in APPEARANCE_CHOICES[name]
            for name, default in DEFAULT_APPEARANCE.items()
        ):
            raise ValueError('Choose an available palette and text size.')
        colors = values.get('colors')
        if 'colors' in values and (
            not isinstance(colors, dict) or colors.keys() - CUSTOM_COLORS or any(
                not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color)
                for color in colors.values()
            )
        ):
            raise ValueError('Choose valid custom colors.')
        with connect(self.server.database) as db:
            db.execute('''
                INSERT INTO appearance VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET theme=excluded.theme,
                    reading_size=excluded.reading_size, editor_size=excluded.editor_size
            ''', (values['theme'], values['reading_size'], values['editor_size']))
            if colors is not None:
                db.execute('''
                    INSERT INTO appearance_colors VALUES (1, ?)
                    ON CONFLICT(id) DO UPDATE SET colors=excluded.colors
                ''', (json.dumps(colors),))
        return self.appearance()

    def do_GET(self):
        if not self.allowed():
            return
        route = urlsplit(self.path).path
        if route.startswith('/api/tutor/'):
            if not self.tutor_allowed():
                return
            try:
                if route == '/api/tutor/settings':
                    self.respond(self.server.tutor.public_settings())
                elif route.startswith('/api/tutor/history/'):
                    mission_id = route.removeprefix('/api/tutor/history/')
                    self.respond({'messages': self.server.tutor.history(mission_id)})
                else:
                    self.respond({'error': 'Unknown tutor endpoint.'}, 404)
            except (TutorError, OSError, sqlite3.Error):
                self.respond({'error': 'Could not load tutor settings or history.'}, 400)
        elif route.startswith('/api/badges/'):
            chapter_id = route.removeprefix('/api/badges/')
            if chapter_id not in {chapter['id'] for chapter in self.server.course['chapters']}:
                self.respond({'error': 'Unknown chapter.'}, 404)
                return
            path = badge_path(self.server.catalog_path or ROOT / 'content' / 'catalog.json', chapter_id)
            try:
                body = path.read_bytes() if path else b''
            except OSError:
                body = b''
            if not body.startswith(b'\x89PNG\r\n\x1a\n'):
                self.respond({'error': 'No badge artwork.'}, 404)
                return
            self.send_response(200)
            self.send_header('Content-Type', 'image/png')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif route == '/api/grimoire':
            try:
                path = self.server.catalog_path or ROOT / 'content' / 'catalog.json'
                document = json.loads((Path(path).parent / 'grimoire.json').read_text(encoding='utf-8'))
                self.respond(document)
            except (OSError, ValueError):
                self.respond({'entries': []})
        elif route == '/api/bootstrap':
            try:
                course = catalog(self.server.catalog_path)
                self.server.course = course
            except CourseError as error:
                self.respond({'error': str(error)}, 400)
                return
            course = json.loads(json.dumps(course))
            for mission in course['missions']:
                mission.pop('reference', None)
            self.respond({'course': course, 'state': self.state(), 'token': self.server.token, 'appearance': self.appearance()})
        elif route.startswith('/api/reference/'):
            mission_id = route.removeprefix('/api/reference/')
            mission = next((m for m in self.server.course['missions'] if m['id'] == mission_id), None)
            if not mission:
                self.respond({'error': 'Unknown mission.'}, 404)
                return
            with connect(self.server.database) as db:
                completed = db.execute('SELECT code,version FROM completions WHERE mission=?', (mission_id,)).fetchone()
                latest = db.execute("SELECT code FROM snapshots WHERE mission=? AND reason='passed submission' ORDER BY id DESC LIMIT 1", (mission_id,)).fetchone()
            if not completed:
                self.respond({'error': 'Pass this mission to unlock its reference solution.'}, 403)
            elif not mission.get('reference'):
                self.respond({'available': False})
            else:
                self.respond({'available': True, 'reference': mission['reference'], 'submitted_code': latest['code'] if latest else completed['code']})
        elif route == '/api/export':
            with connect(self.server.database) as db:
                snapshots = [dict(r) for r in db.execute('SELECT * FROM snapshots ORDER BY id')]
            self.respond({'format': 1, 'exported': timestamp(), **self.state(), 'snapshots': snapshots})
        elif route.startswith('/api/'):
            self.respond({'error': 'Unknown endpoint.'}, 404)
        else:
            super().do_GET()

    def tutor_allowed(self):
        if self.client_address[0] not in ('127.0.0.1', '::1') or not secrets.compare_digest(self.headers.get('X-Workshop-Token', ''), self.server.token):
            self.respond({'error': 'Tutor access is available only on this computer. Reload the workshop.'}, 403)
            return False
        return True

    def list_directory(self, path):
        self.send_error(404)
        return None

    def do_POST(self):
        if not self.allowed():
            return
        origin = self.headers.get('Origin')
        expected = 'http://' + self.headers.get('Host', '')
        if (origin and origin != expected) or not secrets.compare_digest(self.headers.get('X-Workshop-Token', ''), self.server.token):
            self.respond({'error': 'Reload the classroom before saving.'}, 403)
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 250_000:
                raise ValueError('Request is empty or too large.')
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError('Expected an object.')
            route = urlsplit(self.path).path
            if route in ('/api/lessons/check', '/api/lessons/install'):
                updates = self.server.lesson_updates
                if not updates.supported(self.server.course['id']):
                    self.respond({'supported': False})
                    return
                try:
                    result = updates.check(manual=body.get('manual') is True) if route.endswith('/check') else updates.install()
                except OSError:
                    self.respond({'error': 'Could not reach GitHub or write the lesson files. Try again.'}, 503)
                    return
                self.respond({'supported': True, **result})
                return
            if route == '/api/appearance':
                self.respond(self.save_appearance(body))
                return
            if route == '/api/desktop/leave' and hasattr(self.server, 'desktop_callback'):
                self.respond(self.server.desktop_callback(body))
                return
            if route.startswith('/api/tutor/'):
                if not self.tutor_allowed():
                    return
                try:
                    if route == '/api/tutor/settings':
                        result = self.server.tutor.save_settings(body)
                    elif route == '/api/tutor/test':
                        result = self.server.tutor.test_connection()
                    elif route == '/api/tutor/chat':
                        mission = next((m for m in self.server.course['missions'] if m['id'] == body.get('mission')), None)
                        if not mission:
                            raise TutorError('Unknown lesson.')
                        result = self.server.tutor.chat(body, mission, self.server.database)
                    else:
                        self.respond({'error': 'Unknown tutor endpoint.'}, 404)
                        return
                    self.respond(result)
                except TutorError as error:
                    self.respond({'error': str(error)}, 400)
                except (OSError, sqlite3.Error, TypeError, AttributeError):
                    self.respond({'error': 'The tutor could not save or read its settings or conversation. Your lesson code is unchanged.'}, 500)
                return
            course = self.server.course
            missions = {m['id']: m for m in course['missions']}
            mission = missions.get(body.get('mission'))
            code = body.get('code')
            if not mission or not isinstance(code, str) or len(code) > 100_000:
                raise ValueError('Unknown mission or invalid code.')
            route = urlsplit(self.path).path
            if route not in ('/api/save', '/api/submit', '/api/reset', '/api/restore'):
                self.respond({'error': 'Unknown endpoint.'}, 404)
                return
            with connect(self.server.database) as db:
                db.execute('BEGIN IMMEDIATE')
                previous = db.execute('SELECT * FROM drafts WHERE mission=?', (mission['id'],)).fetchone()
                revision = previous['revision'] if previous else 0
                if body.get('revision') != revision:
                    self.respond({'error': 'A different tab changed this mission. Download your code, then reload to get the saved version.'}, 409)
                    return
                if route == '/api/reset':
                    db.execute('INSERT INTO snapshots(mission,code,reason,created) VALUES(?,?,?,?)', (mission['id'], code, 'before reset', timestamp()))
                    code = mission['starter']
                elif route == '/api/restore':
                    saved = db.execute("SELECT code FROM snapshots WHERE mission=? AND reason='before reset' ORDER BY id DESC LIMIT 1", (mission['id'],)).fetchone()
                    if not saved:
                        raise ValueError('No reset backup exists for this mission yet.')
                    db.execute('INSERT INTO snapshots(mission,code,reason,created) VALUES(?,?,?,?)', (mission['id'], code, 'before restore', timestamp()))
                    code = saved['code']
                elif route == '/api/submit':
                    if body.get('version') != mission['version'] or body.get('passed') != len(mission['tests']) or body.get('digest') != hashlib.sha256(code.encode()).hexdigest():
                        raise ValueError('Run all submission checks again before submitting.')
                    completed = {r[0] for r in db.execute('SELECT mission FROM completions')}
                    if any(p not in completed for p in mission.get('prerequisites', [])):
                        raise ValueError('Complete the preceding mission first.')
                    db.execute('INSERT OR IGNORE INTO completions VALUES(?,?,?,?)', (mission['id'], code, timestamp(), mission['version']))
                    db.execute('INSERT INTO snapshots(mission,code,reason,created) VALUES(?,?,?,?)', (mission['id'], code, 'passed submission', timestamp()))
                revision += 1
                db.execute('INSERT INTO drafts VALUES(?,?,?,?) ON CONFLICT(mission) DO UPDATE SET code=excluded.code,revision=excluded.revision,updated=excluded.updated', (mission['id'], code, revision, timestamp()))
            self.respond({'code': code, 'revision': revision, 'state': self.state()})
        except (ValueError, TypeError, KeyError) as exc:
            self.respond({'error': str(exc)}, 400)
        except sqlite3.Error:
            self.respond({'error': 'Could not save to the progress database. Your editor still has your code; download it before closing.'}, 500)


def make_server(host='127.0.0.1', port=8765, database=None, allowed_hosts=(), catalog_path=None, assets=None):
    course = catalog(catalog_path)
    database = database or ROOT / 'data' / 'workshop.sqlite3'
    initialize(Path(database))
    server = ThreadingHTTPServer((host, port), Handler)
    server.database = database
    server.tutor = Tutor(database)
    server.catalog_path = catalog_path
    server.lesson_updates = LessonUpdates(catalog_path or ROOT / 'content' / 'catalog.json', database, connect)
    server.course = course
    server.assets = assets or ROOT / 'dist'
    server.token = secrets.token_urlsafe(32)
    server.allowed_hosts = {'127.0.0.1', 'localhost', *allowed_hosts}
    return server


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default=8765, type=int)
    parser.add_argument('--allowed-host', action='append', default=[])
    args = parser.parse_args()
    if args.host != '127.0.0.1' and not args.allowed_host:
        parser.error('For LAN use, supply --allowed-host with the server IP or hostname clients will use.')
    httpd = make_server(args.host, args.port, allowed_hosts=args.allowed_host)
    print(f'Syntaxia: http://127.0.0.1:{args.port}', flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
