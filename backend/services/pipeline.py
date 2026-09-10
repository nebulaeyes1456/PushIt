# -*- coding: utf-8 -*-
"""PushIt · 端到端编排（M1 mock 链路，无 LLM）：

requirement_id -> 需求(人/项目) -> 动机与"该接就接"判定 -> 估算(A 线)
               -> 策略/话术/双质检(C 线) -> 报告
纯本地 SQLite 读取；commit_result 可把交锋结论写回 change_log（拒绝债监测）。

运行前提：data/pushit.db 已由 scripts/seed_mock.py 生成（幂等）。
"""
import os
import secrets
import sqlite3
from pathlib import Path

from services.estimate.engine import estimate
from services.script.engine import finalize

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("PUSHIT_DATA_DIR") or (ROOT / "data"))
DB = DATA_DIR / "pushit.db"

MOTIVATION_LABEL = {
    "boss_press": "大老板拍板 / 中层转压",
    "self_achievement": "中层要业绩 / 拍脑袋",
    "relay": "帮同事 / 别组转达",
    "other": "其他",
}
ROLE_LABEL = {"boss": "大老板", "mid": "中层", "peer": "平级", "other": "其他"}
KICK_HINTS = ("很快", "顺便", "临时", "简单", "小事", "顺手")
SOURCE_MAP = {"口头": "oral", "消息": "message", "会议": "meeting", "1:1": "oneone"}


def _con():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def process(requirement_id, use_llm=False):
    con = _con()
    try:
        row = con.execute(
            "SELECT r.*, p.name AS person_name, p.role AS person_role, p.comm_style, "
            "p.speech_style, pj.name AS project_name "
            "FROM requirement r JOIN person p ON p.id = r.person_id "
            "JOIN project pj ON pj.id = r.project_id WHERE r.id = ?",
            (requirement_id,)).fetchone()
        if row is None:
            raise KeyError("requirement not found: " + requirement_id)
        baselines = [dict(b) for b in con.execute(
            "SELECT * FROM baseline_item WHERE project_id = ?", (row["project_id"],)).fetchall()]
        person_count = con.execute(
            "SELECT COUNT(*) FROM requirement WHERE person_id=? AND id != ?",
            (row["person_id"], requirement_id)).fetchone()[0] + 1
    finally:
        con.close()

    est = estimate(dict(row), baselines)
    # 动机推断：明确动机优先；'other' 时按提出人角色推断（mid→要业绩 / peer→转达 / boss→老板转压）
    motivation_eff = row["motivation"]
    if motivation_eff == "other":
        motivation_eff = {"mid": "self_achievement", "peer": "relay",
                          "boss": "boss_press"}.get(row["person_role"], "other")
    kick_ball = (motivation_eff == "relay"
                 and any(k in row["raw_text"] for k in KICK_HINTS))
    scr = finalize(dict(row), motivation_eff, row["should_accept"],
                   row["comm_style"] or "low", kick_ball=kick_ball)
    if use_llm:
        from services import llm
        # 差异化上下文：负载 + 关系记忆（免费话术给不了的输入）
        context = {"weekly_committed": 32, "remaining": 8,
                   "person_week_count": person_count}
        enh = llm.enhance_script(dict(row), scr, row["speech_style"] or "unknown", context)
        if enh and enh.get("text"):
            scr = dict(scr)
            scr["text"] = enh["text"]
            scr["conclusion"] = enh.get("conclusion", scr["conclusion"])
            brief = scr["conclusion"].replace("结论：", "")
            scr["recall_test"] = "3 秒复述自检：对方能否复述出「" + brief + "」？能 → 明确性通过。"
            scr["mode"] = "llm"
    scr.setdefault("mode", "rule")
    verdict = ("该接（按“漂亮地接”走）" if row["should_accept"]
               else "该拒 / 需对齐（走拒绝或重谈）")
    return {
        "requirement_id": requirement_id,
        "requirement": row["raw_text"],
        "project": row["project_name"],
        "person": {"name": row["person_name"],
                   "role": ROLE_LABEL.get(row["person_role"], row["person_role"])},
        "motivation": {"id": motivation_eff,
                       "label": MOTIVATION_LABEL.get(motivation_eff, motivation_eff)},
        "should_accept": row["should_accept"],
        "kick_ball": kick_ball,
        "speech_style": row["speech_style"] or "unknown",
        "verdict": verdict,
        "estimate": est,
        "strategy": scr,
    }


def commit_result(requirement_id, result="decline", handed_to=None, warded_hours=None):
    """把交锋结论写回 change_log（幂等：同一 requirement+result 不重复插入）。"""
    con = _con()
    try:
        dup = con.execute("SELECT 1 FROM change_log WHERE requirement_id=? AND result=?",
                          (requirement_id, result)).fetchone()
        if dup:
            return {"committed": False, "reason": "already_exists"}
        person_id = con.execute("SELECT person_id FROM requirement WHERE id=?",
                                (requirement_id,)).fetchone()[0]
        wh = float(warded_hours) if warded_hours is not None else 0.0
        con.execute(
            "INSERT INTO change_log(id,requirement_id,person_id,happened_at,content,impact,result,"
            "handed_to_person_id,warded_hours) VALUES(?,?,?,?,?,?,?,?,?)",
            ("c_" + requirement_id + "_" + result, requirement_id, person_id,
             "2026-09-09 20:00:00", "M1 mock 交锋结果", "mock", result, handed_to, wh))
        con.commit()
        return {"committed": True}
    finally:
        con.close()


def create_requirement(data):
    """新建台账：{text, person_id, project_id, source} -> id；并用 A 线估算写入 estimate_item。"""
    con = _con()
    try:
        rid = "r_" + secrets.token_hex(4)
        person_id = data.get("person_id") or "pmid"
        project_id = data.get("project_id") or "pmain"
        source = SOURCE_MAP.get(data.get("source") or "", data.get("source") or "message")
        con.execute(
            "INSERT INTO requirement(id,project_id,person_id,raw_text,source,motivation,"
            "should_accept,status) VALUES(?,?,?,?,?,?,0,'pending')",
            (rid, project_id, person_id, data.get("text", ""),
             source, data.get("motivation") or "other"))
        est = estimate({"raw_text": data.get("text", "")}, [])
        for it in est["items"]:
            con.execute(
                "INSERT INTO estimate_item(id,requirement_id,subtask,hours_low,hours_high,"
                "dependencies,risk_note,assumptions) VALUES(?,?,?,?,?,?,?,?)",
                ("e_" + secrets.token_hex(4), rid, it["subtask"], it["hours_low"],
                 it["hours_high"], it["dependencies"], it["risk_note"], it["assumptions"]))
        con.commit()
        return rid
    finally:
        con.close()


def list_requirements():
    con = _con()
    try:
        return [dict(r) for r in con.execute(
            "SELECT * FROM requirement ORDER BY created_at DESC, rowid DESC").fetchall()]
    finally:
        con.close()


def load_view():
    """承诺 vs 新增（口径与前端 mock 一致：本周已排 32h、周容量 40h）。"""
    con = _con()
    try:
        row = con.execute(
            "SELECT COALESCE(SUM(e.hours_low),0) AS lo, COALESCE(SUM(e.hours_high),0) AS hi "
            "FROM estimate_item e JOIN requirement r ON r.id = e.requirement_id "
            "WHERE r.status IN ('pending','accepted','aligned')").fetchone()
        committed, cap = 32.0, 40.0
        new_low, new_high = round(row["lo"], 1), round(row["hi"], 1)
        return {"committed": committed, "cap": cap,
                "new_low": new_low, "new_high": new_high,
                "overload": committed + new_high > cap}
    finally:
        con.close()


def persons_view():
    """提出人画像：基础字段 + 行为日志计数（F 线数据源）。"""
    con = _con()
    try:
        out = []
        for p in con.execute("SELECT * FROM person ORDER BY rowid").fetchall():
            d = dict(p)
            counts = {}
            for kind in ("kick_ball", "deflect", "reliable", "commit_kept", "hostile"):
                n = con.execute(
                    "SELECT COUNT(*) FROM person_behavior WHERE person_id=? AND kind=?",
                    (p["id"], kind)).fetchone()[0]
                if n:
                    counts[kind] = n
            d["behavior_counts"] = counts
            out.append(d)
        return out
    finally:
        con.close()


def create_person(data):
    """新建提出人（画像同源）：{name, role} -> id；role 中文映射英文枚举。"""
    role_map = {"大老板": "boss", "中层": "mid", "平级": "peer", "其他": "other"}
    con = _con()
    try:
        pid = "p_" + secrets.token_hex(4)
        con.execute(
            "INSERT INTO person(id,name,role,comm_style,speech_style) VALUES(?,?,?,?,?)",
            (pid, data.get("name", ""), role_map.get(data.get("role"), "other"),
             "low", "unknown"))
        con.commit()
        return pid
    finally:
        con.close()


def changelog_list(requirement_id=None):
    """变更流水账（证据链），可按需求过滤。"""
    con = _con()
    try:
        q = "SELECT c.*, p.name AS person_name FROM change_log c " \
            "LEFT JOIN person p ON p.id = c.person_id"
        args = ()
        if requirement_id:
            q += " WHERE c.requirement_id = ?"
            args = (requirement_id,)
        return [dict(r) for r in con.execute(q + " ORDER BY c.rowid DESC", args).fetchall()]
    finally:
        con.close()


def export_all():
    """全量导出（数据主权 §15.2）。"""
    con = _con()
    try:
        out = {}
        for t in ("project", "person", "requirement", "estimate_item",
                  "baseline_item", "change_log", "encounter", "person_behavior"):
            out[t] = [dict(r) for r in con.execute("SELECT * FROM " + t).fetchall()]
        return out
    finally:
        con.close()


def alignment_text_rules():
    """对齐记录（规则拼装）：把待对齐条目生成一段可发出去的文字。"""
    con = _con()
    try:
        rows = con.execute(
            "SELECT r.raw_text, r.status, p.name FROM requirement r "
            "JOIN person p ON p.id = r.person_id "
            "WHERE r.status IN ('pending','aligned') ORDER BY r.created_at").fetchall()
    finally:
        con.close()
    if not rows:
        return "当前没有待对齐的加活。"
    lines = ["本周对齐记录（PushIt 生成）", ""]
    for i, r in enumerate(rows, 1):
        st = "待对齐" if r["status"] == "pending" else "已对齐待确认"
        lines.append("{0}. {1}（提出：{2}）—— 状态：{3}".format(i, r["raw_text"], r["name"], st))
    lines.append("")
    lines.append("以上均未计入本周承诺；请确认优先级后再排期。")
    return "\n".join(lines)


def rehearse_rules(person_name, role, your_line):
    """预演规则模板（无 LLM 时）：给一个带压力的通用回应。"""
    return {"reply": "（对方，{0}·规则模式）我听到了。那你先说说，这周你手里哪些能挪？".format(person_name)}


def weekly_summary_rules():
    """周报/1:1 素材（规则拼装），供 LLM 润色。"""
    con = _con()
    try:
        total = con.execute("SELECT COUNT(*) FROM requirement").fetchone()[0]
        declined = con.execute("SELECT COUNT(*) FROM requirement WHERE status='declined'").fetchone()[0]
        pending = con.execute(
            "SELECT COUNT(*) FROM requirement WHERE status IN ('pending','aligned')").fetchone()[0]
        won = con.execute(
            "SELECT COALESCE(SUM(warded_hours),0) FROM change_log WHERE result='decline'").fetchone()[0]
    finally:
        con.close()
    lines = ["本周 PushIt 摘要（1:1 / 周报素材）", "",
             "· 台账共 {0} 条：已挡 {1}、待对齐 {2}".format(total, declined, pending),
             "· 累计赢回约 {0} 小时（净账口径，已扣转嫁负担）".format(round(won, 1)),
             "· 本周负载：已排 32h / 40h（见负载页）", "",
             "· 1:1 主动汇报模板：'本周对齐了 N 件加活，保住了演示会交付；有 2 件已书面留痕，"
             "待您确认优先级。'"]
    return "\n".join(lines)
