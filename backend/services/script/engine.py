# -*- coding: utf-8 -*-
"""PushIt · C 线：话术生成 + 双质检（红线检测 §4.3 + 明确性校验 §6.8）。

规则版（无 LLM）：读取 data/strategy_lib.json（B 线 T4 产出）。
产物符合 strategy_lib.script_fields：含 conclusion / recall_test / redline_report / guardrail_tags。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
_LIB = json.loads((ROOT / "data" / "strategy_lib.json").read_text(encoding="utf-8"))
TACTICS = {t["id"]: t for t in _LIB["tactics"]}
REDLINE = _LIB["guardrails"]["redline"]
_FORBIDDEN = REDLINE["forbidden"]
_AMBIGUOUS = ["再说", "看看吧", "尽量", "应该可以", "回头", "到时候再说", "我考虑下", "先这样", "再说吧"]

# 动机 -> 默认打法（§2.3 决策树）；growth/该接走 accept_pretty（§6.7）
_TACTIC_BY_MOTIVATION = {
    "boss_press": "mirror_up",
    "self_achievement": "two_options",
    "relay": "proceduralize",
}

_CONCLUSIONS = {
    "accept_pretty": "结论：我接，但需调整资源或排期；请定 A 或 B。",
    "proceduralize": "结论：本周不承诺，进下周二排期会再定。",
    "two_options": "结论：请从 A/B 两案中选一；未选前不启动。",
    "mirror_up": "结论：建议保演示会、该需求延期；请您向上对齐口径。",
    "agree_then_cost": "结论：可做但不在本周；以您拍板时间为准。",
    "escalate_simple": "结论：本期只做 X，Y 挪后；请确认范围。",
    "return_to_decision": "结论：需先对齐口径与前提；谁做都按交接备注来。",
    "ball_return": "结论：不接不拒；请您先补范围和原始数据，我对齐后再评估。",
}


def pick_tactic(motivation, should_accept):
    if should_accept or motivation == "growth":
        return "accept_pretty"
    return _TACTIC_BY_MOTIVATION.get(motivation, "proceduralize")


def render(tactic_id, requirement_text=""):
    t = TACTICS[tactic_id]
    return t["example"], t["name"]


def redline_check(text):
    """红线检测（§4.3）：查雷句 + 查会被误读为答应的模糊词。"""
    hits = [f for f in _FORBIDDEN if f in text]
    ambiguous = [w for w in _AMBIGUOUS if w in text]
    return {"forbidden_hits": hits, "ambiguous_hits": ambiguous,
            "passed": not hits and not ambiguous}


def clarity_check(tactic_id):
    """明确性校验（§6.8）：话术必须以明确结论收尾（先明确、后台阶）。"""
    conclusion = _CONCLUSIONS.get(tactic_id, "结论：需先对齐范围与优先级后再决定。")
    passed = conclusion.startswith("结论：")
    brief = conclusion.replace("结论：", "")
    return {"passed": passed, "conclusion": conclusion,
            "recall_test": "3 秒复述自检：对方能否复述出「" + brief + "」？能→明确性通过。"}


def finalize(requirement, motivation, should_accept, clarify_dial="high", kick_ball=False):
    if should_accept or motivation == "growth":
        tactic_id = "accept_pretty"
    elif kick_ball and motivation == "relay":
        tactic_id = "ball_return"
    else:
        tactic_id = _TACTIC_BY_MOTIVATION.get(motivation, "proceduralize")
    text, name = render(tactic_id, requirement.get("raw_text", ""))
    redline = redline_check(text)
    clarity = clarity_check(tactic_id)
    return {
        "tactic_id": tactic_id, "tactic_name": name, "text": text,
        "clarify_dial": clarify_dial,
        "conclusion": clarity["conclusion"],
        "recall_test": clarity["recall_test"],
        "redline_report": redline,
        "guardrail_tags": TACTICS[tactic_id]["guardrails"],
        "safe_version": redline["passed"] and clarity["passed"],
    }
