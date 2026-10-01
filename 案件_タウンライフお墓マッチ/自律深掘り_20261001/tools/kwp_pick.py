# -*- coding: utf-8 -*-
"""Claude が選別するための確認表（raw/pick_<周>.csv）。採否はここでは決めない。
  python3 tools/kwp_pick.py r1 [表示件数]
新規・地名なし・商標でない語を、条件語を含むもの → 検索Vol の順に並べる。NO DATA の語も残す。
"""
import re, sys
import kwlib, common
COND = re.compile(r"承継|跡継|後継|管理費|管理料|維持費|年会費|個別|合祀|合葬|安置|期間|期限|満期|何年|何人|夫婦|家族|一人|ひとり"
                  r"|生前|寿陵|遺骨|宗派|宗旨|宗教|檀家|区画|空き|募集|抽選|落選|倍率|使用料|使用権|ローン|見積|相見積|比較|違い"
                  r"|費用|料金|相場|安い|購入|買|探|選び|見学|四十九日|一周忌|間に合|短納期|次男|分家|娘|嫁|夫|ペット|駅|送迎|バリアフリー|屋内|室内")

def aggregate(rows):
    agg = {}
    for r in rows:
        k = r["keyword"]
        if not k:
            continue
        c = kwlib.compact(k); a = agg.setdefault(c, dict(keyword=k, seeds=set(), methods=set(), vol=None, low=None, high=None, avg=None, comp=None, comp_idx=None, hist=False))
        a["seeds"].add(r["seed"]); a["methods"].add(r["method"])
        if r["method"].startswith("HistoricalMetrics") and not a["hist"]:
            a.update(vol=r.get("vol"), low=r.get("low"), high=r.get("high"), avg=r.get("avg"), comp=r.get("comp"), comp_idx=r.get("comp_idx"), hist=True)
        elif not a["hist"] and (r.get("vol") or 0) > (a["vol"] or 0):
            a.update(vol=r.get("vol"), low=r.get("low"), high=r.get("high"), avg=r.get("avg"), comp=r.get("comp"), comp_idx=r.get("comp_idx"))
    return agg

def main(rnd, show=150):
    agg = aggregate(common.rows_of(rnd))
    out = []
    for c, a in agg.items():
        k = a["keyword"]; st, ev = kwlib.existing_status(k); lvl, why = common.regulation(k)
        out.append([k, a["vol"], a["avg"], a["low"], a["high"], a["comp_idx"], " / ".join(sorted(a["seeds"]))[:120],
                    " / ".join(sorted(a["methods"])), st, lvl, why, "地名あり" if common.has_geo(k) else "",
                    "条件語あり" if COND.search(c) else "", common.lp_draft(k)])
    out.sort(key=lambda r: (r[8] != "新規", r[11] != "", r[9] == "HIGH", r[12] == "", -(r[1] or 0)))
    common.write_csv(common.RAW / f"pick_{rnd}.csv",
                     ["keyword", "Vol", "平均CPC", "low", "high", "競合指数", "seed", "取得方法", "既存区分", "規制", "規制理由", "地名", "条件語", "LP下書き"], out)
    shown = [r for r in out if r[8] == "新規" and not r[11] and r[9] != "HIGH"]
    print(f"[{rnd}] ユニーク {len(out)} 語 / 新規・地名なし・規制HIGHでない {len(shown)} 語（全件は raw/pick_{rnd}.csv）")
    for r in shown[:show]:
        print(f"  {r[0]:<28} Vol={r[1]!s:>6} avg={r[2]!s:>6} low={r[3]!s:>6} | {r[12] or '－':<4} | {r[13]} | {r[6][:40]}")

if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 150)
