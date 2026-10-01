# -*- coding: utf-8 -*-
"""SERP取得（Yahoo! JAPAN＝通常の検索結果はGoogleの検索エンジン）＋Googleサジェスト。

Googleを直接取得すると「通常と異なるトラフィック」の確認画面（/sorry）になるため、
同じGoogleの検索結果を返す Yahoo! JAPAN を観測面にする（関連する質問も GoogleWebAnswerShortcut）。
結果は raw/serp/<KW>.json に保存し、同じKWは再取得しない（再開可能）。
"""
from __future__ import annotations
import hashlib, html, json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
RAW = HERE / "raw" / "serp"
RAW.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
WAIT = 2.5

def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ja,en;q=0.5"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")

def strip(s): return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()

def _walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield path + "/" + k, k, v
            yield from _walk(v, path + "/" + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _walk(v, f"{path}[{i}]")

def parse_yahoo(page: str) -> dict:
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
    if not m:
        return {"error": "NEXT_DATAなし"}
    d = json.loads(m.group(1))
    pd = d.get("props", {}).get("pageProps", {}).get("initialProps", {}).get("pageData", {})
    algos = [dict(rank=a.get("index"), title=strip(a.get("title")), url=a.get("url"), snippet=strip(a.get("description")))
             for a in pd.get("algos", []) if a.get("type") == "Algo"]
    paa, related = [], []
    for path, k, v in _walk(pd):
        if k == "relatedQuestions" and isinstance(v, list):
            for q in v:
                r = q.get("result") or {}
                paa.append(dict(question=strip(q.get("query")), answer_title=strip(r.get("title")),
                                answer_url=r.get("url"), answer=strip(r.get("answer"))))
        elif "related" in k.lower() and k != "relatedQuestions" and isinstance(v, list):
            for x in v:
                if isinstance(x, dict):
                    t = strip(x.get("text") or x.get("query") or x.get("title") or "")
                    if t and t not in related:
                        related.append(t)
    # 関連検索ワード：JSONに無い場合はHTMLの見出し直後から拾う
    if not related:
        i = page.find("関連検索ワード")
        if i > 0:
            seg = page[i:i + 6000]
            for a in re.findall(r'<a[^>]+href="[^"]*search\?[^"]*p=([^"&]+)[^"]*"', seg):
                t = urllib.parse.unquote_plus(a)
                if t not in related:
                    related.append(t)
    return dict(algos=algos, paa=paa, related=related)

def suggest(q: str) -> list[str]:
    u = "https://suggestqueries.google.com/complete/search?client=firefox&hl=ja&gl=jp&q=" + urllib.parse.quote(q)
    try:
        return json.loads(_get(u))[1]
    except Exception as e:
        return [f"ERROR:{e}"]

def path_for(q: str) -> Path:
    safe = re.sub(r'[\\/:*?"<>|\s]+', "_", q)[:60]
    return RAW / f"{safe}_{hashlib.md5(q.encode()).hexdigest()[:6]}.json"

# ---- 上位ページの種類（自動の目安。最終判断は監査表で人＝Claudeが行う） ----
DICT_DOM = re.compile(r"weblio|kotobank|wikipedia|goo\.ne\.jp/word|jlogos|dictionary|kanjipedia")
QA_DOM = re.compile(r"chiebukuro|oshiete|okwave|komachi|quora|reddit")
GOV_DOM = re.compile(r"\.lg\.jp|metro\.tokyo|\.go\.jp|city\.|pref\.")
PORTAL_DOM = re.compile(r"e-ohaka|lifedot|haka|reien|ohaka|sekichu|ishiya|bosekisouba|jushouji|memorial|sougi|kamakura|ii-ohaka|hakaishi|bochi")
MEANING = re.compile(r"とは|意味|読み方|由来|歴史|語源")
MANNER = re.compile(r"マナー|服装|香典|持ち物|お布施|挨拶|書き方|のし|表書き")
COMPARE = re.compile(r"費用|相場|比較|おすすめ|選び方|ランキング|メリット|デメリット|違い|注意点|後悔|失敗|価格|料金|いくら")
FIND = re.compile(r"霊園|墓地|樹木葬|納骨堂|永代供養|区画|見学|資料請求|空き|募集|販売|申込|申し込み|墓苑|墓所")

def classify(a: dict) -> str:
    u, t = (a.get("url") or "").lower(), a.get("title") or ""
    if DICT_DOM.search(u): return "辞書・意味"
    if QA_DOM.search(u): return "Q&A"
    if GOV_DOM.search(u): return "行政"
    if MANNER.search(t): return "マナー・儀礼"
    if MEANING.search(t) and not COMPARE.search(t): return "意味解説"
    if COMPARE.search(t): return "比較・費用・選び方"
    if FIND.search(t): return "霊園・墓の紹介"
    return "その他"

def summarize(r: dict, top=10) -> dict:
    cats = [classify(a) for a in r.get("algos", [])[:top]]
    from collections import Counter
    c = Counter(cats)
    return dict(top3=" / ".join(f"{classify(a)}:{a['title'][:28]}" for a in r.get("algos", [])[:3]),
                composition=" ".join(f"{k}{v}" for k, v in c.most_common()),
                near=c["比較・費用・選び方"] + c["霊園・墓の紹介"], far=c["辞書・意味"] + c["意味解説"] + c["マナー・儀礼"])

def fetch(q: str, refresh=False) -> dict:
    p = path_for(q)
    if p.exists() and not refresh:
        return json.loads(p.read_text(encoding="utf-8"))
    url = "https://search.yahoo.co.jp/search?ei=UTF-8&p=" + urllib.parse.quote(q)
    try:
        r = parse_yahoo(_get(url))
    except Exception as e:
        r = {"error": f"{type(e).__name__}: {e}"}
    time.sleep(WAIT)
    r.update(query=q, engine="Yahoo! JAPAN（Google検索エンジン）", fetched_at=time.strftime("%Y-%m-%d %H:%M"),
             google_suggest=suggest(q))
    p.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    time.sleep(0.5)
    return r

if __name__ == "__main__":
    for q in sys.argv[1:]:
        r = fetch(q)
        s = summarize(r)
        print(q, "| 件数", len(r.get("algos", [])), "| PAA", len(r.get("paa", [])), "| 関連", len(r.get("related", [])),
              "| 構成", s["composition"])
        print("   関連:", r.get("related", [])[:8]); print("   PAA:", [x["question"] for x in r.get("paa", [])][:4])
        print("   サジェスト:", r.get("google_suggest", [])[:8])
