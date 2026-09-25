import pkg from '/opt/node22/lib/node_modules/playwright/index.js';
import fs from 'node:fs';
import path from 'node:path';
const { chromium } = pkg;
// スクリプトの位置から見たリポジトリ直下。どこに置いても動くようにする
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const slugs = JSON.parse(process.argv[2]);
const widths = [320, 360, 375, 390, 414, 820];
const b = await chromium.launch();
const problems = [];
const add = (s, w, msg) => problems.push(`${s} @${w}px  ${msg}`);

for (const slug of ['', ...slugs]) {
  const file = path.join(ROOT, slug, 'index.html');
  for (const w of widths) {
    const p = await b.newPage({ viewport: { width: w, height: 900 } });
    const missing = [];
    p.on('requestfailed', r => missing.push(r.url()));
    p.on('console', m => { if (m.type() === 'error') missing.push('console:' + m.text()); });
    await p.goto('file://' + file);
    // 全セクションを表示状態にしてから測る
    await p.evaluate(async () => {
      for (let y = 0; y < document.body.scrollHeight; y += 400) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 25)); }
      window.scrollTo(0, 0);
    });
    await p.waitForTimeout(700);
    // 近づいてから読み込む画像（操作画面など）が読み終わるのを待つ
    await p.evaluate(() => Promise.race([
      Promise.all([...document.images].filter(i => i.getAttribute('src') && !i.closest('details:not([open])')).map(i => i.decode().catch(() => {}))),
      new Promise(r => setTimeout(r, 5000))]));
    // 操作画面（スクロールで STEP が進む部品）：固定されるか、途中までスクロールすると STEP3 になるか
    const sc = await p.evaluate(async () => {
      const root = document.querySelector('[data-scrub]');
      if (!root) return { exists: false };
      const pin = root.querySelector('.scrub__pin');
      const res = { exists: true, on: root.classList.contains('scrub--on'), sticky: getComputedStyle(pin).position,
        imgs: root.querySelectorAll('img').length, broken: [...root.querySelectorAll('img')].filter(i => !i.naturalWidth).length };
      const top = root.getBoundingClientRect().top + scrollY, dist = root.offsetHeight - pin.offsetHeight;
      window.scrollTo(0, top + dist * 0.5);
      await new Promise(r => setTimeout(r, 150));
      const op = [...root.querySelectorAll('.scrub__steps>li')].map(li => +getComputedStyle(li).opacity);
      res.mid = op.indexOf(Math.max(...op)) + 1;
      res.pinTop = Math.round(pin.getBoundingClientRect().top);
      window.scrollTo(0, 0);
      await new Promise(r => setTimeout(r, 150));
      return res;
    });
    const r = await p.evaluate(() => {
      const out = {};
      out.hScroll = document.documentElement.scrollWidth - document.documentElement.clientWidth;
      const vw = document.documentElement.clientWidth;
      // 画面外にはみ出している要素
      out.overflow = [...document.querySelectorAll('main *')].filter(el => {
        const r = el.getBoundingClientRect();
        return r.width > 0 && (r.right > vw + 1.5 || r.left < -1.5);
      }).map(el => el.tagName.toLowerCase() + '.' + String(el.className || '').split(' ')[0]).slice(0, 5);
      // FV：H1ブロックとティザーカードの重なり
      const copy = document.querySelector('.ohaka-hero__copy h1');
      const card = document.querySelector('.fv-card');
      const hero = document.querySelector('.ohaka-hero');
      out.fvGap = Math.round(card.getBoundingClientRect().top - copy.getBoundingClientRect().bottom);
      out.cardBottomOut = Math.round(card.getBoundingClientRect().bottom - hero.getBoundingClientRect().bottom);
      out.heroH = Math.round(hero.getBoundingClientRect().height);
      // 隠れたままのテキスト（アニメ未発火）
      out.hidden = [...document.querySelectorAll('[data-reveal] h2')].filter(h => getComputedStyle(h).opacity !== '1').length;
      // 演出CSSが丸ごと消えても hidden は0になり素通りしてしまうので、CSSの存在自体を確かめる
      out.revealAlive = document.documentElement.classList.contains('js-reveal')
        && [...document.querySelectorAll('[data-reveal]')].length > 0
        && getComputedStyle(document.querySelector('[data-reveal]>*')).transitionDuration !== '0s';
      const sh = document.querySelector('.service-head');
      out.serviceMark = getComputedStyle(sh.querySelector('span')).backgroundImage.includes('gradient');
      out.serviceRule = getComputedStyle(sh, '::after').backgroundColor;
      out.ribbon = getComputedStyle(document.querySelector('.ribbon-head span'), '::before').backgroundColor;
      // 画像の読み込み失敗
      out.brokenImg = [...document.images].filter(i => !i.complete || i.naturalWidth === 0).map(i => i.getAttribute('src'));
      out.imgCount = document.images.length;
      out.ctas = [...document.querySelectorAll('a[data-cta]')].map(a => a.getAttribute('href'));
      out.title = document.title;
      out.h1 = document.querySelector('h1').innerText.replace(/\n/g, '');
      out.h2 = document.querySelector('#points h2').innerText;
      return out;
    });
    const name = slug || '(master /)';
    if (r.hScroll > 0) add(name, w, `横スクロール ${r.hScroll}px`);
    if (r.overflow.length) add(name, w, `はみ出し: ${r.overflow.join(', ')}`);
    if (r.fvGap < 8) add(name, w, `FVでH1とカードが接近/重なり gap=${r.fvGap}px`);
    if (r.cardBottomOut > 2) add(name, w, `FVカードがヒーロー下からはみ出し ${r.cardBottomOut}px`);
    if (r.hidden > 0) add(name, w, `非表示のまま残る見出し ${r.hidden}件`);
    if (!r.revealAlive) add(name, w, 'スクロールイン演出のCSSが効いていない');
    if (!r.serviceMark) add(name, w, 'サービス名の赤マーカーが消えている');
    if (r.serviceRule !== 'rgb(201, 55, 44)') add(name, w, `サービス名の赤下線が消えている (${r.serviceRule})`);
    if (r.ribbon !== 'rgb(23, 107, 101)') add(name, w, `リボンの装飾が消えている (${r.ribbon})`);
    const realBroken = r.brokenImg.filter(u => !/02-prefecture\.png/.test(u)); // details内の遅延画像は未展開で正常
    if (realBroken.length) add(name, w, `画像切れ: ${realBroken.join(', ')}`);
    if (r.ctas.some(h => h !== 'https://townlife-ohaka.jp/')) add(name, w, `CTAリンク異常: ${r.ctas}`);
    if (r.ctas.length !== 5) add(name, w, `CTA数が${r.ctas.length}（想定5）`);
    if (!sc.exists) add(name, w, '操作画面（data-scrub）がない');
    else {
      if (!sc.on || sc.sticky !== 'sticky') add(name, w, `操作画面の動きが効いていない (on=${sc.on}, position=${sc.sticky})`);
      if (sc.imgs !== 5 || sc.broken) add(name, w, `操作画面の画像 ${sc.imgs}枚 / 読めない ${sc.broken}枚`);
      if (sc.mid !== 3 || Math.abs(sc.pinTop) > 1) add(name, w, `操作画面が進まない/固定されない (中間でSTEP${sc.mid}, top=${sc.pinTop})`);
    }
    const realMiss = missing.filter(u => !/googletagmanager|ERR_TUNNEL/.test(u)); // 検証環境は外部通信遮断
    if (realMiss.length) add(name, w, `リクエスト失敗/エラー: ${realMiss.slice(0,3).join(' | ')}`);
    if (w === 390) console.log(`${name.padEnd(22)} 画像${r.imgCount} CTA${r.ctas.length} FV余白${String(r.fvGap).padStart(4)}px 高さ${r.heroH} | ${r.h1}`);
    await p.close();
  }
}
await b.close();
console.log('\n===== 検出された問題 =====');
console.log(problems.length ? problems.join('\n') : 'なし');
