# -*- coding: utf-8 -*-
"""上位ページ本文から業界語（名詞の連なり）を抜き出す。

- 対象：SERPの上位N件（辞書・Q&A・行政は除く）
- 名詞（接頭・接尾を含む）が連続した部分を1語として取り、墓・供養まわりの語を含むものだけ残す
- 何ページに出たか（文書頻度）で並べる。採否は Claude が判断する（自動では決めない）
本文は raw/pages/ にテキストで保存（再取得しない）
"""
from __future__ import annotations
import hashlib, html, json, re, time, urllib.request
from collections import defaultdict
from pathlib import Path
from sudachipy import dictionary, tokenizer as _tk
import serp

HERE = Path(__file__).resolve().parent.parent
PAGES = HERE / "raw" / "pages"; PAGES.mkdir(parents=True, exist_ok=True)
_T = dictionary.Dictionary().create(); _M = _tk.Tokenizer.SplitMode.C
DOMAIN = re.compile(r"墓|霊園|葬|納骨|供養|遺骨|骨|区画|永代|合祀|合葬|承継|継承|跡継|後継|檀家|宗派|宗旨|宗教|寺院|回忌|安置|"
                    r"埋葬|埋蔵|使用料|管理費|管理料|生前|寿陵|墓苑|墓所|墓地|納骨堂|樹木|祭祀|改葬|分骨|位牌|骨壺|カロート|区画")
SKIP_DOM = re.compile(r"chiebukuro|weblio|kotobank|wikipedia|youtube|\.lg\.jp|metro\.tokyo|\.go\.jp")

def page_text(url: str) -> str:
    p = PAGES / (hashlib.md5(url.encode()).hexdigest()[:12] + ".txt")
    if p.exists():
        return p.read_text(encoding="utf-8")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": serp.UA, "Accept-Language": "ja"})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read(1_500_000).decode("utf-8", "ignore")
        raw = re.sub(r"<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
        raw = re.sub(r"<(header|footer|nav)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
        txt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw)))
    except Exception as e:
        txt = f"[ERROR] {type(e).__name__}: {e}"
    p.write_text(url + "\n" + txt, encoding="utf-8")
    time.sleep(1.0)
    return p.read_text(encoding="utf-8")

def compounds(text: str) -> set[str]:
    out, buf = set(), []
    for line in re.split(r"[。！？\n]", text[:60000]):
        if not line.strip():
            continue
        for m in _T.tokenize(line[:2000], _M):
            pos = m.part_of_speech()
            if pos[0] in ("名詞",) or pos[0] == "接頭辞" or (pos[0] == "接尾辞" and pos[1] == "名詞的"):
                buf.append(m.surface())
            else:
                if 2 <= len(buf) <= 5 or (len(buf) == 1 and len(buf[0]) >= 3):
                    w = "".join(buf)
                    if 3 <= len(w) <= 14 and DOMAIN.search(w) and not re.search(r"[0-9０-９a-zA-Z]{3,}|[、。・／/|:：%％円年月日]", w):
                        out.add(w)
                buf = []
        buf = []
    return out

def extract(queries: list[str], top=3) -> dict:
    df, where = defaultdict(int), defaultdict(set)
    for q in queries:
        r = serp.fetch(q)
        urls = [a["url"] for a in r.get("algos", []) if not SKIP_DOM.search(a["url"])][:top]
        for u in urls:
            t = page_text(u)
            if t.startswith("[ERROR]") or "\n[ERROR]" in t[:300]:
                continue
            for w in compounds(t):
                df[w] += 1; where[w].add(q)
    return {w: dict(pages=df[w], seeds=sorted(where[w])) for w in df}
