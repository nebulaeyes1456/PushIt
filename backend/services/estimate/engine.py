# -*- coding: utf-8 -*-
"""PushIt · A 线：代价估算引擎（规则版 mock，无 LLM）。

依据项目书 §8「防反噬口径」：
只给保守区间（低-高），不给点值；显式列出口径/前提假设；超载标红。
P1 再做"估 vs 实际"校准；本版为 M1 演示用启发式。
"""
import re

WEEK_CAPACITY = 40.0  # 每周可排工时（含已有承诺，简单模型）

# 关键词 -> 复杂度系数（启发式，仅供 mock 演示）
_SCALE = {
    "导出": 1.0, "报表": 1.0, "看板": 1.0, "页面": 1.2, "接口": 1.2,
    "权限": 1.5, "迁移": 2.0, "预演": 1.3, "排查": 1.3, "数据字典": 0.6,
    "梳理": 0.8, "复查": 1.0, "统计": 1.0, "复盘": 0.8,
}
_VERBS = ["导出", "生成", "接入", "上线", "统计", "整理", "修复", "预演", "复查", "排查", "搭", "写"]


def _scale_of(text):
    s = 1.0
    for kw, v in _SCALE.items():
        if kw in text:
            s = max(s, v)
    clauses = len(re.split(r"[，。、；和及,]", text))  # 并列越多范围越大
    s *= 0.8 + 0.2 * min(clauses, 4)
    return round(s, 2)


def estimate(requirement, baselines=None):
    text = requirement.get("raw_text", "") or ""
    s = _scale_of(text)
    low = round(2 * s, 1)
    high = round(low * 2.2, 1) if s >= 1.2 else round(low * 1.8, 1)
    items = [{
        "subtask": "{0}（按「{1}」拆解）".format(text[:18], _first_verb(text)),
        "hours_low": low,
        "hours_high": high,
        "dependencies": "依赖老模块口径对齐（默认前提）",
        "risk_note": "老模块耦合、返工风险偏高" if s >= 1.2 else "范围边界需先确认",
        "assumptions": "口径沿用现有方案；期间无新需求插入",
    }]
    committed = round(sum((b.get("base_hours") or 0) for b in (baselines or [])), 1)
    remaining = round(WEEK_CAPACITY - committed, 1)
    capacity = {
        "committed": committed, "cap": WEEK_CAPACITY, "remaining": remaining,
        "after_add_low": round(remaining - low, 1),
    }
    capacity["overload"] = capacity["after_add_low"] < 0
    return {"items": items, "total_low": low, "total_high": high,
            "scale": s, "capacity": capacity}


def _first_verb(text):
    for v in _VERBS:
        if v in text:
            return v
    return "实现"
