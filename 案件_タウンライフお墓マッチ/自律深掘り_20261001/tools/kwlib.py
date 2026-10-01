# -*- coding: utf-8 -*-
"""KWの照合キーと既存母集団の読み込み（この調査の全スクリプトで共通）。

照合は3段階：
  compact  … 空白を詰めて小文字化（KWPの「お 墓 見積もり」と「お墓見積もり」を同じにする）
  variant  … 表記ゆれ（助詞・語順・「お」・「いない/ない/なし」の違い）を吸収。既存照合に使う
  group    … さらに同義語をそろえる（跡取り→跡継ぎ、承継者→跡継ぎ、管理料→管理費 など）。類似KWのまとめに使う
"""
from __future__ import annotations
import csv, io, re
from functools import lru_cache
from pathlib import Path
from sudachipy import dictionary, tokenizer as _tk

HERE = Path(__file__).resolve().parent.parent          # 自律深掘り_20261001/
CASE = HERE.parent                                     # 案件_タウンライフお墓マッチ/
_T = dictionary.Dictionary().create()
_M = _tk.Tokenizer.SplitMode.C

def compact(k: str) -> str:
    return "".join(str(k).lower().split()).replace("　", "")

DROP_POS = {"助詞", "補助記号", "空白"}
DROP_NORM = {"御", "居る", "有る", "為る"}
NEG = {"ない", "無い", "無し", "なし", "ありません", "ません", "いない"}

@lru_cache(maxsize=200000)
def tokens(k: str) -> tuple:
    out = []
    for m in _T.tokenize(compact(k), _M):
        pos, n = m.part_of_speech()[0], m.normalized_form()
        if pos in DROP_POS or n in DROP_NORM:
            continue
        if pos == "助動詞" and n not in NEG:
            continue
        out.append("なし" if n in NEG else n)
    return tuple(out)

def variant(k: str) -> str:
    return "|".join(sorted(tokens(k)))

SYN = {
    "跡取り": "跡継ぎ", "後継ぎ": "跡継ぎ", "継承": "承継", "後継": "承継", "後継者": "承継者", "継承者": "承継者",
    "管理料": "管理費", "維持費": "管理費", "年会費": "管理費", "年間管理費": "管理費",
    "不要": "なし", "要らない": "なし", "いらない": "なし", "無料": "なし",
    "料金": "費用", "値段": "費用", "価格": "費用", "相場": "費用", "金額": "費用",
    "墓地": "墓", "墓所": "墓", "お墓": "墓",
    "合祀": "合葬", "合同": "合葬",
    "購入": "買う", "買い": "買う",
    "一人": "ひとり", "独り": "ひとり", "お一人様": "おひとりさま", "おひとり様": "おひとりさま",
}

def group(k: str) -> str:
    t = [SYN.get(x, x) for x in tokens(k)]
    # 「承継者」「者」の揺れ：承継 者 → 承継者
    s = " ".join(t).replace("承継 者", "承継者").replace("跡継ぎ", "承継者")
    return "|".join(sorted(set(s.split())))

# ---------------- 既存の墓案件KW母集団 ----------------
SOURCES = [
    ("既存925", "追加調査_20260930/既存/①全候補KW一覧_925.csv", "keyword"),
    ("9/30追加調査", "追加調査_20260930/⑤追加候補統合版.csv", "keyword"),
    ("9/30追加調査（除外）", "追加調査_20260930/⑥除外候補.csv", "keyword"),
    ("10/01具体条件", "具体条件深掘り_20261001/⑤統合版.csv", "keyword"),
    ("10/01具体条件（除外）", "具体条件深掘り_20261001/④除外候補.csv", "keyword"),
    ("KWプール(out/final)", "out/final_keywords.csv", "keyword"),
    ("KWプール(out/pool)", "out/pool_records.csv", "Keyword"),
]

@lru_cache(maxsize=1)
def existing():
    """{'compact': {key: [sources]}, 'variant': {key: [(source, keyword)]}}"""
    by_c, by_v = {}, {}
    for label, rel, col in SOURCES:
        p = CASE / rel
        if not p.exists():
            continue
        with io.open(p, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                k = (row.get(col) or "").strip()
                if not k:
                    continue
                by_c.setdefault(compact(k), set()).add(label)
                by_v.setdefault(variant(k), set()).add((label, k))
    return by_c, by_v

def existing_status(k: str) -> tuple[str, str]:
    """('既存'|'既存（表記ゆれ）'|'新規', 根拠)"""
    by_c, by_v = existing()
    c = by_c.get(compact(k))
    if c:
        return "既存", " / ".join(sorted(c))
    v = by_v.get(variant(k))
    if v:
        ex = sorted(v)[:3]
        return "既存（表記ゆれ）", " / ".join(f"{s}:{w}" for s, w in ex)
    return "新規", ""
