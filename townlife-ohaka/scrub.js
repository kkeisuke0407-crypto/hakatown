/* 「やることは、5つだけ。」の操作画面を動かす。
   - 画面に入ったら自動再生し、最後まで行ったら最初に戻る。画面から外れたら止める
   - タップ（または「次のSTEPへ」ボタン）で次のSTEPへ飛ばせる。ページのスクロールは止めない
   - 動画ファイルではないので、iPhoneの低電力モードでも止まらない
   - JSが動かない環境では、HTMLに書いた STEP 1〜5 の文章がそのまま読める
   - 動きを減らす設定の人には自動再生せず、ボタンでSTEPごとに切り替えるだけにする */
(function () {
  var root = document.querySelector('[data-scrub]');
  if (!root || !('IntersectionObserver' in window) || !window.requestAnimationFrame) return;

  var BASE = new URL('./images/', document.currentScript.src).href;
  var REDUCE = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var END = 17.4;                  // 演出の長さ(秒)
  var HOLD = 1.6;                  // 最後の画面で止める時間(秒)。そのあと最初に戻る
  var CARD_W = 560, CARD_H = 700;  // 絵の設計サイズ。表示時はこれを縮小する
  var SCR_W = 452, SCR_H = 658;    // スマホ画面の見えている範囲

  // 画面（座標はすべて元画像のピクセル。表示ファイルの解像度とは無関係）
  var SHOTS = {
    a: { f: 'steps-01-area.webp',       w: 710,  h: 965 },
    b: { f: 'steps-02-prefecture.webp', w: 710,  h: 1220 },
    c: { f: 'steps-03-chat.webp',       w: 710,  h: 1155 },
    d: { f: 'steps-04-companies.webp',  w: 1170, h: 2073 },
    e: { f: 'steps-05-info.webp',       w: 690,  h: 565 }
  };
  Object.keys(SHOTS).forEach(function (k) { SHOTS[k].s = SCR_W / SHOTS[k].w; });
  // STEP の区切り（秒）と、画面の切り替え
  var STEPS = [[0, 4.6], [4.6, 7.8], [7.8, 10.9], [10.9, 14.2], [14.2, END]];
  var SEGS = [['a', 0], ['b', 2.3], ['c', 4.6], ['d', 7.8], ['e', 14.2]];
  var SLIDE = 0.45;
  // 動きを減らす設定のときに見せる各STEPの完成状態（秒）
  var KEY = [4.46, 7.0, 10.4, 14.18, 17.35];
  // 演出。tap=指が動いてタップ / hl=枠で強調 / ring=丸で強調 / press=押した影 / check=チェック / caret=入力カーソル
  var FX = [
    { k: 'a', kind: 'tap', t: [0.55, 1.25, 1.35, 1.95], from: [420, 560], to: [588, 756] },
    { k: 'a', kind: 'hl', t: [1.35, 2.3], box: [530, 700, 648, 810] },
    { k: 'b', kind: 'tap', t: [2.95, 3.55, 3.65, 4.2], from: [330, 760], to: [104, 891] },
    { k: 'b', kind: 'hl', t: [3.65, 4.6], box: [72, 858, 560, 926] },
    { k: 'b', kind: 'check', t: [3.7, 4.6], at: [104, 891] },
    { k: 'c', kind: 'tap', t: [5.2, 5.9, 6.0, 6.6], from: [580, 880], to: [505, 1053] },
    { k: 'c', kind: 'press', t: [6.0, 6.35], box: [366, 1000, 646, 1105] },
    { k: 'c', kind: 'hl', t: [6.35, 7.8], box: [366, 1000, 646, 1105] },
    { k: 'd', kind: 'hl', t: [8.6, 10.9], box: [165, 470, 1090, 552] },
    { k: 'd', kind: 'hl', t: [9.2, 10.9], box: [165, 1093, 1090, 1175] },
    { k: 'd', kind: 'hl', t: [9.8, 10.9], box: [165, 1721, 780, 1806] },
    { k: 'd', kind: 'ring', t: [11.3, 12.6], at: [101, 424] },
    { k: 'd', kind: 'ring', t: [11.6, 12.6], at: [101, 1071] },
    { k: 'd', kind: 'ring', t: [11.9, 12.6], at: [101, 1698] },
    { k: 'd', kind: 'tap', t: [12.5, 13.2, 13.3, 13.9], from: [760, 1640], to: [585, 1975] },
    { k: 'd', kind: 'press', t: [13.3, 13.65], box: [60, 1895, 1110, 2060], r: 60 },
    { k: 'e', kind: 'hl', t: [15.0, END], box: [62, 305, 630, 400] },
    { k: 'e', kind: 'caret', t: [15.3, END], box: [90, 334, 93, 372] }
  ];

  var clamp = function (x, a, b) { return Math.min(b, Math.max(a, x)); };
  var lin = function (t, a, b) { return clamp((t - a) / (b - a), 0, 1); };
  var ease = function (x) { return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
  var out = function (x) { return 1 - Math.pow(1 - x, 3); };
  var make = function (cls, parent) { var e = document.createElement('div'); e.className = cls; parent.appendChild(e); return e; };
  function scrollY(k, t) {
    var over = Math.max(0, SHOTS[k].h * SHOTS[k].s - SCR_H);
    if (k === 'd') return -over * ease(lin(t, 8.3, 10.3));
    if (k === 'c') return -over;   // チャットは回答ボタンが見える位置
    return 0;
  }

  var pin = root.querySelector('.scrub__pin');
  var caps = [].slice.call(root.querySelectorAll('.scrub__steps > li'));
  var stage = root.querySelector('.scrub__stage');
  var bars = [], shotEls = {}, fxEls = [], built = false, card, nextBtn, lastStep = -1;

  function build() {
    if (built) return; built = true;
    var bar = make('scrub__bar', pin); pin.insertBefore(bar, pin.firstChild);
    for (var i = 0; i < 5; i++) bars.push(make('', make('scrub__seg', bar)));
    card = make('scrub__card', stage);
    make('scrub__phone', card);
    var screen = make('scrub__screen', card);
    var shots = make('scrub__shots', screen), fx = make('scrub__fx', screen);
    Object.keys(SHOTS).forEach(function (k) { shotEls[k] = make('scrub__shot', shots); });
    FX.forEach(function (f) {
      if (REDUCE && (f.kind === 'tap' || f.kind === 'press')) return;
      var o = { f: f };
      if (f.kind === 'tap') { o.a = make('scrub__ov scrub__ripple', fx); o.b = make('scrub__ov scrub__finger', fx); }
      else if (f.kind === 'check') {
        o.a = make('scrub__ov scrub__check', fx);
        o.a.innerHTML = '<svg width="20" height="20" viewBox="0 0 20 20"><path d="M3 10.5l4.5 4.5L17 5" fill="none" stroke="#00b3bd" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
      }
      else o.a = make('scrub__ov scrub__' + f.kind, fx);
      fxEls.push(o);
    });
    nextBtn = document.createElement('button');
    nextBtn.type = 'button'; nextBtn.className = 'scrub__next';
    pin.appendChild(nextBtn);
    root.classList.add('scrub--on');
    layout(); render(0);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { layout(); render(t); });
  }
  // 画像は近づいてから読み込む（高さはページを開いた時点で確定させ、途中でずれないようにする）
  var loaded = false;
  function loadImages() {
    if (loaded) return; loaded = true;
    Object.keys(SHOTS).forEach(function (k) {
      var img = document.createElement('img');
      img.src = BASE + SHOTS[k].f; img.alt = ''; img.decoding = 'async';
      shotEls[k].appendChild(img);
    });
  }

  // 画面の高さに合わせて、絵の大きさとスクロール量を決める
  var probe = document.createElement('div');
  probe.style.cssText = 'position:fixed;top:0;height:100vh;height:100svh;width:0;visibility:hidden;pointer-events:none';
  document.body.appendChild(probe);
  function layout() {
    var vh = probe.offsetHeight || window.innerHeight;
    var capH = 0;
    caps.forEach(function (li) { capH = Math.max(capH, li.offsetHeight); });
    root.style.setProperty('--scrub-cap', capH + 'px');
    var w = pin.clientWidth;
    var free = vh - capH - 110;    // 進捗バー・ボタン・余白ぶんを引く（1画面に収める）
    var s = Math.min(w / CARD_W, free / CARD_H, 1);
    s = Math.max(s, 0.3);
    stage.style.width = Math.round(CARD_W * s) + 'px';
    stage.style.height = Math.round(CARD_H * s) + 'px';
    card.style.transform = 'scale(' + s + ')';
  }

  function stepOf(t) { var step = 0; STEPS.forEach(function (s, i) { if (t >= s[0]) step = i; }); return step; }
  function render(t) {
    var step = stepOf(t);
    if (REDUCE) t = KEY[step];
    if (step !== lastStep) { lastStep = step; nextBtn.innerHTML = step === 4 ? 'もう一度見る' : '次のSTEPへ<span aria-hidden="true">›</span>'; }
    // 進捗バー
    bars.forEach(function (b, i) { b.style.transform = 'scaleX(' + (REDUCE ? (i <= step ? 1 : 0) : lin(t, STEPS[i][0], STEPS[i][1])) + ')'; });
    // 文章（STEPごとに入れ替え）
    caps.forEach(function (li, i) {
      var s = STEPS[i], o = 1, y = 0;
      if (REDUCE) o = i === step ? 1 : 0;
      else if (t < s[0] || (i < 4 && t >= s[1])) o = 0;
      else {
        if (s[0] > 0) { var p = out(lin(t, s[0], s[0] + 0.35)); o = p; y = (1 - p) * 10; }
        if (i < 4) { var q = lin(t, s[1] - 0.2, s[1]); o *= 1 - q; y -= q * 8; }
      }
      li.style.opacity = o; li.style.transform = 'translateY(' + y + 'px)';
      li.style.visibility = o > 0.01 ? 'visible' : 'hidden';
    });
    // 画面（横に送る）
    var cur = 0; SEGS.forEach(function (g, i) { if (t >= g[1]) cur = i; });
    var offs = {}; Object.keys(SHOTS).forEach(function (k) { offs[k] = null; });
    var g = SEGS[cur], p = g[1] > 0 ? ease(lin(t, g[1], g[1] + SLIDE)) : 1;
    offs[g[0]] = (1 - p) * SCR_W;
    if (cur > 0 && p < 1) offs[SEGS[cur - 1][0]] = -p * SCR_W;
    Object.keys(SHOTS).forEach(function (k) {
      var e = shotEls[k];
      if (offs[k] === null) { e.style.display = 'none'; return; }
      e.style.display = 'block'; e.style.transform = 'translate(' + offs[k] + 'px,' + scrollY(k, t) + 'px)';
    });
    // 演出
    fxEls.forEach(function (o) {
      var f = o.f, a = o.a, b = o.b, dx = offs[f.k];
      var hide = function (x) { if (x) x.style.display = 'none'; };
      var at = function (x, y) { var s = SHOTS[f.k].s; return [x * s + dx, y * s + scrollY(f.k, t)]; };
      if (dx === null) { hide(a); hide(b); return; }
      if (f.kind === 'tap') {
        var t0 = f.t[0], t1 = f.t[1], t2 = f.t[2], t3 = f.t[3];
        if (t < t0 || t > t3 + 0.25) { hide(a); hide(b); return; }
        var m = ease(lin(t, t0 + 0.1, t1));
        var P = at(f.from[0] + (f.to[0] - f.from[0]) * m, f.from[1] + (f.to[1] - f.from[1]) * m);
        b.style.display = 'block'; b.style.left = P[0] + 'px'; b.style.top = P[1] + 'px';
        b.style.opacity = lin(t, t0, t0 + 0.2) * (1 - lin(t, t3, t3 + 0.25));
        b.style.transform = 'scale(' + (t >= t2 && t < t2 + 0.18 ? 0.84 : 1) + ')';
        var r = lin(t, t2, t2 + 0.5);
        if (t >= t2 && r < 1) { a.style.display = 'block'; a.style.left = P[0] + 'px'; a.style.top = P[1] + 'px'; a.style.opacity = 1 - r; a.style.transform = 'scale(' + (1 + r * 1.6) + ')'; }
        else hide(a);
        return;
      }
      if (t < f.t[0] || t >= f.t[1]) { hide(a); return; }
      var fade = REDUCE ? 1 : out(lin(t, f.t[0], f.t[0] + 0.25));
      a.style.display = 'block';
      if (f.kind === 'ring' || f.kind === 'check') {
        var Q = at(f.at[0], f.at[1]);
        a.style.left = (f.kind === 'check' ? Q[0] - 10 : Q[0]) + 'px'; a.style.top = (f.kind === 'check' ? Q[1] - 11 : Q[1]) + 'px';
        a.style.opacity = fade;
        a.style.transform = f.kind === 'ring' ? 'scale(' + (1 + 0.35 * Math.sin(lin(t, f.t[0], f.t[0] + 0.6) * Math.PI)) + ')' : 'scale(' + (0.6 + 0.4 * fade) + ')';
        return;
      }
      var A = at(f.box[0], f.box[1]), B = at(f.box[2], f.box[3]);
      a.style.left = A[0] + 'px'; a.style.top = A[1] + 'px'; a.style.width = (B[0] - A[0]) + 'px'; a.style.height = (B[1] - A[1]) + 'px';
      if (f.r) a.style.borderRadius = (f.r * SHOTS[f.k].s) + 'px';
      if (f.kind === 'press') a.style.opacity = 1 - lin(t, f.t[1] - 0.15, f.t[1]);
      else if (f.kind === 'caret') a.style.opacity = REDUCE || Math.floor((t - f.t[0]) / 0.5) % 2 === 0 ? 1 : 0;
      else a.style.opacity = fade;
    });
  }

  // 再生：見えている間だけ時間を進める（t は演出の秒）
  var t = 0, playing = false, last = 0, holdAt = 0, dipAt = 0;
  function frame(now) {
    if (!playing) return;
    var dt = last ? Math.min(0.1, (now - last) / 1000) : 0; last = now;
    if (!REDUCE) {
      t += dt;
      if (t >= END) {
        t = END;
        if (!holdAt) holdAt = now;
        if (now - holdAt > HOLD * 1000) restart(now);
      }
    }
    card.style.opacity = dipAt ? 0.35 + 0.65 * lin(now, dipAt, dipAt + 350) : 1;
    render(t);
    requestAnimationFrame(frame);
  }
  function restart(now) { t = 0; holdAt = 0; dipAt = REDUCE ? 0 : now; }
  function play() { if (playing || REDUCE) return; playing = true; last = 0; requestAnimationFrame(frame); }
  function pause() { playing = false; }
  // タップで次のSTEPへ（最後のSTEPなら最初から）
  function next() {
    var step = stepOf(t);
    holdAt = 0;
    if (step === 4) restart(performance.now());
    else t = STEPS[step + 1][0];
    render(t);
  }

  build();
  root.addEventListener('click', function (e) { if (!e.target.closest('a')) next(); });
  new IntersectionObserver(function (es) { if (es[0].isIntersecting) loadImages(); }, { rootMargin: '1500px 0px' }).observe(root);
  new IntersectionObserver(function (es) { if (es[0].intersectionRatio >= 0.3) play(); else pause(); }, { threshold: [0, 0.3, 0.6] }).observe(root);
  var rt;
  addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(function () { layout(); render(t); }, 150); });
})();
