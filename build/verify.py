#!/usr/bin/env python3
"""Check the values embedded in the built page against the source workbook."""
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xlsx_reader import rows  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, 'mappa-pnc.html')
XLSX = os.path.join(ROOT, 'Dataset PNC.xlsx')

html = open(HTML, encoding='utf-8').read()
m = re.search(r'const DATA = (\{.*?\});\n', html, re.S)
data = json.loads(m.group(1))

it = rows(XLSX)
header = [h.strip() for h in next(it)]
col = {n: i for i, n in enumerate(header)}
src = {r[0]: r for r in it if r and r[0]}

codes = [u[4] for u in data['units']]
assert len(codes) == len(set(codes)) == len(src), 'unit count mismatch'
assert set(codes) == set(src), 'code set mismatch'

dense = {}
for s in data['subjects']:
    arr = [0] * len(codes)
    for j, i in enumerate(s['i']):
        arr[i] = s['v'][j]
    dense[s['k']] = arr

fails = []
random.seed(7)
for i in random.sample(range(len(codes)), 400):
    code = codes[i]
    row = src[code]
    tot = float(row[col['Totale risorse']])
    pc = float(row[col['Risorse pc']])
    if abs(data['total'][i] - round(tot)) > 1:
        fails.append((code, 'totale', data['total'][i], tot))
    if pc > 0 and abs(data['pop'][i] - round(tot / pc)) > 1:
        fails.append((code, 'popolazione', data['pop'][i], tot / pc))
    for s in data['subjects']:
        if s['k'] == 'altro':
            expect = tot - sum(float(row[col[c]]) for c in header
                               if c not in ('CODICE ISTAT', 'COMUNE', 'Totale risorse',
                                            'Risorse pc') and not c.endswith(' pc'))
            if abs(dense['altro'][i] - round(expect)) > 2:
                fails.append((code, 'altro', dense['altro'][i], expect))
            continue
        key = s['k'] if s['k'] in col else s['k'] + ' '
        got, want = dense[s['k']][i], float(row[col[key]])
        if abs(got - round(want)) > 1:
            fails.append((code, s['k'], got, want))

national = sum(data['total'])
national_src = sum(float(r[col['Totale risorse']]) for r in src.values())
if abs(national - national_src) > len(src):
    fails.append(('IT', 'totale nazionale', national, national_src))

if fails:
    for f in fails[:20]:
        print('MISMATCH', f)
    raise SystemExit('%d mismatches' % len(fails))
print('OK  %d municipalities, %d sectors, national total EUR %.2f bn'
      % (len(codes), len(data['subjects']), national / 1e9))
print('OK  400 random municipalities match the workbook on every column')
