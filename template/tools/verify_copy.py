# -*- coding: utf-8 -*-
"""生成LPが (1) K/L列の文言と一致 (2) H3以降がマスターと完全一致 かを検査する。"""
import io, os, re, sys, unicodedata
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from lp_data import LPS, FIXED_MARK as FIX

# ★案件ごとに差し替える：GA4の測定ID
GA4_ID = 'G-XXXXXXXXXX'

strip = lambda s: re.sub(r'<[^>]+>', '', s)
def norm(s):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', s))

master = io.open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
master_tail = master[master.index(FIX):]

ng = []
for lp in LPS:
    f = os.path.join(ROOT, lp['slug'], 'index.html')
    html = io.open(f, encoding='utf-8').read()

    # 1) H3以降がマスターと完全一致（相対パスの ./→../ だけが差分）
    tail = html[html.index(FIX):]
    if tail != master_tail.replace('src="./assets/', 'src="../assets/') \
                          .replace('href="./assets/', 'href="../assets/'):
        ng.append('%s: H3以降がマスターと不一致' % lp['slug'])

    # 2) K/L列の実文がページ内に（タグを除いた状態で）そのまま入っているか
    page = norm(strip(html))
    checks = [('H1', ''.join(lp['h1'])), ('ティザー見出し', strip(lp['ttl'])),
              ('ティザー本文', strip(lp['txt'])), ('H2', lp['h2'])]
    checks += [('導入%d' % (i+1), strip(t)) for i, t in enumerate(lp['intro'])]
    for i, (kind, val) in enumerate(lp['body']):
        if kind in ('p', 'note'):
            checks.append(('H2本文%d' % (i+1), strip(val)))
        else:
            for k, v in val:
                checks.append(('H2本文リスト', k + v))
    for label, t in checks:
        if norm(t) not in page:
            ng.append('%s: %s がページ内に見つからない → %s' % (lp['slug'], label, t[:40]))

    # 3) 計測タグ・CTA・KW属性
    for need in [GA4_ID, "gtag('config'", 'data-cta="final"', 'data-cta="trust"',
                 'data-cta="cases"', 'data-cta="operation"', 'app.js', 'styles.css']:
        if need not in html:
            ng.append('%s: %s が欠落' % (lp['slug'], need))
    if 'data-keyword="%s"' % lp['kw'] not in html:
        ng.append('%s: data-keyword 未設定' % lp['slug'])
    if '<title>%s</title>' % lp['title'] not in html:
        ng.append('%s: title 未反映' % lp['slug'])
    if lp['desc'] not in html:
        ng.append('%s: description 未反映' % lp['slug'])
    # 文字化け・素の & のチェック
    if '�' in html:
        ng.append('%s: 文字化け(U+FFFD)あり' % lp['slug'])

print('検査LP数:', len(LPS))
print('NG:', len(ng))
for x in ng:
    print('  -', x)
