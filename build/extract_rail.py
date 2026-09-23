#!/usr/bin/env python3
"""Extract the Italian railway network from an OSM extract into GeoJSON.

Reads an .osm.pbf regional extract and writes the running lines of the network
as simplified LineStrings. The output is committed to the repository as
`data/ferrovie.geojson`, so building the page needs neither the 2.5 GB extract
nor network access; rerun this only to refresh the geometry from newer OSM data.

Usage:
    pip install osmium
    curl -O https://download.openstreetmap.fr/extracts/europe/italy-latest.osm.pbf
    python3 build/extract_rail.py italy-latest.osm.pbf

The processing mirrors what the page does to the boundary arcs, so both layers
end up on the same integer grid and cost the same per vertex:

1. keep the lines an overview map should show, drop yard and service track;
2. snap every vertex to the quantisation grid of the boundary file, about
   14.6 m in both axes at Italian latitudes;
3. chain ways that share an endpoint into long polylines;
4. drop the vertices a Douglas-Peucker pass finds redundant at grid resolution.

Step 2 is what makes step 4 cheap: after snapping, a tolerance of one grid unit
already removes seven vertices in eight, because OSM traces curves far more
finely than a national map can show.
"""
import argparse
import json
import os
from collections import defaultdict

import osmium

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The quantisation grid of limits_IT_municipalities.topo.json. Sharing it with
# the boundaries keeps the two layers on identical coordinates.
SX, SY, TX, TY = (0.0001770626580220439, 0.00013216098506245644,
                  6.627259916662413, 35.493633956256495)

# Lines of the running network. Everything out of service (disused, abandoned,
# razed, construction, proposed) carries its own railway=* value and so never
# matches; tram, subway and light_rail are urban networks, out of scale here.
KEEP = {'rail', 'narrow_gauge'}
# service=* is track inside yards and stations (siding, spur, yard, crossover):
# it multiplies the geometry without adding anything legible at this scale.
DROP_USAGE = {'industrial', 'military', 'test', 'tourism'}


def read_ways(pbf):
    """Every running railway line in the extract, as quantised integer points."""
    out = []
    # Nodes have to be read for the location cache to fill, so the entity
    # filter narrowing the iterator down to ways comes after it.
    proc = (osmium.FileProcessor(pbf, osmium.osm.NODE | osmium.osm.WAY)
            .with_locations('flex_mem')
            .with_filter(osmium.filter.EntityFilter(osmium.osm.WAY))
            .with_filter(osmium.filter.KeyFilter('railway')))
    for w in proc:
        t = w.tags
        if t.get('railway') not in KEEP:
            continue
        if 'service' in t or t.get('usage') in DROP_USAGE:
            continue
        pts = []
        for n in w.nodes:
            if not n.location.valid():
                continue
            p = (round((n.lon - TX) / SX), round((n.lat - TY) / SY))
            if not pts or p != pts[-1]:
                pts.append(p)
        if len(pts) >= 2:
            out.append((1 if t.get('highspeed') == 'yes' else 0, pts))
    return out


def stitch(lines):
    """Chain lines sharing an endpoint into longer polylines.

    Fewer, longer lines mean fewer length prefixes in the payload and fewer
    moveTo calls per frame. Where three or more lines meet, whichever chain
    reaches the junction first consumes it; the rest stay separate.
    """
    ends = defaultdict(list)
    for i, ln in enumerate(lines):
        ends[ln[0]].append(i)
        ends[ln[-1]].append(i)
    used = [False] * len(lines)
    out = []
    for i, ln in enumerate(lines):
        if used[i]:
            continue
        used[i] = True
        chain = list(ln)
        for _ in range(2):                      # extend the tail, then the head
            while True:
                tail = chain[-1]
                nxt = next((j for j in ends[tail]
                            if not used[j] and (lines[j][0] == tail
                                                or lines[j][-1] == tail)), None)
                if nxt is None:
                    break
                used[nxt] = True
                seg = lines[nxt]
                chain.extend(seg[1:] if seg[0] == tail else seg[-2::-1])
            chain.reverse()
        out.append(chain)
    return out


def simplify(pts, tol):
    """Douglas-Peucker, iterative so long chains can't blow the stack."""
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    t2 = tol * tol
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        x0, y0 = pts[i]
        dx, dy = pts[j][0] - x0, pts[j][1] - y0
        den = dx * dx + dy * dy
        best, bi = -1.0, -1
        for k in range(i + 1, j):
            px, py = pts[k]
            if den:
                t = ((px - x0) * dx + (py - y0) * dy) / den
                t = 0.0 if t < 0 else (1.0 if t > 1 else t)
                ex, ey = px - (x0 + t * dx), py - (y0 + t * dy)
            else:
                ex, ey = px - x0, py - y0
            d = ex * ex + ey * ey
            if d > best:
                best, bi = d, k
        if best > t2:
            keep[bi] = True
            stack.append((i, bi))
            stack.append((bi, j))
    return [p for p, k in zip(pts, keep) if k]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pbf', help='.osm.pbf extract covering Italy')
    ap.add_argument('--out', default=os.path.join(ROOT, 'data', 'ferrovie.geojson'))
    ap.add_argument('--tolerance', type=int, default=1,
                    help='Douglas-Peucker tolerance in grid units (default 1, '
                         'about 15 m, the resolution of the grid itself)')
    args = ap.parse_args()

    ways = read_ways(args.pbf)
    print('linee di corsa  %6d tratte, %7d vertici'
          % (len(ways), sum(len(p) for _, p in ways)))

    groups = defaultdict(list)
    for hs, pts in ways:
        groups[hs].append(pts)

    feats = []
    for hs in sorted(groups):
        chains = stitch(groups[hs])
        for c in chains:
            s = simplify(c, args.tolerance)
            if len(s) < 2:
                continue
            feats.append({
                'type': 'Feature',
                'properties': {'hs': hs},
                'geometry': {
                    'type': 'LineString',
                    # Back to lon/lat, but snapped: the page re-quantises onto
                    # the same grid and gets these integers back exactly.
                    'coordinates': [[round(TX + x * SX, 6), round(TY + y * SY, 6)]
                                    for x, y in s],
                },
            })

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w') as fh:
        json.dump({'type': 'FeatureCollection', 'features': feats}, fh)

    pts = sum(len(f['geometry']['coordinates']) for f in feats)
    hs = sum(1 for f in feats if f['properties']['hs'])
    print('dopo stitching  %6d polilinee' % len(feats))
    print('semplificate    %6d vertici (tolleranza %d = %.0f m)'
          % (pts, args.tolerance, args.tolerance * 14.6))
    print('alta velocita   %6d polilinee' % hs)
    print('scritto         %6.2f MB  %s'
          % (os.path.getsize(args.out) / 1e6, args.out))


if __name__ == '__main__':
    main()
