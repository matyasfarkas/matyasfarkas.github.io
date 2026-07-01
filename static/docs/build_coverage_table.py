#!/usr/bin/env python3
"""Emit the LaTeX rows for the landscape country x variable-group coverage
table in docs/user_manual.tex, built deterministically from
app/public/data/coverage_manifest.json.

Read-only: prints LaTeX to stdout. No network, no re-estimation. The output
is pasted into the \\subsection{Country x Variable Coverage Matrix} of the
manual (or piped). Deterministic across runs.

Usage (from docs/):  python3 build_coverage_table.py
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, '..', 'app', 'public', 'data', 'coverage_manifest.json')


def load():
    with open(MANIFEST) as f:
        return json.load(f)


# Concept -> ordered list of candidate id roots (matched against an id with the
# trailing _<CC> stripped, and also against the raw id for US/GLP naming).
CONCEPTS = {
    'GDP':    ['GDP', 'GDPH', 'JGDP'],         # real activity (US carries GDPH real)
    'Price':  ['HICP', 'CPI', 'UI', 'JC'],     # consumer-price index (HICP/CPI/PCE)
    'Unemp':  ['LR'],                          # LR = unemployment rate in every bloc
    'Pol':    ['POLRATE'],                     # policy rate
    'Long':   ['YIELD10', 'GLB_USLR', 'FCM5'], # 10y / long government yield
    'Credit': ['CREDIT_GDP', 'LEV'],           # credit-to-GDP (US LEV = BCNSDODNS leverage proxy)
    'Lend':   ['LENDR', 'RATE', 'RATE3M', 'MMRATE', 'FCM2'],  # lending / short rate
    'FX':     ['NEER', 'REER', 'FXTWM'],       # external value
    'Fisc':   ['FREV_GDP', 'FPEXP_GDP', 'EFFI', 'SFA'],  # fiscal block present?
}


def strip_cc(vid, cc):
    if vid.endswith('_' + cc):
        return vid[:-(len(cc) + 1)]
    return vid


def cell_for(bloc, roots):
    """Return (mark, lastobs) for the first variable whose stripped root matches
    any candidate root; '' if the concept is absent in this bloc."""
    cc = bloc['code']
    have = {}
    for v in bloc['variables']:
        have[strip_cc(v['id'], cc)] = v
        have[v['id']] = v
    for r in roots:
        if r in have:
            v = have[r]
            return ('Y', v['lastObs'], bool(v.get('flag')))
    return ('', '', False)


FAMILY_TEX = {
    'FRED': 'FRED',
    'Eurostat': 'Eurostat',
    'OECD/FRED': 'OECD/FRED',
}


def family(bloc):
    """Classify the bloc's PRIMARY source family off its real-GDP source (the
    canonical anchor). Matching on 'any variable mentions Eurostat' is wrong:
    CA/UK/JP carry a 'national/Eurostat gov-finance' string on their fiscal
    ratios yet are not Eurostat-sourced economies."""
    cc = bloc['code']
    if cc in ('US', 'CN'):
        return 'FRED'
    gdp = next((v for v in bloc['variables']
                if strip_cc(v['id'], cc) in ('GDP', 'GDPH', 'JGDP')), None)
    s = gdp['source'] if gdp else ''
    if 'Eurostat' in s:
        return 'Eurostat'
    if 'OECD/FRED' in s or 'OECD' in s or 'FRED' in s:
        return 'OECD/FRED'
    return 'mixed'


def short_flag(bloc):
    bf = bloc.get('blocFlags', [])
    tags = []
    for f in bf:
        if f.startswith('WEO-backfilled'):
            tags.append('WEO')
        elif f.startswith('source-review'):
            tags.append('review')
        elif f.startswith('ragged-edge'):
            pass  # captured by last-obs column
        elif 'frozen OECD-MEI' in f:
            tags.append('frozen~mirror')
    # de-dup, keep order
    seen = []
    for t in tags:
        if t not in seen:
            seen.append(t)
    return ','.join(seen)


def main():
    d = load()
    blocs = sorted(d['blocs'], key=lambda b: b['code'])
    # column order in the table
    cols = ['GDP', 'Price', 'Unemp', 'Pol', 'Long', 'Credit', 'Lend', 'FX', 'Fisc']
    out = []
    for b in blocs:
        cc = b['code']
        last = b['lastHistQuarter']
        fam = family(b)
        cells = []
        for c in cols:
            mark, lo, flagged = cell_for(b, CONCEPTS[c])
            if mark == 'Y':
                cells.append('\\cmark')
            else:
                cells.append('--')
        flag = short_flag(b)
        flagtex = ('\\,\\footnotesize\\textit{' + flag + '}') if flag else ''
        row = '\\texttt{%s} & %s & %s & %s%s \\\\' % (
            cc, ' & '.join(cells), last, FAMILY_TEX.get(fam, fam), flagtex)
        out.append(row)
    print('\n'.join(out))
    # also emit a tiny summary to stderr for the author
    n = len(blocs)
    sys.stderr.write('rows=%d  cols=%s\n' % (n, ','.join(cols)))


if __name__ == '__main__':
    main()
