# -*- coding: utf-8 -*-
"""PushIt · LLM 分层 provider（M2，OpenAI 兼容协议；DeepSeek/Qwen/GLM 均可用）。

分层（§10.3 v1.1）：
  fast   层 —— 话术润色/估算格式化（轻、快、便宜）
  reason 层 —— 复杂关系分析/动机识别/画像更新（推理模型，逻辑推理）
未配置或调用失败 → 返回 None，上层自动降级规则引擎；脱敏由调用方负责。
环境变量：PUSHIT_API_BASE / PUSHIT_API_KEY / PUSHIT_MODEL_FAST / PUSHIT_MODEL_REASON
"""
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

_CONFIG_PATH = Path(os.environ.get("PUSHIT_DATA_DIR")
                    or (Path(__file__).resolve().parents[2] / "data")) / "llm_config.json"


def _load_file_config():
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


_CFG = _load_file_config()
BASE = (os.environ.get("PUSHIT_API_BASE")
        or _CFG.get("api_base") or "https://api.deepseek.com").rstrip("/")
KEY = os.environ.get("PUSHIT_API_KEY") or _CFG.get("api_key") or ""
MODEL_FAST = os.environ.get("PUSHIT_MODEL_FAST") or _CFG.get("model_fast") or "deepseek-chat"
MODEL_REASON = (os.environ.get("PUSHIT_MODEL_REASON")
                or _CFG.get("model_reason") or "deepseek-reasoner")
TIMEOUT = 30


def available():
    return bool(BASE and KEY)


def _chat(messages, model, max_tokens, temperature):
    body = json.dumps({"model": model, "messages": messages,
                       "max_tokens": max_tokens, "temperature": temperature},
                      ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        BASE + "/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + KEY})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def _json_from(content):
    text = content or ""
    m = re.search(r"```(?:json)?\s*\{.*\}\s*```", text, re.S)  # 剥离代码块
    if m:
        text = m.group(0).strip("`")
        text = text[text.find("{"):]
    s = text.find("{")
    e = text.rfind("}")
    if s < 0 or e < 0:
        return None
    try:
        return json.loads(text[s:e + 1])
    except Exception:
        return None


def fast_json(system, user, max_tokens=300, temperature=0.3):
    """快层：返回解析后的 JSON dict；不可用/失败返回 None（降级规则）。"""
    if not available():
        return None
    try:
        content = _chat([{"role": "system", "content": system},
                         {"role": "user", "content": user}],
                        MODEL_FAST, max_tokens, temperature)
        return _json_from(content)
    except (urllib.error.URLError, Exception):
        return None


def reason_json(system, user, max_tokens=800, temperature=0.2):
    """推理层：走推理模型（复杂关系分析/画像）。失败返回 None。"""
    if not available():
        return None
    try:
        content = _chat([{"role": "system", "content": system},
                         {"role": "user", "content": user}],
                        MODEL_REASON, max_tokens, temperature)
        return _json_from(content)
    except Exception:
        return None


# ---------------- 业务封装（调用方只认这些函数） ----------------

_SCRIPT_SYSTEM = (
    "你是职场向上管理助手。把给定需求与打法生成一段'三秒能念出口'的低损短句。"
    "要求：1) 只输出 JSON：{\"text\": \"话术\", \"conclusion\": \"明确结论\"}；"
    "2) 归因外置：拒绝的是方案/时间/风险，不拒绝人；"
    "3) 顺序铁律：先给明确结论（做/不做/何时做），再给理由与台阶；"
    "4) 语气克制、不阴阳、不用影视台词；5) text 控制在 60 字内。"
)


_TONE = {
    "formal": "对方爱听尊敬、正式的称呼与措辞，请用「您/请示/汇报」式语气",
    "plain": "对方觉得太客套很做作，用平实、直接、像同事商量的语气，少用敬语",
}


def enhance_script(requirement, strategy, speech_style="unknown"):
    """快层：生成/润色话术与结论。返回 dict 或 None（脱敏：不传人名）。"""
    user = ("需求原文：{0}\n已选打法：{1}\n对象沟通风格：{2}".format(
        requirement.get("raw_text", ""),
        strategy.get("tactic_name", ""),
        strategy.get("clarify_dial", "high")))
    tone = _TONE.get(speech_style)
    if tone:
        user += "\n对方语言风格偏好：" + tone
    return fast_json(_SCRIPT_SYSTEM, user, max_tokens=300)


_PROFILE_SYSTEM = (
    "你是职场关系分析师。基于行为事件列表推断该提出人的行为画像与应对建议。"
    "只输出 JSON：{\"summary\": \"一段画像\", \"tendency\": \"kick_ball|reliable|mixed\","
    " \"advice\": \"下次面对此人请求时的应对要点\"}。仅基于给定事件，不臆造。"
)


def build_profile(person_name, role, events):
    """推理层：由行为日志生成画像；失败返回 None（规则降级由调用方做）。"""
    lines = ["称呼：" + person_name, "角色：" + role]
    lines += ["事件：" + e for e in events]
    return reason_json(_PROFILE_SYSTEM, "\n".join(lines), max_tokens=500)


_ALIGN_SYSTEM = (
    "你是职场助理。把给定草稿润色成简洁、克制、专业的「对齐记录」，保持编号结构，"
    "不添加新事实。只输出 JSON：{\"text\": \"...\"}。"
)


def polish_alignment(raw):
    """快层：润色对齐记录。失败返回 None。"""
    return fast_json(_ALIGN_SYSTEM, "草稿：\n" + raw, max_tokens=500)


_REHEARSE_SYSTEM = (
    "你在模拟对话中扮演一位职场领导/同事，为对方制造真实但克制的压力，逼他练沟通。"
    "只输出 JSON 对象，格式：{\"reply\":\"一句自然口语的回应\"}。不要输出 JSON 之外的任何内容。"
)


def rehearse_reply(person_name, role, your_line, history=""):
    """快层：扮演对方回应（预演）。失败返回 None。"""
    user = "对方是{0}（{1}）。下属说：{2}".format(person_name, role, your_line)
    if history:
        user += "\n此前对话：\n" + history
    return fast_json(_REHEARSE_SYSTEM, user, max_tokens=200)
