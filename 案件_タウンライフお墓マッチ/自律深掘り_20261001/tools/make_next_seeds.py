# -*- coding: utf-8 -*-
"""次の周に KWP へ入れる seed（raw/seeds_<周>.csv）を作る。
  python3 tools/make_next_seeds.py r2
材料：その周より前の判定ファイルの TERMS（SERPから採った専門語）と NEXT_KWP（KWPの結果から次へ回す語）。
すでにどこかの周で KWP に入れた seed は除く（同じ枝を二度掘らない）。
"""
import csv, importlib, io, json, sys
from pathlib import Path
import kwlib

def main(rnd):
    asked = set()
    for p in (kwlib.HERE / "raw").glob("hist_*.jsonl"):
        asked |= {kwlib.compact(json.loads(l)["keyword"]) for l in p.open(encoding="utf-8")}
    for p in (kwlib.HERE / "raw").glob("ideas_*.jsonl"):
        asked |= {kwlib.compact(json.loads(l)["seed"]) for l in p.open(encoding="utf-8")}
    rows, seen = [], set()
    for p in sorted(Path(__file__).parent.glob("judgments_*.py")):
        m = importlib.import_module(p.stem)
        if getattr(m, "ROUND", "") >= rnd:
            continue
        label = getattr(m, "ROUND_LABEL", m.__name__)
        items = [(form, f"{label}：SERP専門語『{t}』", why) for t, form, kind, src, why in getattr(m, "TERMS", [])]
        items += [(k, f"{label}：KWP結果から", why) for k, why in getattr(m, "NEXT_KWP", [])]
        for form, origin, why in items:
            c = kwlib.compact(form)
            if c in asked or c in seen:
                continue
            seen.add(c); rows.append([form, origin, why])
    out = kwlib.HERE / "raw" / f"seeds_{rnd}.csv"
    with io.open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(["seed", "origin", "出典"]); w.writerows(rows)
    print(f"{out.name}: {len(rows)} 語（KWP取得済みの seed は除外）")

if __name__ == "__main__":
    main(sys.argv[1])
