# PPC記事LP テンプレート

`docs/LP-PLAYBOOK.md` の構成をそのまま動く形にしたもの。
新しい案件はこのフォルダをコピーして始める。

```bash
cp -r template/ ../new-project/
cd ../new-project/
```

---

## 中身

```
index.html          マスターLP。構成は完成済み、中身は見本
assets/
  styles.css        デザイン一式（ここを育てる）
  3sha-base.css     土台
  app.js            スクロールイン演出
  images/           画像（空。案件ごとに入れる）
about/index.html    運営者情報ページ
tools/
  lp_data.py        横展開LPのコピー（雛形1本入り）
  build_lp.py       横展開の生成
  verify_copy.py    コピー・共通部の照合
  qa_lp.mjs         表示検査
```

**`index.html` は空の骨ではなく、動く見本。**
文章を上書きしていく方が、白紙から組むより品質が安定する。
セクションごとに `【可変】` `【固定】` と意図をコメントで書いてある。

---

## 差し替える6つ

### 1. 色（`assets/styles.css` の `:root`）

ブランドに合わせて変える。**役割は変えない。**

| 変数 | 役割 |
| --- | --- |
| `--gold` `--cta` `--cta-bottom` | ブランド色。見出し・CTA |
| `--hot` `--hot-bg` | **サービス名だけに使う赤。他では使わない** |
| `--mk` | 見出しマーカー（ブランド色の淡いもの） |
| `--marker` | 本文マーカー（黄） |
| `--note` `--arrow` `--accent-txt` | 文字用。**薄くしない** |

色を変えたら必ずコントラストを確認する（WCAG AA：通常4.5:1）。

### 2. `index.html` の中身

上から順に、コメントの意図に沿って書き換える。
**セクションの順番・クラス・見出しの階層は変えない。**

### 3. 画像（`assets/images/`）

必要なもの：ヒーロー、選択肢の図、比較の図、提案フロー図、
困っている様子、公式トップ、操作スクショ、事例写真。

- WebP化して1枚1MB以下
- `<img>` の `width` / `height` は**実寸を入れる**（ズレるとCLS）
- 差し替えたらファイルが切れていないか確認（`docs/LP-CHECKLIST.md` A参照）

### 4. 計測とCTA

- `index.html` の `G-XXXXXXXXXX` を GA4 の測定IDに
- CTAの `href` を遷移先に（5か所）
- `data-cta` は**設置位置ごとに違う値**にする（使い回さない）
- `tools/qa_lp.mjs` の `CTA_URL` `CTA_COUNT` `HOT` `GOLD` を案件の値に

### 5. 横展開（`tools/lp_data.py`）

検索意図ごとに1ブロック足す。書き方は同ファイルの見本と
`docs/LP-PLAYBOOK.md` 7章。

### 6. 運営者情報（`about/index.html`）

サイト名・運営者名を入れる。
**事実でない所在地・連絡先は書かない。** 無いなら項目ごと消す。

---

## 回し方

```bash
python3 tools/build_lp.py                        # 横展開を生成
python3 tools/verify_copy.py                     # 照合   → NG 0
node tools/qa_lp.mjs '["slug-a","slug-b"]'       # 表示   → 問題なし
```

**共通部を直すときは `index.html` だけを編集して再生成する。**
横展開LPを直接編集しない（次の生成で消える）。

公開前は `docs/LP-CHECKLIST.md` を上から通す。

### コピー直後は検査が落ちる（正しい挙動）

CTAの遷移先とGA4のIDが未設定なので、`qa_lp.mjs` が
`CTAリンク異常` を、`verify_copy.py` が `G-XXXXXXXXXX が欠落` を出す。
**設定を忘れたまま公開できないようにしてある。**
上の「差し替える6つ」の4番を済ませれば通る。

---

## 変えてはいけないもの

品質を再現するための土台。

- セクションの順番（痛み → 認識転換 → サービス登場）
- 見出しの階層（帯／マーカー＋下線／■ の3段階）
- **赤はサービス名の1か所だけ**というルール
- 演出を `js-reveal` クラスで制御する仕組み
  （JS無効・動き抑制設定でも内容が必ず見える）
- 検査スクリプト2本を通す運用
