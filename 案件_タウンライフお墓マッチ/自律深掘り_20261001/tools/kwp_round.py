# -*- coding: utf-8 -*-
"""KWPを1周ぶん取得する（READ ONLY・再開可能）。

  python3 tools/kwp_round.py r1 ①探索seed一覧.csv            # seed列を読む
  python3 tools/kwp_round.py r2 raw/seeds_r2.csv               # 2周目（SERPから拾った語など）

各seedについて
  - Historical Metrics（seed自身の実測。平均CPCつき）
  - Keyword Ideas（seed 1語ずつ・limit=0で全ページ）
を取り、raw/hist_<周>.jsonl と raw/ideas_<周>.jsonl に生データのまま保存する。
地域設定は前回（追加調査_20260930・具体条件深掘り_20261001）と同じ配信予定10都府県を1リクエストで指定。

認証情報は環境変数（GOOGLE_ADS_DEVELOPER_TOKEN / CLIENT_ID / CLIENT_SECRET / REFRESH_TOKEN /
LOGIN_CUSTOMER_ID / CUSTOMER_ID）から kwp_mcp が読む。kwp_mcp は書き込み系の呼び出しを持たない。
"""
from __future__ import annotations
import csv, io, json, os, sys, time, warnings
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent.parent
CASE = HERE.parent
REPO = CASE.parent
RAW = HERE / "raw"; RAW.mkdir(exist_ok=True)
sys.path.insert(0, str(REPO / "kwp_mcp" / "src"))

GEO10 = json.load(io.open(CASE / "追加調査_20260930" / "geo10.json", encoding="utf-8"))
REGION = "・".join(g["jp"] for g in GEO10) + "（KWP地域設定・10都府県を1リクエストで指定）"
TODAY = time.strftime("%Y-%m-%d")

def mdict(gm):
    return dict(avg_monthly_searches=gm.avg_monthly_searches, competition=gm.competition,
                competition_index=gm.competition_index, low_bid=gm.low_top_of_page_bid,
                high_bid=gm.high_top_of_page_bid, average_cpc=gm.average_cpc)

def read_seeds(path: Path) -> list[dict]:
    with io.open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out, seen = [], set()
    for r in rows:
        s = " ".join((r.get("seed") or r.get("KWP投入形") or r.get("keyword") or "").split())
        if s and s not in seen:
            seen.add(s)
            out.append(dict(seed=s, origin=r.get("origin") or r.get("見つかったseed") or r.get("観点") or "",
                            source=r.get("出典") or r.get("source") or path.name))
    return out

def log(rnd, kind, label, n, total, err=None):
    with (RAW / "requests.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(dict(round=rnd, kind=kind, label=label, records=n, total_size=total, error=err,
                                region=REGION, at=time.strftime("%Y-%m-%d %H:%M:%S")), ensure_ascii=False) + "\n")

def main(rnd: str, seed_file: str):
    from kwp_mcp.config import Settings
    from kwp_mcp.server import Context
    from kwp_mcp.keyword_planner import TargetingContext

    settings = Settings.load()
    customer = os.environ.get("GOOGLE_ADS_CUSTOMER_ID") or "6661622672"   # 前回までと同じアカウント
    ctx = Context(settings)
    planner = ctx.planner
    lang = ctx.resolver.resolve_language("ja", customer_id=customer)

    def targeting(customer_id, country, language, network):
        return TargetingContext(
            geo_resource_names=[g["resource"] for g in GEO10], language_resource_name=lang.resource_name,
            country="JP10", language="ja", network="GOOGLE_SEARCH",
            geo={"key": "JP10", "prefs": [g["jp"] for g in GEO10]}, lang=lang.to_dict())
    planner.targeting = targeting
    opts = dict(include_average_cpc=True, country="JP10", language="ja", network="GOOGLE_SEARCH", force_refresh=True)

    seeds = read_seeds(Path(seed_file) if Path(seed_file).is_absolute() else HERE / seed_file)
    print(f"[{rnd}] seed {len(seeds)} 語 / 地域 {REGION}", flush=True)

    # ---- Historical Metrics（seed 自身）----
    hp = RAW / f"hist_{rnd}.jsonl"
    done = {json.loads(l)["keyword"] for l in hp.open(encoding="utf-8")} if hp.exists() else set()
    todo = [s for s in seeds if s["seed"] not in done]
    meta = {s["seed"]: s for s in seeds}
    for i in range(0, len(todo), 200):
        chunk = todo[i:i + 200]
        res = planner.get_historical_metrics(customer_id=customer, keywords=[s["seed"] for s in chunk], **opts)
        with hp.open("a", encoding="utf-8") as f:
            got = set()
            for rec in res["records"]:
                k = " ".join(rec.original_keyword.split()); got.add(k)
                m = meta.get(k, {})
                f.write(json.dumps(dict(keyword=k, origin=m.get("origin", ""), source=m.get("source", ""),
                                        metrics_found=rec.metrics_found, metrics=mdict(rec.google_metrics),
                                        region=REGION, surveyed_at=TODAY), ensure_ascii=False) + "\n")
            # KWPが行を返さなかったseedも「NO DATA」として残す
            for s in chunk:
                if s["seed"] not in got:
                    f.write(json.dumps(dict(keyword=s["seed"], origin=s["origin"], source=s["source"], metrics_found=False,
                                            metrics={}, region=REGION, surveyed_at=TODAY, note="KWPが行を返さなかった"),
                                       ensure_ascii=False) + "\n")
        log(rnd, "hist", f"{len(chunk)}語", len(res["records"]), None)
        print(f"[{rnd}] hist {res['stats'].metrics_found_count}/{len(chunk)} 語に数値", flush=True)

    # ---- Keyword Ideas（seed 1語ずつ）----
    ip = RAW / f"ideas_{rnd}.jsonl"
    done = set()
    if ip.exists():
        done = {json.loads(l)["seed"] for l in ip.open(encoding="utf-8") if not json.loads(l).get("error")}
    todo = [s for s in seeds if s["seed"] not in done]
    print(f"[{rnd}] ideas 残り {len(todo)} / {len(seeds)}", flush=True)
    with ip.open("a", encoding="utf-8") as f:
        for n, s in enumerate(todo, 1):
            try:
                out = planner.generate_keyword_ideas(customer_id=customer, seed_keywords=[s["seed"]], limit=0, **opts)
                recs = [dict(keyword=" ".join(r.original_keyword.split()), metrics=mdict(r.google_metrics)) for r in out["records"]]
                total, err = out.get("total_size"), None
            except Exception as exc:
                recs, total, err = [], None, f"{type(exc).__name__}: {str(exc)[:200]}"
                if "429" in err or "Exhausted" in err or "RESOURCE_EXHAUSTED" in err:
                    time.sleep(30)
            log(rnd, "ideas", s["seed"], len(recs), total, err)
            f.write(json.dumps(dict(**s, round=rnd, error=err, total_size=total, record_count=len(recs),
                                    region=REGION, surveyed_at=TODAY, records=recs), ensure_ascii=False) + "\n")
            f.flush()
            if n % 10 == 0:
                print(f"[{rnd}] ideas {n}/{len(todo)}", flush=True)
            time.sleep(1.5)
    print(f"[{rnd}] 完了", flush=True)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
