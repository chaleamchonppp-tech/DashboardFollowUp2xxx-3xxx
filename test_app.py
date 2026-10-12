import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
import app

HEADERS=['Lv','ข้อกำหนดโครงการ /WBS','คำอธิบายภาษาไทย','งบประมาณปัจจุบัน','รวม Act.ทั้งหมดที่ควบคุม งปม.','งบประมาณคงเหลือ','สถานะ']
def raw(rows):
    out=io.StringIO();writer=csv.writer(out);writer.writerow(HEADERS);writer.writerows(rows);return out.getvalue().encode('utf-8-sig')
class ImportTests(unittest.TestCase):
    def test_leaf_budget_and_duplicate(self):
        row=[5,'I-69-B-ABC69.M4.2201','งาน','1,200.50','700.25','500.25','C1']
        jobs,buckets,warnings=app.parse_raw('SAP.csv',raw([[4,'I-69-B-ABC69.M4.2000','สรุป',999999,0,0,'Z0'],row,row]))
        self.assertEqual(len(jobs),1);self.assertEqual(next(iter(jobs.values()))['budget'],120050)
        self.assertEqual(buckets,['2xxx']);self.assertEqual(len(warnings),1)
    def test_conflicting_duplicate_rejected(self):
        a=[5,'I-69-B-ABC69.M4.2201','งาน',1200,700,500,'C1'];b=a.copy();b[-1]='F4'
        with self.assertRaisesRegex(ValueError,'ขัดแย้ง'):app.parse_raw('SAP.csv',raw([a,b]))
    def test_sample_is_not_raw(self):
        with self.assertRaises(ValueError):app.parse_raw('example.csv','ลำดับ,ชื่องาน\n1,งาน'.encode())
    def test_snapshots_persist_and_no_overwrite(self):
        original=app.DB
        with tempfile.TemporaryDirectory() as tmp:
            app.DB=Path(tmp)/'test.sqlite'
            try:
                a={'w':{'status':'C1','budget':100,'actual':20}}
                app.save_snapshot('2026-10-05','a.csv',a,['2xxx'])
                b={'w':{'status':'F4','budget':100,'actual':90}}
                app.save_snapshot('2026-10-12','b.csv',b,['2xxx'])
                with self.assertRaises(ValueError):app.save_snapshot('2026-10-05','a.csv',b,['2xxx'])
                with app.connect() as con:
                    rows=con.execute('SELECT jobs FROM snapshots ORDER BY day').fetchall()
                    self.assertEqual(json.loads(rows[0][0])['w']['status'],'C1')
                    self.assertEqual(json.loads(rows[1][0])['w']['status'],'F4')
            finally:app.DB=original
    def test_baseline_matches_reference(self):
        seed=json.loads((app.ROOT/'data/seed.json').read_text());refs=json.loads((app.ROOT/'data/reference.json').read_text())
        rows=[j for w,j in seed['jobs'].items() if w in refs]
        self.assertEqual(len(rows),334)
        self.assertEqual(sum(j['budget'] for j in rows),10951809058)
        self.assertEqual(sum(j['actual'] for j in rows),7882800890)
if __name__=='__main__':unittest.main()
