// アフィリエイトリンク設定前は計測イベントを作りません。
// dataLayerイベントは中間クリックであり、提案依頼完了・成約ではありません。
document.querySelectorAll('[data-cta-position]').forEach(link => {
  link.addEventListener('click', () => {
    if (link.dataset.affiliateConfigured !== 'true') return;
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({event:'affiliate_click',offer:'townlife_ohaka',keyword:document.querySelector('[data-keyword]')?.dataset.keyword,cta_position:link.dataset.ctaPosition});
  });
});
