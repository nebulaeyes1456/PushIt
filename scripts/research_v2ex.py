# -*- coding: utf-8 -*-
"""PushIt · 潜在用户发言调研脚本（V2EX 公开 API，无需登录）。

目的：抓取目标人群（程序员/知识工作者）关于"加活/排期/拒绝/背锅"的公开讨论，
按产品痛点矩阵分类统计，验证 §12 假设 1（真的有人需要"把账算清+低损拒绝"吗）。

合规：只用公开 API、请求限速、仅研究用途；不爬登录/付费内容。
用法：.venv\\Scripts\\python scripts\\research_v2ex.py
产出：data/research_v2ex.json（统计 + 样本），终端打印结论摘要。
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "data" / "research_v2ex.json"
NODES = ["career", "jobs"]  # 职场 / 招聘节点（种子人群：程序员社区）

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 痛点矩阵（对应项目书 §1 场景与 §6 护栏；中英双语关键词覆盖多源）
KEYWORDS = {
    "oral_add": ["临时", "顺手", "突然", "一句话", "又让我", "加活", "加了个活", "甩给我", "塞给我",
                 "one more thing", "ad-hoc", "spontaneous request", "dump work"],
    "scope_creep": ["需求变", "加需求", "排期不动", "改需求", "范围蔓延", "越做越多",
                    "scope creep", "new requirements", "requirement change", "growing scope"],
    "est_cut": ["工期", "排期", "几天做完", "砍工期", "压缩", "赶工",
                "deadline", "tight schedule", "estimate", "crunch"],
    "speak_hard": ["不好意思", "不敢", "怎么拒绝", "拒绝领导", "情商", "得罪", "开口",
                   "how to say no", "refuse", "push back", "say no to boss"],
    "fear": ["穿小鞋", "针对", "记仇", "背锅", "领导看法", "绩效", "被辞",
             "retaliation", "blame", "performance review", "pip"],
    "kick_ball": ["甩锅", "推诿", "踢皮球", "同事的活", "别人不做",
                  "pass the buck", "blame shifting"],
    "up_mgmt": ["向上管理", "manage up", "management up"],
    "pua": ["pua", "职场pua", "领导pua", "被pua"],
    "quit_signal": ["辞职", "裸辞", "想走", "跑路", "受不了",
                    "quit", "resign", "burnout"],
}
LABELS = {
    "oral_add": "① 口头加活（目标：代价账+当场/事后挡）",
    "scope_creep": "② 范围蔓延没人认账（目标：承诺基线+流水账）",
    "est_cut": "③ 估算被砍（目标：保守区间+防反噬口径）",
    "speak_hard": "④ 开不了口（目标：低损话术+明确性护栏）",
    "fear": "⑤ 怕穿小鞋/背锅（目标：留痕+该接就接+拒绝债）",
    "kick_ball": "⑥ 被踢皮球（目标：皮球判定器+把球送回去）",
    "up_mgmt": "⑧ 向上管理相关讨论（目标用户正在学的方法）",
    "pua": "⑨ 职场 PUA（痛感放大器，内容素材）",
    "quit_signal": "⑦ 忍到想辞职（最痛信号）",
}
UA = "Mozilla/5.0 (PushIt research; contact: repo owner)"


def classify(text):
    t = text.lower()
    return [k for k, words in KEYWORDS.items() if any(w.lower() in t for w in words)]


def _get(url, gzip_ok=True):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()
        if gzip_ok and resp.headers.get("Content-Encoding") == "gzip":
            import gzip
            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8"))


def api(path, params):
    url = "https://www.v2ex.com/api/" + path + "?" + urllib.parse.urlencode(params)
    return _get(url, gzip_ok=False)


def fetch_topics():
    topics = {}
    for node in NODES:
        try:
            rows = api("topics/show.json", {"node_name": node})
            for t in rows:
                if t.get("id") and t["id"] not in topics:
                    topics[t["id"]] = t
            time.sleep(0.8)
        except Exception as e:
            print("[warn] v2ex node %s: %s" % (node, e))
    return list(topics.values())


def fetch_hn():
    """Hacker News（Algolia 公开 API）：scope creep / refuse boss / overtime / toxic manager。"""
    out = {}
    for q in ["scope creep", "refuse boss", "overtime", "toxic manager"]:
        try:
            data = _get("https://hn.algolia.com/api/v1/search?query="
                        + urllib.parse.quote(q) + "&hitsPerPage=30&tags=story", gzip_ok=False)
            for h in data.get("hits", []):
                out[h["objectID"]] = {"id": h["objectID"], "title": h.get("title") or "",
                                      "url": "https://news.ycombinator.com/item?id=" + h["objectID"],
                                      "created": h.get("created_at_i"), "content": ""}
            time.sleep(0.6)
        except Exception as e:
            print("[warn] hn(%s): %s" % (q, e))
    return list(out.values())


def fetch_stackexchange():
    """The Workplace（Stack Exchange 公开 API，无需 key）：拒绝老板/范围蔓延/加班。"""
    out = {}
    for q in ["refuse boss", "scope creep", "unreasonable request", "overtime deadline"]:
        try:
            data = _get("https://api.stackexchange.com/2.3/search/advanced?site=workplace"
                        "&pagesize=30&order=desc&sort=activity&q=" + urllib.parse.quote(q))
            for it in data.get("items", []):
                out[it["question_id"]] = {"id": it["question_id"], "title": it.get("title") or "",
                                          "url": it.get("link", ""),
                                          "created": it.get("creation_date"),
                                          "content": ""}
            time.sleep(0.6)
        except Exception as e:
            print("[warn] stackexchange(%s): %s" % (q, e))
    return list(out.values())


def fetch_github_issues():
    """GitHub 公开搜索 API：中文讨论（需求蔓延/甩锅/加班）。"""
    out = {}
    for q in ["需求蔓延", "甩锅 加班", "拒绝 需求", "向上管理", "职场PUA"]:
        try:
            data = _get("https://api.github.com/search/issues?per_page=30&q="
                        + urllib.parse.quote(q), gzip_ok=False)
            for it in data.get("items", []):
                out[it["id"]] = {"id": it["id"], "title": it.get("title") or "",
                                 "url": it.get("html_url", ""),
                                 "created": it.get("created_at"),
                                 "content": (it.get("body") or "")[:300]}
            time.sleep(0.6)
        except Exception as e:
            print("[warn] github(%s): %s" % (q, e))
    return list(out.values())


def fetch_bing(queries):
    """搜索引擎标题级统计（公开结果页、低频、仅提取标题做研究统计，不抓正文）。"""
    out = {}
    for q in queries:
        try:
            url = "https://cn.bing.com/search?q=" + urllib.parse.quote(q) + "&count=20"
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", "ignore")
            titles = re.findall(r"<h2[^>]*>\s*<a[^>]*>(.*?)</a>", html, re.S)
            n = 0
            for t in titles:
                t = re.sub(r"<[^>]+>", "", t).strip()
                if len(t) > 6:
                    key = q + "#" + str(n)
                    out[key] = {"id": key, "title": t, "url": "", "created": None, "content": ""}
                    n += 1
            print("[ok] bing(%s): %d 条标题" % (q, n))
            time.sleep(1.5)
        except Exception as e:
            print("[warn] bing(%s): %s" % (q, e))
    return list(out.values())


def main():
    topics = (fetch_topics() + fetch_hn() + fetch_stackexchange() + fetch_github_issues()
              + fetch_bing([
                  "向上管理 吐槽", "职场PUA", "领导 临时加活 怎么办",
                  "需求蔓延 吐槽", "如何拒绝领导 加活", "被同事甩锅 怎么办"]))
    seen, uniq = set(), []
    for t in topics:
        if t["id"] not in seen:
            seen.add(t["id"])
            uniq.append(t)
    print("fetched topics(total/uniq):", len(topics), "/", len(uniq))
    rows = []
    for t in uniq:
        title = t.get("title") or ""
        content = re.sub(r"<[^>]+", "", t.get("content") or "")[:300]
        tags = classify(title + " " + content)
        if tags:
            rows.append({
                "id": t.get("id"), "title": title,
                "url": t.get("url", ""),
                "tags": tags, "labels": [LABELS[k] for k in tags],
                "created": t.get("created"),
            })
    cnt = Counter()
    for r in rows:
        cnt.update(r["tags"])

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(
        {"sources": ["v2ex", "hn.algolia", "stackexchange/workplace", "github/issues", "bing"],
         "fetched": len(uniq), "matched": len(rows), "counts": dict(cnt),
         "samples": rows},
        ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n===== 需求验证摘要 =====")
    print("有效主题 %d 条，命中痛点 %d 条（命中率 %d%%）" % (
        len(uniq), len(rows), round(100 * len(rows) / max(len(uniq), 1))))
    for k, n in cnt.most_common():
        print("  %-4d %s" % (n, LABELS[k]))
    print("\n样本（中文优先，前 10 条）：")
    zh_first = sorted(rows, key=lambda r: 0 if any(ord(c) > 127 for c in r["title"]) else 1)
    for r in zh_first[:10]:
        print("  -", r["title"][:52], "|", "/".join(r["tags"]))
    print("\nsaved ->", OUT_JSON)


if __name__ == "__main__":
    main()
