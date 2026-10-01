# -*- coding: utf-8 -*-
"""⑦〜⑫を作る。判定は tools/judgments_*.py（後の周が優先）。
judgments ファイルが持てる変数：
  SEED_JUDGE / KW_JUDGE : {keyword: (検索意図, CV距離A/B/C, 判断 候補/保留/除外, 理由[, LP])}
  TEST_PICK             : [(keyword, 理由, 想定LP, 除外KW案)]   ← ⑫ 初回テスト候補（Claudeが選ぶ）
"""
import importlib, json, re
from pathlib import Path
import kwlib, common, kwp_pick

def judgments():
    J, picks = {}, []
    for p in sorted(Path(__file__).parent.glob("judgments_*.py")):
        m = importlib.import_module(p.stem)
        for name in ("SEED_JUDGE", "KW_JUDGE"):
            for k, v in getattr(m, name, {}).items():
                J[kwlib.compact(k)] = v
        picks = getattr(m, "TEST_PICK", picks) or picks
    return J, picks

def match_type(vol):
    if vol in (None, "", 0):
        return "インテントマッチでテスト（KWPで数値なし。フレーズではimpが出にくい）"
    v = int(vol)
    if v <= 20:
        return "フレーズ一致（impが出なければインテントマッチでテスト）"
    if v <= 100:
        return "フレーズ一致"
    return "完全一致も可（Vol100超）"

def score(a, j):
    dist = {"A": 0, "B": 1, "C": 2}.get(j[1] if j else "", 3)
    return (dist, -(a["vol"] or 0), a["avg"] or 10**9, a["comp_idx"] if a["comp_idx"] is not None else 101)

def main():
    rnds = common.rounds()
    rows = [r for rnd in rnds for r in common.rows_of(rnd)]
    agg = kwp_pick.aggregate(rows)
    first = {}
    for r in rows:
        if r["keyword"]:
            first.setdefault(kwlib.compact(r["keyword"]), r["round"])
    J, picks = judgments()
    H = ["keyword", "初出の周", "seed", "取得方法", "月間検索Vol", "競合", "競合指数", "上部掲載単価_低値", "上部掲載単価_高値",
         "平均CPC相当値", "規制判定", "規制の理由", "CV距離", "判断", "検索意図", "判定理由", "LP", "類似グループ"]
    new, dup, excl, lp_rows = [], [], [], []
    for c, a in agg.items():
        k = a["keyword"]; st, ev = kwlib.existing_status(k); lvl, why = common.regulation(k); j = J.get(c)
        lp = (j[4] if j and len(j) > 4 and j[4] else common.lp_draft(k))
        base = [k, first.get(c, ""), " / ".join(sorted(a["seeds"]))[:200], " / ".join(sorted(a["methods"])), a["vol"], a["comp"],
                a["comp_idx"], a["low"], a["high"], a["avg"], lvl, why, j[1] if j else "", j[2] if j else "未判定",
                j[0] if j else "", j[3] if j else "", lp, kwlib.group(k)]
        if common.has_geo(k):
            excl.append(["対象外（地名入り：地域横展開枠）"] + base); continue
        if st != "新規":
            dup.append([k, st, ev, a["vol"], a["avg"], first.get(c, ""), " / ".join(sorted(a["seeds"]))[:120]]); continue
        new.append(base)
        if lvl in ("HIGH", "REVIEW") or (j and j[2] in ("除外", "保留")):
            if lvl == "HIGH" and "注記" in why and not (j and j[2] == "除外"):
                cls = "保留（案件ルールと要判断）"
            elif (j and j[2] == "除外") or lvl == "HIGH":
                cls = "除外"
            else:
                cls = "保留"
            excl.append([cls] + base)
        if j and j[2] in ("候補", "保留"):
            lp_rows.append(base)
    new.sort(key=lambda b: ({"A": 0, "B": 1, "C": 2}.get(b[12], 3), -(b[4] or 0)))
    common.write_csv(kwlib.HERE / "⑦新規KW統合版.csv", H, new)
    common.write_csv(kwlib.HERE / "⑧既存KWとの重複一覧.csv", ["keyword", "既存区分", "既存の根拠", "月間検索Vol", "平均CPC相当値", "初出の周", "seed"], dup)
    common.write_csv(kwlib.HERE / "⑨除外・保留KW.csv", ["区分"] + H, excl)
    # ⑪ 類似KW代表版（候補・保留のみ。同義語はまとめるが、墓種・費用/選び方の違いはキーが別になるので混ざらない）
    groups = {}
    for b in lp_rows:
        groups.setdefault(b[17], []).append(b)
    rep_rows, rep_of = [], {}
    for g, bs in groups.items():
        bs.sort(key=lambda b: score(agg[kwlib.compact(b[0])], J.get(kwlib.compact(b[0]))))
        rep = bs[0]
        for b in bs:
            rep_of[b[0]] = rep[0]
        rep_rows.append([rep[0], len(bs), " / ".join(b[0] for b in bs[1:]), rep[4], rep[9], rep[6], rep[12], rep[13], rep[16], g])
    rep_rows.sort(key=lambda r: ({"A": 0, "B": 1, "C": 2}.get(r[6], 3), -(r[3] or 0)))
    common.write_csv(kwlib.HERE / "⑪類似KW代表版.csv", ["代表KW", "まとめた語数", "まとめた語", "月間検索Vol", "平均CPC相当値", "競合指数", "CV距離", "判断", "LP", "類似グループのキー"], rep_rows)
    # ⑩ LP・AG分類（AG＝類似グループの代表KW）
    lp_out = sorted(([b[16], rep_of.get(b[0], b[0]), b[0], b[4], b[9], b[12], b[13], b[14]] for b in lp_rows), key=lambda r: (r[0], r[1]))
    common.write_csv(kwlib.HERE / "⑩LP_AG分類.csv", ["LP", "AG（類似グループの代表KW）", "keyword", "月間検索Vol", "平均CPC相当値", "CV距離", "判断", "検索意図"], lp_out)
    # ⑫ 初回テスト候補（Claudeが選んだ TEST_PICK）
    test = []
    for k, why, lp, neg in picks:
        a = agg.get(kwlib.compact(k)) or {}
        test.append([k, kwlib.existing_status(k)[0], a.get("vol"), a.get("avg"), a.get("low"), a.get("high"), a.get("comp_idx"), match_type(a.get("vol")), lp, why, neg])
    common.write_csv(kwlib.HERE / "⑫初回テスト候補5〜20KW.csv",
                     ["keyword", "既存区分", "月間検索Vol", "平均CPC相当値（KWP）", "上部掲載単価_低値", "上部掲載単価_高値", "競合指数", "一致タイプ", "想定LP", "選んだ理由", "除外KW案"], test)
    stats = dict(rounds=rnds, unique=len(agg), new=len(new), dup=len(dup), excl=len(excl), lp=len(lp_rows), groups=len(rep_rows), test=len(test),
                 by_round={rnd: len({kwlib.compact(r["keyword"]) for r in rows if r["round"] == rnd and r["keyword"]}) for rnd in rnds},
                 new_by_round={rnd: sum(1 for b in new if b[1] == rnd) for rnd in rnds})
    json.dump(stats, open(kwlib.HERE / "raw" / "stats.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(stats, ensure_ascii=False))

if __name__ == "__main__":
    main()
