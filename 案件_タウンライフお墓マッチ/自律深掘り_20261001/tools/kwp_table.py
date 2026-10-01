# -*- coding: utf-8 -*-
"""KWP第N回結果.csv を作る（生データのまま。1レコード1行）。
  python3 tools/kwp_table.py r1 "②KWP第1回結果.csv"
"""
import sys
import kwlib, common

H = ["keyword", "seed", "月間検索Vol", "競合", "競合指数", "上部掲載単価_低値", "上部掲載単価_高値", "平均CPC相当値",
     "取得方法", "調査した地域", "取得日", "既存区分", "既存の根拠", "規制判定（rules_ohaka）", "規制の理由", "地名入り（今回対象外）"]

def main(rnd, name):
    rows = []
    for r in common.rows_of(rnd):
        k = r["keyword"]
        st, ev = kwlib.existing_status(k) if k else ("", "")
        lvl, why = common.regulation(k) if k else ("", "")
        rows.append([k, r["seed"], r.get("vol"), r.get("comp"), r.get("comp_idx"), r.get("low"), r.get("high"), r.get("avg"),
                     r["method"], r.get("region"), r.get("date"), st, ev, lvl, why, "地名あり" if k and common.has_geo(k) else ""])
    common.write_csv(kwlib.HERE / name, H, rows)
    kws = {kwlib.compact(r[0]) for r in rows if r[0]}
    print(f"{name}: {len(rows)} 行 / ユニーク {len(kws)} 語")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
