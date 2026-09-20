// アフィリエイトリンク設定前は計測イベントを作りません。
// dataLayerイベントは中間クリックであり、提案依頼完了・成約ではありません。
document.querySelectorAll('[data-cta-position]').forEach(link => {
  link.addEventListener('click', () => {
    if (link.dataset.affiliateConfigured !== 'true') return;
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({event:'affiliate_click',offer:'townlife_ohaka',keyword:document.querySelector('[data-keyword]')?.dataset.keyword,cta_position:link.dataset.ctaPosition});
  });
});

// サービス名のブロックは、視界に入ったタイミングで出す。
// 隠す指定は <html class="js-reveal"> が付いているときだけ効くので、
// JSが動かない場合やアニメーションを控える設定の場合はそのまま表示される。
(function () {
  if (!document.documentElement.classList.contains('js-reveal')) return;
  var targets = document.querySelectorAll('[data-reveal]');
  if (!targets.length) return;
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      entry.target.dataset.reveal = 'in';
      io.unobserve(entry.target);
    });
  }, { threshold: 0.4 });
  targets.forEach(function (el) { io.observe(el); });
})();
