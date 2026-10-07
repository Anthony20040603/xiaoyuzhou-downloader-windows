import sys,threading,json
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
sys.path.insert(0,str(Path('work/app').resolve()))
from engine import download,Episode
payload=next(Path('outputs/测试音频').rglob('*.mp3')).read_bytes()
ranges=[]
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        start=int(self.headers.get('Range','bytes=0-').split('=')[1].split('-')[0]);ranges.append(start)
        if self.path=='/no-range.mp3':start=0
        self.send_response(206 if start else 200)
        self.send_header('Content-Length',str(len(payload)-start));self.send_header('ETag','"test-v1"')
        self.send_header('Content-Type','audio/mpeg')
        if start:self.send_header('Content-Range',f'bytes {start}-{len(payload)-1}/{len(payload)}')
        self.end_headers()
        try:self.wfile.write(payload[start:])
        except (ConnectionResetError,BrokenPipeError,ConnectionAbortedError):pass
    def log_message(self,*a):pass
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
report=[]
for endpoint in ('range.mp3','no-range.mp3'):
    ep=Episode(endpoint,f'http://127.0.0.1:{server.server_port}/{endpoint}','2026-10-04','',guid=endpoint)
    stop=threading.Event()
    def progress(n,total):
        if n>=131072:stop.set()
    first=download('work/engine-test','test',ep,stop,progress);assert first['status']=='已暂停'
    stop.clear(); second=download('work/engine-test','test',ep,stop)
    assert Path(second['path']).read_bytes()==payload
    third=download('work/engine-test','test',ep,stop);assert third['status']=='已存在'
    report.append({'endpoint':endpoint,'paused':first['status'],'resumed':second['status'],'duplicate':third['status']})
assert any(r>0 for r in ranges)
server.shutdown()
Path('work/engine-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
