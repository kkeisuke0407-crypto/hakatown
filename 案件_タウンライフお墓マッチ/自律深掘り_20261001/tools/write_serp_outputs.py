# -*- coding: utf-8 -*-
"""③SERP意図監査.csv と ④SERPから発見した専門語.csv を、全周の判定ファイルから作り直す。

判定ファイル tools/judgments_*.py（ファイル名順）が持てる変数：
  ROUND / ROUND_LABEL     : 周（r1, r2 …）と表示名
  SERP_JUDGE              : {keyword: (検索意図, CV距離, 出稿候補, 理由)}   → ③
  TERMS                   : [(専門語, KWP投入形, 種類, 出典, 一段深い理由)]  → ④（KWP投入）
  TERMS_HOLD              : [(専門語, 保留/除外, 理由)]                       → ④
  TERMS_JSON              : raw/ の本文抽出結果（出現ページ数の参照用）
"""
import csv, importlib, io, json
from pathlib import Path
import kwlib, serp

OUT3 = kwlib.HERE / "③SERP意図監査.csv"
OUT4 = kwlib.HERE / "④SERPから発見した専門語.csv"
H3 = ["周", "keyword", "既存区分", "観測面", "取得日時", "上位1〜3位", "上位10件の構成（自動の目安）",
      "関連する質問", "関連検索", "Googleサジェスト", "検索意図", "CV距離", "出稿候補", "判定理由"]
H4 = ["周", "専門語", "KWP投入形", "種類", "出典", "一段深い理由", "本文の出現ページ数", "見つかったseed", "既存区分", "既存の根拠", "判定"]

def modules():
    for p in sorted(Path(__file__).parent.glob("judgments_*.py")):
        yield importlib.import_module(p.stem)

def main():
    rows3, rows4 = [], []
    for m in modules():
        label = getattr(m, "ROUND_LABEL", m.__name__)
        for kw, (intent, dist, cand, why) in getattr(m, "SERP_JUDGE", {}).items():
            r = serp.fetch(kw); s = serp.summarize(r); st, _ = kwlib.existing_status(kw)
            rows3.append([label, kw, st, r.get("engine", ""), r.get("fetched_at", ""), s["top3"], s["composition"],
                          " / ".join(x["question"] for x in r.get("paa", [])), " / ".join(r.get("related", [])),
                          " / ".join(r.get("google_suggest", [])[:10]), intent, dist, cand, why])
        tj = kwlib.HERE / "raw" / getattr(m, "TERMS_JSON", "")
        terms = json.load(io.open(tj, encoding="utf-8")) if tj.is_file() else {}
        for t, form, kind, src, why in getattr(m, "TERMS", []):
            hit = terms.get(t) or {}; st, ev = kwlib.existing_status(form)
            rows4.append([label, t, form, kind, src, why, hit.get("pages", ""), " / ".join(hit.get("seeds", [])[:6]), st, ev, "KWP投入"])
        for t, verdict, why in getattr(m, "TERMS_HOLD", []):
            hit = terms.get(t) or {}; st, ev = kwlib.existing_status(t)
            rows4.append([label, t, "", "", "SERP本文・関連検索", why, hit.get("pages", ""), " / ".join(hit.get("seeds", [])[:6]), st, ev, verdict])
    for path, h, rows in ((OUT3, H3, rows3), (OUT4, H4, rows4)):
        with io.open(path, "w", encoding="utf-8-sig", newline="") as f:
            cw = csv.writer(f); cw.writerow(h); cw.writerows(rows)
    print("③", len(rows3), "行 / ④", len(rows4), "行")

if __name__ == "__main__":
    main()
