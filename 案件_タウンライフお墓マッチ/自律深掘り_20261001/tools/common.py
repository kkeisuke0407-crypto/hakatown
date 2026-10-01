# -*- coding: utf-8 -*-
"""KWP結果の読み込み・規制判定・地名判定・LP割り当て（下書き）の共通処理。"""
from __future__ import annotations
import csv, io, json, re, sys
from pathlib import Path
import kwlib

HERE = kwlib.HERE; CASE = kwlib.CASE; RAW = HERE / "raw"
sys.path.insert(0, str(CASE))
import rules_ohaka  # 案件の規制ルール（前回までと同じ基準）

GEO = re.compile(r"北海道|青森|岩手|宮城|仙台|秋田|山形|福島|茨城|栃木|群馬|埼玉|千葉|東京|都内|神奈川|横浜|川崎"
                 r"|新潟|富山|石川|福井|山梨|長野|岐阜|静岡|浜松|愛知|名古屋|三重|滋賀|京都|大阪|堺|兵庫|神戸"
                 r"|奈良|和歌山|鳥取|島根|岡山|広島|山口|徳島|香川|愛媛|高知|福岡|佐賀|長崎|熊本|大分|宮崎"
                 r"|鹿児島|沖縄|関東|関西|首都圏|都立|都営|府営|県営|.{1,4}市営|.{1,4}区|.{1,4}市(?!場)")
METHOD = {"hist": "HistoricalMetrics", "ideas": "KeywordIdeas"}

def regulation(k: str) -> tuple[str, str]:
    lvl, why = rules_ohaka.regulation(k)
    # 案件ルールの誤判定になりやすい語（型の名前）を注記する。判定値そのものは変えない
    n = kwlib.compact(k)
    if lvl == "HIGH" and re.search(r"仏壇型|仏壇式|位牌式|位牌型", n) and "納骨堂" in n:
        why += "｜注記：『仏壇型・位牌式』は納骨堂の型の名前。別市場ではない可能性が高い（要判断）"
    if lvl == "HIGH" and "ペット" in n and re.search(r"一緒|共葬|入れる", n):
        why += "｜注記：人とペットが一緒に入る霊園。SERPは霊園一覧で墓探しの意図（案件ルールの見直し要否を判断）"
    return lvl, why

def has_geo(k: str) -> bool:
    return bool(GEO.search(kwlib.compact(k)))

def rows_of(rnd: str) -> list[dict]:
    """周 rnd の KWP 結果を1行1レコードで返す（値は加工しない）。"""
    out = []
    hp, ip = RAW / f"hist_{rnd}.jsonl", RAW / f"ideas_{rnd}.jsonl"
    if hp.exists():
        for l in hp.open(encoding="utf-8"):
            j = json.loads(l); m = j.get("metrics") or {}
            out.append(dict(keyword=j["keyword"], seed=j["keyword"], round=rnd,
                            method=METHOD["hist"] + ("" if j.get("metrics_found") else "（NO DATA）"),
                            vol=m.get("avg_monthly_searches"), comp=m.get("competition"), comp_idx=m.get("competition_index"),
                            low=m.get("low_bid"), high=m.get("high_bid"), avg=m.get("average_cpc"),
                            region=j.get("region"), date=j.get("surveyed_at"), origin=j.get("origin", "")))
    if ip.exists():
        for l in ip.open(encoding="utf-8"):
            j = json.loads(l)
            if j.get("error"):
                out.append(dict(keyword="", seed=j["seed"], round=rnd, method=f"KeywordIdeas（エラー：{j['error']}）",
                                region=j.get("region"), date=j.get("surveyed_at"), origin=j.get("origin", "")))
                continue
            if not j.get("records"):
                out.append(dict(keyword="", seed=j["seed"], round=rnd, method="KeywordIdeas（0件＝この枝に検索需要なし）",
                                region=j.get("region"), date=j.get("surveyed_at"), origin=j.get("origin", "")))
            for r in j.get("records", []):
                m = r.get("metrics") or {}
                out.append(dict(keyword=r["keyword"], seed=j["seed"], round=rnd, method=METHOD["ideas"],
                                vol=m.get("avg_monthly_searches"), comp=m.get("competition"), comp_idx=m.get("competition_index"),
                                low=m.get("low_bid"), high=m.get("high_bid"), avg=m.get("average_cpc"),
                                region=j.get("region"), date=j.get("surveyed_at"), origin=j.get("origin", "")))
    return out

def rounds() -> list[str]:
    return sorted({p.stem.split("_", 1)[1] for p in RAW.glob("hist_*.jsonl")} | {p.stem.split("_", 1)[1] for p in RAW.glob("ideas_*.jsonl")})

# ---- LP割り当て（検索意図の規則による下書き。Claudeの判定で上書きする）----
LP_RULES = [
    ("墓いらない", r"いらない|要らない|持たない|墓なし|お墓なし"),
    ("墓地と霊園の違い", r"(墓地.*霊園|霊園.*墓地|民営.*公営|公営.*民営|寺院墓地).*(違い|比較|とは)"),
    ("近くの樹木葬", r"(近く|近所|駅近|家から近い).*樹木葬|樹木葬.*(近く|近所|駅近)"),
    ("近くの霊園", r"近く|近所|駅近|駅から近い|送迎|バリアフリー|アクセス"),
    ("墓種比較", r"違い|合祀.*個別|個別.*合祀|どっち|どちら|種類.*比較|比較.*種類"),
    ("樹木葬費用", r"樹木葬.*(費用|料金|値段|価格|相場|いくら|安い|期限|満期|何人|個別型|集合型|合祀型)"),
    ("納骨堂費用", r"納骨堂.*(費用|料金|値段|価格|相場|いくら|安い)"),
    ("永代供養費用", r"永代供養.*(費用|料金|値段|価格|相場|いくら|安い|一人|期間|安置)"),
    ("納骨堂", r"納骨堂|自動搬送|機械式|ロッカー|室内墓所|屋内墓|室内霊園|屋内納骨"),
    ("お墓比較", r"比較|相見積|見積|サイト|見学|一括"),
    ("お墓購入", r"購入|買う|買い|生前|寿陵|ローン|相続税|税金|次男|分家|四十九日|一周忌|短納期|建墓|間に合"),
    ("お墓費用", r"費用|料金|値段|価格|相場|いくら|維持費|管理費|管理料|使用料|墓地代|墓石セット|安い|内訳"),
    ("霊園探し", r"霊園|墓苑|墓地|空き区画|募集区画|新区画|落選|抽選|倍率|共葬"),
    ("墓地選び方", r"宗派|宗旨|檀家|無宗教|宗教|区画"),
    ("お墓の選び方", r"選び方|終活|迷惑|負担|一人|ひとり|おひとりさま|夫婦|承継|跡継|後継|祭祀|夫の墓|嫁|娘|家族墓|両家|二世帯|個人墓|合葬|合同墓|集合墓|レンタル墓|期限付"),
]
def lp_draft(k: str) -> str:
    n = kwlib.compact(k)
    for lp, pat in LP_RULES:
        if re.search(pat, n):
            return lp
    return "未割当"

def write_csv(path: Path, header: list[str], rows: list[list]):
    with io.open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
