# hakatown

タウンライフお墓マッチ 記事LP（KW：霊園探し）

- 公開URL: https://hakatown.hakobu-family.com/
- 制作元: `Documents/Codex/タウンライフお墓/作業中/LP/v8`

## 構成

- `index.html` … 記事LP本体
- `townlife-ohaka/styles.css` … このLP用のスタイル
- `townlife-ohaka/3sha-base.css` … ベースのレイアウトCSS
- `townlife-ohaka/app.js`
- `townlife-ohaka/images/` … FV・図版・操作画面・公式素材

## 公開の仕組み

`main` への push で GitHub Actions（`.github/workflows/static.yml`）がリポジトリ全体を
GitHub Pages へデプロイします。独自ドメインは `CNAME` で指定しています。

## 横展開するとき

差し替えるのは FV と「霊園探しで見るのは、この4つ」のブロックのみ。
それ以降は共通CVブロックとして再利用できます（`index.html` 内のコメント参照）。
