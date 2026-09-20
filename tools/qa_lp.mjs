import pkg from '/opt/node22/lib/node_modules/playwright/index.js';
import fs from 'node:fs';
import path from 'node:path';
const { chromium } = pkg;
const ROOT = '/home/user/hakatown';
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
    const realBroken = r.brokenImg.filter(u => !/02-prefecture\.png/.test(u)); // details内の遅延画像は未展開で正常
    if (realBroken.length) add(name, w, `画像切れ: ${realBroken.join(', ')}`);
    if (r.ctas.some(h => h !== 'https://townlife-ohaka.jp/')) add(name, w, `CTAリンク異常: ${r.ctas}`);
    if (r.ctas.length !== 5) add(name, w, `CTA数が${r.ctas.length}（想定5）`);
    const realMiss = missing.filter(u => !/googletagmanager|ERR_TUNNEL/.test(u)); // 検証環境は外部通信遮断
    if (realMiss.length) add(name, w, `リクエスト失敗/エラー: ${realMiss.slice(0,3).join(' | ')}`);
    if (w === 390) console.log(`${name.padEnd(22)} 画像${r.imgCount} CTA${r.ctas.length} FV余白${String(r.fvGap).padStart(4)}px 高さ${r.heroH} | ${r.h1}`);
    await p.close();
  }
}
await b.close();
console.log('\n===== 検出された問題 =====');
console.log(problems.length ? problems.join('\n') : 'なし');
