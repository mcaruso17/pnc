#!/usr/bin/env python3
"""Build the interactive PNC map.

Joins the PNC financing dataset (one row per municipality, ISTAT code) to the
ISTAT administrative boundaries republished by openpolis/geojson-italy, and
writes a single self-contained HTML page.

Usage:
    python3 build/build_site.py [--topojson PATH] [--xlsx PATH] [--out PATH]
"""
import argparse
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xlsx_reader import rows  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The boundary file is the 1 January 2026 ISTAT vintage (7,896 municipalities);
# the PNC dataset uses the list in force from 21 February 2026 (7,894). Two
# mergers separate them, so the older polygons are dissolved into their
# successors before the join.
MERGES = {
    '018082': '018094',   # Lirio incorporated into Montalto Pavese, 31/01/2026
    '024027': '024129',   # Castegnero  -> Castegnero Nanto, 21/02/2026
    '024071': '024129',   # Nanto       -> Castegnero Nanto, 21/02/2026
}
# Name and province to use for a municipality created by a merger, since no
# polygon in the boundary file carries them yet.
NEW_UNITS = {
    '024129': {'name': 'Castegnero Nanto', 'prov': 'Vicenza', 'prov_acr': 'VI',
               'reg': 'Veneto', 'reg_code': '05'},
}

# Column label in the workbook -> (display label, theme). Order here is the
# order of the dropdown.
THEMES = [
    ('Infrastrutture e mobilità', [
        ('Porti', 'Porti'),
        ('Ferrovie regionali', 'Ferrovie regionali'),
        ('Materiale rotabile', 'Materiale rotabile'),
        ('A24-A25', 'Autostrade A24-A25'),
        ('Strade ANAS', 'Strade ANAS'),
        ('Autobus', 'Autobus'),
        ('Navi', 'Navi'),
    ]),
    ('Territorio, abitare e aree fragili', [
        ('Sisma', 'Ricostruzione post-sisma'),
        ('Case popolari', 'Edilizia residenziale pubblica'),
        ('Aree interne', 'Aree interne'),
        ('Agricoltura', 'Agricoltura'),
    ]),
    ('Salute e ricerca', [
        ('Ospedali', 'Ospedali'),
        ('Ecosistema della salute', 'Ecosistema della salute'),
        ('Ricerca medica', 'Ricerca medica'),
        ('Ricerca sanitaria', 'Ricerca sanitaria'),
    ]),
    ('Cultura, innovazione e PA', [
        ('Cultura', 'Cultura'),
        ("Accordi per l'innovazione", "Accordi per l'innovazione"),
        ('Innovazione', 'Innovazione'),
        ('Orizzonte Europa', 'Orizzonte Europa'),
        ('Digitalizzazione PA', 'Digitalizzazione PA'),
    ]),
    ('Giustizia', [
        ('Edilizia penitenziaria', 'Edilizia penitenziaria'),
    ]),
]

B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'


def enc_uint(n, out):
    """Append an unsigned varint, 5 payload bits per character."""
    while True:
        chunk = n & 31
        n >>= 5
        out.append(B64[chunk | 32] if n else B64[chunk])
        if not n:
            return


def enc_int(n, out):
    enc_uint((n << 1) ^ (n >> 63) if n < 0 else n << 1, out)


def encode_arcs(arcs):
    out = []
    enc_uint(len(arcs), out)
    for arc in arcs:
        enc_uint(len(arc), out)
        for x, y in arc:
            enc_int(x, out)
            enc_int(y, out)
    return ''.join(out)


def flat_arcs(node, found=None):
    """Every arc index in an arbitrarily nested arc structure."""
    if found is None:
        found = []
    if isinstance(node, int):
        found.append(node)
    else:
        for child in node:
            flat_arcs(child, found)
    return found


def read_dataset(path):
    it = rows(path)
    header = [h.strip() for h in next(it)]
    records = []
    for r in it:
        if not r or not r[0]:
            continue
        records.append(r)
    return header, records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--topojson', default=os.path.join(
        os.path.dirname(ROOT), 'openpolis', 'geojson-italy', 'topojson',
        'limits_IT_municipalities.topo.json'))
    ap.add_argument('--xlsx', default=os.path.join(ROOT, 'Dataset PNC.xlsx'))
    ap.add_argument('--template', default=os.path.join(ROOT, 'build', 'template.html'))
    # index.html so that GitHub Pages serves it at the root of the site
    ap.add_argument('--out', default=os.path.join(ROOT, 'index.html'))
    args = ap.parse_args()

    # ---------------------------------------------------------------- data
    header, records = read_dataset(args.xlsx)
    col = {name: i for i, name in enumerate(header)}
    raw = {r[0]: r for r in records}
    print('dataset: %d municipalities' % len(raw))

    # ------------------------------------------------------------ geometry
    topo = json.load(open(args.topojson, encoding='utf-8'))
    geoms = topo['objects']['comuni']['geometries']
    scale, translate = topo['transform']['scale'], topo['transform']['translate']

    def describe(p, code):
        meta = NEW_UNITS.get(code)
        if meta:
            return dict(meta, prov_code=p['prov_istat_code'])
        return {'name': p['name'], 'prov': p['prov_name'], 'prov_acr': p['prov_acr'],
                'reg': p['reg_name'], 'reg_code': p['reg_istat_code'],
                'prov_code': p['prov_istat_code']}

    units = {}          # istat code -> record being assembled
    order = []
    for g in geoms:
        p = g['properties']
        own = p['com_istat_code']
        code = MERGES.get(own, own)
        u = units.get(code)
        if u is None:
            u = units[code] = dict(describe(p, code), code=code, rings=[])
            order.append(code)
        elif own == code:
            # the surviving municipality's own polygon: its name and province
            # win over those of the suppressed ones merged into it
            u.update(describe(p, code))
        rings = g['arcs'] if g['type'] == 'MultiPolygon' else [g['arcs']]
        u['rings'].extend(rings)

    missing_geo = [c for c in raw if c not in units]
    missing_data = [c for c in units if c not in raw]
    if missing_geo or missing_data:
        raise SystemExit('join failed: %d data rows without geometry (%s), '
                         '%d polygons without data (%s)' % (
                             len(missing_geo), missing_geo[:5],
                             len(missing_data), missing_data[:5]))
    print('join: %d units matched 1:1' % len(units))

    # Sort north-west to south-east only for stable output; index order is
    # what the value arrays refer to.
    order.sort(key=lambda c: (units[c]['reg_code'], units[c]['prov_code'], units[c]['name']))
    index = {c: i for i, c in enumerate(order)}

    # ------------------------------------------------- border classification
    owners = defaultdict(set)
    for code in order:
        for a in set(x if x >= 0 else ~x for x in flat_arcs(units[code]['rings'])):
            owners[a].add(code)
    prov_arcs, reg_arcs = [], []
    for a, who in owners.items():
        regs = {units[c]['reg_code'] for c in who}
        provs = {units[c]['prov_code'] for c in who}
        if len(who) == 1 or len(regs) > 1:
            reg_arcs.append(a)
            prov_arcs.append(a)
        elif len(provs) > 1:
            prov_arcs.append(a)

    # ---------------------------------------------------------- value arrays
    def num(code, column):
        v = raw[code][col[column]]
        return float(v) if v not in ('', None) else 0.0

    population, total = [], []
    for code in order:
        tot = num(code, 'Totale risorse')
        pc = num(code, 'Risorse pc')
        population.append(round(tot / pc) if pc else 0)
        total.append(round(tot))

    subjects, sectors_sum = [], [0.0] * len(order)
    for theme, items in THEMES:
        for column, label in items:
            if column not in col:
                raise SystemExit('missing column %r' % column)
            idx, val = [], []
            for i, code in enumerate(order):
                v = num(code, column)
                sectors_sum[i] += v
                if v:
                    idx.append(i)
                    val.append(round(v))
            subjects.append({'k': column.strip(), 'l': label, 't': theme,
                             'i': idx, 'v': val})
    other_idx, other_val = [], []
    for i in range(len(order)):
        v = total[i] - round(sectors_sum[i])
        if v > 0.5:
            other_idx.append(i)
            other_val.append(round(v))
    subjects.append({'k': 'altro', 'l': 'Altri interventi non ripartiti',
                     't': 'Voce residuale', 'i': other_idx, 'v': other_val})

    payload = {
        'transform': [scale[0], scale[1], translate[0], translate[1]],
        'arcs': encode_arcs(topo['arcs']),
        'provArcs': sorted(prov_arcs),
        'regArcs': sorted(reg_arcs),
        'units': [[units[c]['name'], units[c]['prov_acr'], units[c]['prov'],
                   units[c]['reg'], c] for c in order],
        'rings': [units[c]['rings'] for c in order],
        'pop': population,
        'total': total,
        'subjects': subjects,
    }

    blob = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    template = open(args.template, encoding='utf-8').read()
    if '__PNC_DATA__' not in template:
        raise SystemExit('template has no __PNC_DATA__ placeholder')
    html = template.replace('__PNC_DATA__', blob)
    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(html)

    print('arcs        %8.2f MB' % (len(payload['arcs']) / 1e6))
    print('rings       %8.2f MB' % (len(json.dumps(payload['rings'])) / 1e6))
    print('values      %8.2f MB' % (len(json.dumps(payload['subjects'])) / 1e6))
    print('written     %8.2f MB  %s' % (os.path.getsize(args.out) / 1e6, args.out))
    print('national total  €%.3f bn over %d municipalities' % (
        sum(total) / 1e9, sum(1 for t in total if t)))


if __name__ == '__main__':
    main()
