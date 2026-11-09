"""Desktop shell. Course content and learner progress remain outside the executable."""
import argparse
import ctypes
import json
import logging
import msvcrt
import os
from pathlib import Path
import subprocess
import sys
import threading
from urllib.parse import urlencode

from course_files import open_course, load_catalog
from server import make_server


def message(text):
    ctypes.windll.user32.MessageBoxW(None, str(text), 'Syntaxia', 0x40)


def confirm_close(error):
    text = (f"The workshop could not confirm that your latest code was saved.\n\n{error}"
            "\n\nClose anyway? Unsaved edits may be lost. Choose No to keep the window open and copy or download your code.")
    return ctypes.windll.user32.MessageBoxW(None, text, 'Close Syntaxia?', 0x34) == 6


def await_editor(window, closing=False, timeout=10):
    # evaluate_js itself can block while WebView2 initializes its bridge. Include
    # that wait in the deadline, not just the later Promise callback.
    complete = threading.Event()
    result = {}
    errors = []
    accepting = threading.Event()
    accepting.set()

    def saved(value):
        if accepting.is_set():
            if isinstance(value, dict):
                result.update(value)
            complete.set()

    def evaluate():
        try:
            options = json.dumps({'closing': closing})
            window.evaluate_js(
                'Promise.resolve(window.workshopDesktop ? '
                f'window.workshopDesktop.prepareLeave({options}) : {{ok: true}})',
                callback=saved)
        except Exception as error:
            if accepting.is_set():
                errors.append(error)
                complete.set()

    threading.Thread(target=evaluate, daemon=True).start()
    try:
        if not complete.wait(timeout):
            raise RuntimeError('The editor did not respond within 10 seconds.')
        if errors:
            raise RuntimeError('The editor connection is unavailable.') from errors[0]
        if not result.get('ok'):
            raise RuntimeError(result.get('message', 'Could not save your code.'))
        return result
    finally:
        accepting.clear()


class CourseLock:
    def __init__(self, database):
        database.parent.mkdir(parents=True, exist_ok=True)
        self.file = database.with_suffix('.desktop.lock').open('a+b')
        self.file.write(b'0')
        self.file.flush()
        self.file.seek(0)
        try:
            msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            self.file.close()
            raise RuntimeError('This course is already open in Syntaxia. Use its existing window.')

    def close(self):
        self.file.close()


def main():
    home = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
    parser = argparse.ArgumentParser()
    parser.add_argument('course', nargs='?', default=str(home / 'workshop.course.json'))
    parser.add_argument('--check-report', type=Path)
    args = parser.parse_args()
    course = open_course(args.course)
    if args.check_report:
        content = load_catalog(course.catalog)
        args.check_report.write_text(json.dumps({'ok': True, 'chapters': len(content['chapters']), 'missions': len(content['missions'])}), encoding='utf-8')
        return
    lock = CourseLock(course.database)
    logging.basicConfig(filename=course.database.with_suffix('.desktop.log'), level=logging.WARNING)
    import webview
    from webview.menu import Menu, MenuAction, MenuSeparator
    assets = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'dist'
    server = make_server(port=0, database=course.database, catalog_path=course.catalog, assets=assets)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    position_file = course.database.with_suffix('.desktop.json')
    position = {}
    try:
        position = json.loads(position_file.read_text(encoding='utf-8'))
        if not isinstance(position, dict):
            position = {}
    except (OSError, ValueError):
        pass
    base_url = f'http://127.0.0.1:{server.server_port}/'

    def url():
        return base_url + '?' + urlencode({'desktop': '1', 'mission': position.get('mission', '')})

    window = webview.create_window('Syntaxia', url(), width=1440, height=940, min_size=(900, 650), background_color='#141820')
    allowed_close = threading.Event()
    leaving = threading.Lock()

    def prepare(action, closing=False):
        if not leaving.acquire(blocking=False):
            return
        try:
            result = await_editor(window, closing=closing)
            if result.get('mission'):
                position['mission'] = result['mission']
                position_file.write_text(json.dumps(position), encoding='utf-8')
            action()
        except Exception as error:
            logging.exception('Desktop action failed')
            if closing:
                if confirm_close(error):
                    action()
            else:
                message(error)
        finally:
            leaving.release()

    def close():
        if allowed_close.is_set():
            return True

        def destroy():
            allowed_close.set()
            window.destroy()

        threading.Thread(target=prepare, args=(destroy, True), daemon=True).start()
        return False

    def reload_course():
        try:
            load_catalog(course.catalog)
        except Exception as error:
            message(f'Lessons could not be reloaded. Your current lesson is still open.\n\n{error}')
            return
        prepare(lambda: window.load_url(url()))

    def choose_course():
        selected = window.create_file_dialog(webview.FileDialog.OPEN, file_types=('Workshop courses (*.course.json)',))
        if selected:
            try:
                other = open_course(selected[0])
                command = [sys.executable]
                if not getattr(sys, 'frozen', False):
                    command.append(str(Path(__file__).resolve()))
                subprocess.Popen([*command, str(other.descriptor)])
            except Exception as error:
                message(error)

    window.events.closing += close
    menu = [Menu('Course', [
        MenuAction('Reload lessons', reload_course),
        MenuAction('Open another course…', choose_course),
        MenuSeparator(),
        MenuAction('Open lesson folder', lambda: os.startfile(course.catalog.parent)),
        MenuAction('Open progress folder', lambda: os.startfile(course.database.parent)),
        MenuSeparator(),
        MenuAction('Exit', window.destroy),
    ])]
    webview.settings['ALLOW_DOWNLOADS'] = True
    try:
        webview.start(gui='edgechromium', menu=menu, icon=str(assets.parent / 'assets' / 'workshop-taskbar.ico'))
    finally:
        server.shutdown()
        server.server_close()
        lock.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        logging.exception('Workshop failed to start')
        message(f'Syntaxia could not start.\n\n{error}\n\nKeep the EXE beside workshop.course.json and the content folder. The desktop app requires Microsoft Edge WebView2 Runtime.')
