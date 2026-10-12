import base64
import csv
import io
import json
import os
import hmac
import re
import sqlite3
from datetime import date
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import openpyxl

ROOT = Path(__file__).parent
DB = Path(os.environ.get('DASHBOARD_DB_PATH', str(ROOT / 'data/dashboard.sqlite')))
PATTERN = re.compile(r'\.([A-Z0-9]+)\.([23]\d{3})$')

def number(value):
    if value in (None, '', '-'): return 0
    result = float(str(value).replace(',', ''))
    if not __import__('math').isfinite(result): raise ValueError('จำนวนเงินไม่ถูกต้อง')
    return round(result * 100)

def tables(name, content):
    if name.lower().endswith('.csv'):
        for encoding in ('utf-8-sig', 'cp874'):
            try: text = content.decode(encoding); break
            except UnicodeDecodeError: continue
        else: raise ValueError('ไม่รองรับรหัสภาษาใน CSV')
        return [(name, list(csv.reader(io.StringIO(text))))]
    if name.lower().endswith('.xlsx'):
        book = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        result = [(sheet.title, list(sheet.values)) for sheet in book]
        book.close()
        return result
    raise ValueError('กรุณาใช้ไฟล์ CSV หรือ XLSX')

def parse_raw(name, content):
    jobs = {}; buckets = set(); warnings = []; seen = {}
    for title, rows in tables(name, content):
        if not rows: continue
        headers = [str(x or '').strip() for x in rows[0]]
        if not headers or headers[0] != 'Lv' or 'งบประมาณปัจจุบัน' not in headers: continue
        def get(row, key):
            i = headers.index(key) if key in headers else -1
            return row[i] if i >= 0 and i < len(row) else None
        for line, row in enumerate(rows[1:], 2):
            wbs = str(get(row, 'ข้อกำหนดโครงการ /WBS') or '').strip()
            match = PATTERN.search(wbs)
            if not match: continue
            bucket = match[2][0] + 'xxx'; buckets.add(bucket)
            if str(get(row, 'Lv')) not in ('5', '5.0'): continue
            if match[1] not in ('HB', 'JA', 'M4'): continue
            signature = tuple(str(get(row, key) or '').strip() for key in headers[:24])
            if wbs in seen:
                if signature == seen[wbs]:
                    warnings.append(f'ตัดแถวซ้ำที่เหมือนกัน: {wbs}')
                    continue
                raise ValueError(f'WBS ซ้ำและข้อมูลขัดแย้ง: {wbs} แถว {line}')
            seen[wbs] = signature
            status = str(get(row, 'สถานะ') or '').strip()
            sap = str(get(row, 'Status') or '')
            if not status: status = sap.split('//')[-1].strip() if '//' in sap else 'ไม่ระบุ'
            jobs[wbs] = dict(wbs=wbs, name=str(get(row, 'คำอธิบายภาษาไทย') or ''), group=match[1], bucket=bucket,
                year=(re.search(r'^I-(\d{2})-',wbs).group(1) if re.search(r'^I-(\d{2})-',wbs) else ''),
                status=status, sap=sap, budget=number(get(row,'งบประมาณปัจจุบัน')),
                actual=number(get(row,'รวม Act.ทั้งหมดที่ควบคุม งปม.')),
                remaining=number(get(row,'งบประมาณคงเหลือ')), material=number(get(row,'Plan ค่าวัสดุ')),
                expense=number(get(row,'Plan คชจ.หน้างาน')))
    if not jobs: raise ValueError('ไม่พบงานระดับ Lv 5 ในชีต SAP ดิบที่มีงบประมาณปัจจุบัน')
    return jobs, sorted(buckets), warnings

def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute('CREATE TABLE IF NOT EXISTS snapshots (day TEXT PRIMARY KEY, source TEXT, jobs TEXT, buckets TEXT)')
    return con

def reference(name, content):
    jobs = {}
    for title, rows in tables(name,content):
        if not rows: continue
        heads = [str(x or '').strip() for x in rows[0]]
        if 'กฟฟ.' not in heads or 'ข้อกำหนดโครงการ /WBS' not in heads: continue
        for row in rows[1:]:
            def get(key):
                i=heads.index(key) if key in heads else -1
                return row[i] if i>=0 and i<len(row) else ''
            wbs=str(get('ข้อกำหนดโครงการ /WBS') or '').strip()
            if PATTERN.search(wbs): jobs[wbs]={'office':str(get('กฟฟ.') or ''),'region':str(get('กฟฟ.จุดรวมงาน') or ''),'plan':str(get('ปีที่ดำเนินงาน') or ''),'name':str(get('ชื่องาน') or '')}
    return jobs

def save_snapshot(day, source, jobs, buckets):
    date.fromisoformat(day)
    with connect() as con:
        if con.execute('SELECT 1 FROM snapshots WHERE day=?',(day,)).fetchone():
            raise ValueError('มีข้อมูลวันที่นี้แล้ว กรุณาเลือกวันที่อื่น เพื่อรักษาประวัติเดิม')
        con.execute('INSERT INTO snapshots VALUES (?,?,?,?)',(day,source,json.dumps(jobs,ensure_ascii=False),json.dumps(buckets)))

def restore_backup(payload):
    if payload.get('version') != 1 or not isinstance(payload.get('snapshots'), list):
        raise ValueError('ไฟล์สำรองไม่ถูกต้อง')
    pending = []
    days = set()
    for snapshot in payload['snapshots']:
        day = snapshot['day']; date.fromisoformat(day)
        if day in days: raise ValueError('วันที่ซ้ำในไฟล์สำรอง')
        days.add(day)
        jobs = snapshot['jobs']; buckets = snapshot['buckets']
        if not isinstance(jobs, dict) or not isinstance(buckets, list) or not set(buckets) <= {'2xxx','3xxx'}:
            raise ValueError('โครงสร้างงานไม่ถูกต้อง')
        for wbs, job in jobs.items():
            match = PATTERN.search(wbs)
            if not match or job['wbs'] != wbs or job['group'] != match[1] or job['bucket'] != match[2][0]+'xxx' or job['bucket'] not in buckets:
                raise ValueError('WBS หรือกลุ่มงบไม่ถูกต้อง')
            for key in ('name','year','status','sap'):
                if not isinstance(job[key], str): raise ValueError('ข้อมูลข้อความไม่ถูกต้อง')
            for key in ('budget','actual','remaining','material','expense'):
                if type(job[key]) is not int: raise ValueError('จำนวนเงินในไฟล์สำรองไม่ถูกต้อง')
        source = snapshot['source']
        if not isinstance(source,str): raise ValueError('ชื่อไฟล์ไม่ถูกต้อง')
        pending.append((day,source,jobs,buckets))
    added = 0
    with connect() as con:
        for day,source,jobs,buckets in pending:
            old = con.execute('SELECT jobs,buckets FROM snapshots WHERE day=?',(day,)).fetchone()
            if old:
                if json.loads(old[0]) != jobs or sorted(json.loads(old[1])) != sorted(buckets):
                    raise ValueError(f'วันที่ {day} มีข้อมูลขัดแย้ง ระบบไม่เขียนทับประวัติ')
                continue
            con.execute('INSERT INTO snapshots VALUES (?,?,?,?)',(day,source,json.dumps(jobs,ensure_ascii=False),json.dumps(buckets)))
            added += 1
    return added

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT/'static'),**kwargs)
    def authorized(self):
        if os.environ.get('REQUIRE_AUTH') == '0': return True
        user = os.environ.get('APP_USERNAME', '')
        password = os.environ.get('APP_PASSWORD', '')
        if not user and not password and os.environ.get('REQUIRE_AUTH') != '1': return True
        valid = False
        try:
            scheme, token = self.headers.get('Authorization', '').split(' ', 1)
            supplied = base64.b64decode(token, validate=True)
            expected = (user + ':' + password).encode('utf-8')
            valid = bool(user and password) and scheme.lower() == 'basic' and hmac.compare_digest(supplied, expected)
        except (ValueError, UnicodeError): pass
        if valid: return True
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Dashboard", charset="UTF-8"')
        self.send_header('Content-Length', '0')
        self.end_headers()
        return False
    def do_HEAD(self):
        if self.authorized(): super().do_HEAD()
    def send_json(self,data,status=200):
        raw=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        if self.path == '/healthz': return self.send_json({'status': 'ok'})
        if not self.authorized(): return
        if self.path in ('/data/seed.json', '/data/reference.json'):
            return self.send_json(json.loads((ROOT / self.path.lstrip('/')).read_text()))
        if self.path=='/api/data':
            with connect() as con:
                rows=con.execute('SELECT day,source,jobs,buckets FROM snapshots ORDER BY day').fetchall()
            refs=json.loads((ROOT/'data/reference.json').read_text()) if (ROOT/'data/reference.json').exists() else {}
            return self.send_json({'snapshots':[{'day':r[0],'source':r[1],'jobs':json.loads(r[2]),'buckets':json.loads(r[3])} for r in rows],'reference':refs})
        return super().do_GET()
    def do_POST(self):
        if not self.authorized(): return
        if self.path not in ('/api/import','/api/restore'): return self.send_json({'error':'ไม่พบเส้นทาง'},404)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size <= 0 or size>30_000_000: raise ValueError('ขนาดคำขอไม่ถูกต้อง หรือไฟล์ใหญ่เกิน 20 MB')
            payload=json.loads(self.rfile.read(size))
            if self.path == '/api/restore':
                return self.send_json({'count': restore_backup(payload)})
            content=base64.b64decode(payload['content'],validate=True)
            jobs,buckets,warnings=parse_raw(payload['name'],content)
            save_snapshot(payload['day'],Path(payload['name']).name,jobs,buckets)
            self.send_json({'count':len(jobs),'buckets':buckets,'warnings':warnings})
        except Exception as exc: self.send_json({'error':str(exc)},400)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=int(os.environ.get('PORT','8000')));args=parser.parse_args()
    if os.environ.get('REQUIRE_AUTH') == '1' and (not os.environ.get('APP_USERNAME') or len(os.environ.get('APP_PASSWORD','')) < 12):
        raise SystemExit('Set APP_USERNAME and APP_PASSWORD (at least 12 characters) before starting the hosted dashboard.')
    connect().close()
    print(f'Dashboard listening on port {args.port}',flush=True)
    ThreadingHTTPServer(('0.0.0.0',args.port),Handler).serve_forever()
