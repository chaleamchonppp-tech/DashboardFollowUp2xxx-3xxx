"""Restore the supplied baseline only when no snapshots exist."""
import json
from app import ROOT, connect, save_snapshot
with connect() as con:
    empty = con.execute('SELECT COUNT(*) FROM snapshots').fetchone()[0] == 0
if empty:
    seed = json.loads((ROOT / 'data/seed.json').read_text())
    save_snapshot(seed['day'], seed['source'], seed['jobs'], seed['buckets'])
    print('Restored baseline:', len(seed['jobs']), 'SAP jobs')
else:
    print('Existing snapshots preserved')
