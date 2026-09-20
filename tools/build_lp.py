# -*- coding: utf-8 -*-
"""横展開LPを index.html（マスター）から生成する。

共通部の実体はマスター1か所だけ。このスクリプトは index.html を読み、
・<head> のうち title / description / 相対パスだけを差し替え
・FV と 最初のH2（#points の先頭）だけを各LPのコピーに置換
・H3「いま選べるのは、この4種類。」以降は1文字も触らずそのまま流用
して <slug>/index.html を書き出す。index.html 自体は絶対に書き換えない。

使い方: python3 tools/build_lp.py
"""
import io, os, re, sys, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from lp_data import LPS

MASTER = os.path.join(ROOT, 'index.html')
FIXED_MARK = '  <h3 class="sub-head">いま選べるのは、この4種類。</h3>'
VAR_START  = '<section id="fv" class="kin-fv kin-fv--visual">'

src = io.open(MASTER, encoding='utf-8').read()

# ---- マスターを「頭」「可変部」「固定部（H3以降すべて）」に割る ----
i_head = src.index(VAR_START)
i_fix  = src.index(FIXED_MARK)
head_part  = src[:i_head]     # <!DOCTYPE> 〜 <main ...> まで
fixed_part = src[i_fix:]      # H3以降すべて（CTA・画像・計測タグ・footer 含む）

def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

def build_head(lp):
    h = head_part
    # title / description / 検索KW属性だけ差し替える。計測タグ・CSS・JSはそのまま
    h = re.sub(r'<title>.*?</title>', '<title>%s</title>' % esc(lp['title']), h, count=1, flags=re.S)
    h = re.sub(r'(<meta name="description" content=")(.*?)(">)',
               lambda m: m.group(1) + esc(lp['desc']) + m.group(3), h, count=1, flags=re.S)
    h = re.sub(r'(<main class="wrap page" data-keyword=")(.*?)(")',
               lambda m: m.group(1) + esc(lp['kw']) + m.group(3), h, count=1)
    return h

def to_child_paths(s):
    """1階層下に置くので ./ を ../ にする。それ以外のURLは触らない。"""
    return s.replace('src="./townlife-ohaka/', 'src="../townlife-ohaka/') \
            .replace('href="./townlife-ohaka/', 'href="../townlife-ohaka/')

def build_variable(lp):
    hero_cls = ' ohaka-hero--h1-m' if lp.get('h1_size') == 'm' else ''
    if lp.get('hero') == 'tall':
        hero_cls += ' ohaka-hero--tall'
    ttl_len = len(re.sub(r'<[^>]+>', '', lp['ttl']))
    ttl_cls = '' if ttl_len <= 20 else (' fv-card__ttl--m' if ttl_len <= 30 else ' fv-card__ttl--s')
    spans = ''.join('<span>%s</span>' % s for s in lp['h1'])
    intro = '\n'.join('    <p>%s</p>' % p for p in lp['intro'])

    body = []
    for kind, val in lp['body']:
        if kind == 'p':
            body.append('  <p>%s</p>' % val)
        elif kind == 'note':
            body.append('  <p class="kin-note">%s</p>' % val)
        elif kind == 'list':
            items = '\n'.join('    <li><b>%s</b><span>%s</span></li>' % (k, v) for k, v in val)
            body.append('  <ul class="step-list">\n%s\n  </ul>' % items)
        else:
            raise ValueError(kind)
    body = '\n'.join(body)

    return '''<section id="fv" class="kin-fv kin-fv--visual">
  <figure class="kin-fv__visual ohaka-hero{hero_cls}">
    <img src="../townlife-ohaka/images/hero-family.png" alt="明るい自宅でタブレットを見ながら相談する夫婦のイメージ" width="1536" height="1024" fetchpriority="high">
    <div class="ohaka-hero__copy">
      <p>家族で考える、これからのお墓</p>
      <h1 id="main-title">{spans}</h1>
    </div>
    <!-- ティザー：画像に文字は焼き込まず、HTMLテキストのカードを写真に重ねる -->
    <div class="fv-card">
      <p class="fv-card__ttl{ttl_cls}">{ttl}</p>
      <p class="fv-card__txt">{txt}</p>
      <a class="fv-card__btn" href="#service"><span aria-hidden="true">↓</span>どんな探し方か見てみる</a>
    </div>
  </figure>
  <div class="entry-content ohaka-intro">
    <p class="kin-banner-label kin-banner-label--campaign">PR</p>
    <p class="fv-note">※本記事中の画像はイメージです。<br>※本記事の金額・内容は一例です。</p>
{intro}
  </div>
</section>

<div class="entry-content">

<!-- ===== 検索への即答【KW別】 ===== -->
<section id="points" class="sec">
  <header class="sec-head" data-reveal>
    <p class="sec-eyebrow">{eyebrow}</p>
    <h2><span>{h2}</span></h2>
  </header>
{body}
'''.format(hero_cls=hero_cls, spans=spans, ttl_cls=ttl_cls, ttl=lp['ttl'], txt=lp['txt'],
           intro=intro, eyebrow=lp['eyebrow'], h2=lp['h2'], body=body)

written = []
for lp in LPS:
    html = to_child_paths(build_head(lp)) + build_variable(lp) + to_child_paths(fixed_part)
    d = os.path.join(ROOT, lp['slug'])
    os.makedirs(d, exist_ok=True)
    io.open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(html)
    written.append(lp['slug'])

# マスターが変わっていないことを念のため確認
assert io.open(MASTER, encoding='utf-8').read() == src, 'index.html を書き換えてしまっている'
print('生成:', len(written), 'ページ')
print('共通部（H3以降）:', len(fixed_part), '文字 / sha1', hashlib.sha1(fixed_part.encode()).hexdigest()[:12])
