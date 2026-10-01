# RUNBOOK｜KWP探索ループの続きを回す手順（次のセッション用）

依頼の原文は `依頼書.md`。判断基準はすべてそこに従う。
このフォルダは「seed作成 → seedのSERP → 業界語抽出（1周目の前半）」まで終わっている。
**KWPはまだ1回も取得していない**（前のセッションに Google Ads API の認証情報が無かったため）。

---

## 0. 準備（毎回のセッションで1回）

```bash
cd hozon/案件_タウンライフお墓マッチ/自律深掘り_20261001
python3 -m venv .venv
.venv/bin/pip install -q -e ../../kwp_mcp sudachipy sudachidict_core
# 認証情報が環境変数に入っているか（値は表示しない）
for v in GOOGLE_ADS_DEVELOPER_TOKEN GOOGLE_ADS_CLIENT_ID GOOGLE_ADS_CLIENT_SECRET GOOGLE_ADS_REFRESH_TOKEN GOOGLE_ADS_LOGIN_CUSTOMER_ID GOOGLE_ADS_CUSTOMER_ID; do
  [ -n "${!v}" ] && echo "$v OK" || echo "$v なし"; done
```

- システムの pip には入れない（PyJWT がDebian管理で衝突する）。必ず `.venv` を使う
- `kwp_mcp` は READ ONLY（書き込み系の呼び出しを持たない）。広告アカウントは変更されない
- 以下のコマンドはすべて `.venv/bin/python` で実行する（`tools/` 内で `python` と書いた所も同じ）

## 1. 1周目：KWP

```bash
.venv/bin/python tools/kwp_round.py r1 ①探索seed一覧.csv            # Historical + Ideas（再開可能）
.venv/bin/python tools/kwp_table.py r1 "②KWP第1回結果.csv"         # 生データ1行1レコード
.venv/bin/python tools/kwp_pick.py r1 200                          # 選別用の確認表（raw/pick_r1.csv）
```

## 2. 1周目：Claudeの選別 → SERP → 専門語

1. `raw/pick_r1.csv` と画面の一覧を読み、依頼書STEP3の基準で有望語を選ぶ
   - Vol10〜30でも、NO DATAでも、具体性が高ければ残す
   - 地名入りは対象外（`⑨` に自動で「地域横展開枠」として分かれる）
   - 規制判定（`rules_ohaka.regulation`）が HIGH でも「注記」付きのもの（仏壇型・位牌式の納骨堂、ペットと一緒に入れる墓）は
     ルール側の誤判定の可能性があるので、除外せず保留にしてユーザーに確認する
2. 有望語の SERP を取る：`.venv/bin/python tools/serp.py "語1" "語2" …`（Yahoo! JAPAN＝Googleの検索エンジン。結果は raw/serp/ に保存）
3. 上位ページ本文から業界語を抜く：
   ```python
   import terms, json; res = terms.extract(["語1","語2",...]); json.dump(res, open("raw/terms_round1b.json","w"), ensure_ascii=False)
   ```
   3ページ以上に出る語を、既存の母集団にあるか（`kwlib.existing_status`）を見ながら読む
4. 判定を `tools/judgments_r1b_kwp.py` に書く（形式は `tools/judgments_r1a_seed.py` と同じ）
   ```python
   ROUND = "r1"; ROUND_LABEL = "1周目（KWP選別後のSERP）"; TERMS_JSON = "terms_round1b.json"
   SERP_JUDGE = {kw: (検索意図, CV距離A/B/C, 候補/保留/除外, 理由)}      # SERPを見た語（→③）
   KW_JUDGE   = {kw: (検索意図, CV距離, 候補/保留/除外, 理由[, LP])}     # KWPで見た語の判定（→⑦〜⑪）
   TERMS      = [(専門語, KWP投入形, 種類, 出典, 一段深い理由)]           # 次の周へ（→④）
   TERMS_HOLD = [(専門語, 保留/除外, 理由)]
   NEXT_KWP   = [(KWPの結果から次の周に回す語, 理由)]
   ```
   - CV距離：A=霊園・墓を探す/比べる段階、B=墓種・条件を調べる段階、C=意味・手続き・既にお墓がある人
5. `.venv/bin/python tools/write_serp_outputs.py` で ③④ を作り直す（全周ぶん）

## 3. 2周目・3周目

```bash
.venv/bin/python tools/make_next_seeds.py r2          # 前の周の TERMS と NEXT_KWP から raw/seeds_r2.csv（KWP済みは除く）
.venv/bin/python tools/kwp_round.py r2 raw/seeds_r2.csv
.venv/bin/python tools/kwp_table.py r2 "⑤KWP第2回結果.csv"
.venv/bin/python tools/kwp_pick.py r2 200
# → 2. と同じ選別・SERP・専門語（judgments_r2.py, terms_round2.json）
.venv/bin/python tools/make_next_seeds.py r3
.venv/bin/python tools/kwp_round.py r3 raw/seeds_r3.csv
.venv/bin/python tools/kwp_table.py r3 "⑥KWP第3回結果.csv"
```

- 1周目のSERPで先に拾った61語（`④` の「1周目（seed SERP・KWP前）」）は、2周目の seed に自動で入る
- KeywordIdeas が0件の seed は「この枝に検索需要なし」として ②⑤⑥ に行が残る。失敗ではない
- 新しい有望語がほとんど増えなくなった枝はそこで終える。3周目は有望枝だけでよい

## 4. 仕上げ

1. `tools/judgments_z_final.py` に初回テスト候補を書く（今回発見した**新規**から5〜20語。最初は5語程度から）
   ```python
   TEST_PICK = [(keyword, 選んだ理由, 想定LP, 除外KW案)]
   ```
   一致タイプは `build_final.py` が Vol から付ける（Vol100以下=フレーズ／100超=完全一致も可／ごく低Vol・NO DATA=インテントマッチでテスト）
2. `.venv/bin/python tools/build_final.py` → ⑦〜⑫ と `raw/stats.json`
3. `README.md` を更新（何周掘ったか・各周の発見数・新規数・有望な枝・死んだ枝・ラッコ使用有無・次に掘るテーマ）。数字は `raw/stats.json` から
4. hozon にコミット・プッシュ（既存ファイルは触らない）

## 注意

- KWP の low は「実際に取れるCPC」ではない（墓いらない：low約4円 → 実CPC約400円）。CPCの信用順は 実CPC ＞ Ads実績・予測 ＞ KWP avg/high ＞ KWP low
- Google を直接取得すると「通常と異なるトラフィック」の確認画面になる。回避しない。SERPは Yahoo! JAPAN（関連する質問も `GoogleWebAnswerShortcut`）
- ラッコキーワードは使っていない。自然な言い回しの補助として Google サジェストを `serp.py` が一緒に取っている
- 既存の母集団（照合先）：既存925／9/30追加調査（統合・除外）／10/01具体条件（統合・除外）／out の KWプール。`tools/kwlib.py` の `SOURCES`
