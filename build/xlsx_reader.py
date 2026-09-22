"""Minimal read-only XLSX reader (stdlib only).

The build box has no third-party Python packages, so this parses the parts of
SpreadsheetML that the PNC dataset actually uses: shared strings and one
worksheet of numeric/string cells.
"""
import io
import re
import zipfile
import xml.etree.ElementTree as ET

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


def _shared_strings(z):
    out = []
    try:
        data = z.read('xl/sharedStrings.xml')
    except KeyError:
        return out
    for _, el in ET.iterparse(io.BytesIO(data), events=('end',)):
        if el.tag == NS + 'si':
            out.append(''.join(t.text or '' for t in el.iter(NS + 't')))
            el.clear()
    return out


def _col_index(ref):
    letters = re.match(r'([A-Z]+)', ref).group(1)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def rows(path, sheet='xl/worksheets/sheet1.xml'):
    """Yield each row of the sheet as a list of strings."""
    z = zipfile.ZipFile(path)
    strings = _shared_strings(z)
    for _, el in ET.iterparse(z.open(sheet), events=('end',)):
        if el.tag != NS + 'row':
            continue
        cells = {}
        for c in el.findall(NS + 'c'):
            kind = c.get('t')
            if kind == 'inlineStr':
                node = c.find(NS + 'is')
                text = ''.join(t.text or '' for t in node.iter(NS + 't')) if node is not None else ''
            else:
                v = c.find(NS + 'v')
                if v is None:
                    text = ''
                elif kind == 's':
                    text = strings[int(v.text)]
                else:
                    text = v.text or ''
            cells[_col_index(c.get('r'))] = text
        width = max(cells) + 1 if cells else 0
        yield [cells.get(i, '') for i in range(width)]
        el.clear()
