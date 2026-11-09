"""Local lesson service owned by the Rust desktop shell; stdin closes with parent."""
import argparse
import json
import logging
import msvcrt
import sys
import threading
from pathlib import Path
from course_files import open_course, load_catalog
from server import make_server

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--course',required=True)
    parser.add_argument('--check-report',type=Path)
    args=parser.parse_args()
    course=open_course(args.course)
    if args.check_report:
        c=load_catalog(course.catalog)
        args.check_report.write_text(json.dumps({'ok':True,'shell':'Rust / Tauri','chapters':len(c['chapters']),'missions':len(c['missions'])}),encoding='utf-8')
        return
    course.database.parent.mkdir(parents=True,exist_ok=True)
    lock=course.database.with_suffix('.desktop.lock').open('a+b')
    lock.write(b'0'); lock.flush(); lock.seek(0)
    try:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    except OSError:
        raise RuntimeError('This course is already open in Syntaxia.')
    logging.basicConfig(filename=course.database.with_suffix('.desktop.log'),level=logging.WARNING)
    assets=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'dist'
    server=make_server(port=0,database=course.database,catalog_path=course.catalog,assets=assets)
    position_file=course.database.with_suffix('.desktop.json')
    try: position=json.loads(position_file.read_text(encoding='utf-8'))
    except (OSError,ValueError): position={}
    if not isinstance(position,dict): position={}
    output_lock=threading.Lock()
    def emit(value):
        with output_lock: print(json.dumps(value),flush=True)
    def completed(body):
        request=body.get('request_id')
        if type(request) is not int or not isinstance(body.get('ok'),bool):
            raise ValueError('Invalid desktop acknowledgement.')
        if body['ok'] and not body.get('closing', True):
            try: load_catalog(course.catalog)
            except Exception:
                body={**body,'ok':False,'message':'Lessons could not be reloaded. Check the external course files; your current lesson is still open.'}
        mission=body.get('mission')
        if body['ok'] and mission:
            if mission not in {m['id'] for m in server.course['missions']}:
                raise ValueError('Unknown lesson position.')
            position_file.write_text(json.dumps({'mission':mission}),encoding='utf-8')
        emit({'kind':'leave','request_id':request,'ok':body['ok'],'mission':mission,'message':body.get('message','')})
        return {'ok':True}
    server.desktop_callback=completed
    # The dedicated control pipe handles both graceful quit and an unexpectedly
    # terminated parent. Provider threads never keep the service alive.
    def control():
        for line in sys.stdin:
            if line.strip()=='quit': break
        server.shutdown()
    thread=threading.Thread(target=control,daemon=True)
    emit({'kind':'ready','port':server.server_port,'mission':position.get('mission',''),
          'catalog':str(course.catalog),'database':str(course.database)})
    thread.start()
    try: server.serve_forever(poll_interval=0.1)
    finally: server.server_close(); lock.close()

if __name__=='__main__':
    try: main()
    except Exception as e:
        print(json.dumps({'kind':'error','message':str(e)}),flush=True)
        sys.exit(1)
