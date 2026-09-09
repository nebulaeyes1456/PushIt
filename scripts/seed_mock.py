# -*- coding: utf-8 -*-
"""PushIt mock 种子（幂等）：执行迁移 + 首次空库注入示例数据。
用法：python scripts/seed_mock.py
产出：data/pushit.db（迁移 + 种子）；重跑安全（仅当 requirement 为空时注入）。
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("PUSHIT_DATA_DIR") or (ROOT / "data"))
DB = DATA_DIR / "pushit.db"
MIG_DIR = ROOT / "backend" / "schema" / "migrations"

try:
    sys.stdout.reconfigure(encoding="utf-8")  # 避免 GBK 控制台打印中文报错
except Exception:
    pass


def now():
    return "2026-09-09 12:00:00"


def seed(con):
    cur = con.cursor()
    if cur.execute("SELECT COUNT(*) FROM requirement").fetchone()[0] > 0:
        print("[skip] requirement 已有数据，跳过注入（幂等）")
        return

    P = "INSERT INTO project(id,name,is_mainline,period_commit,created_at) VALUES(?,?,?,?,?)"
    cur.executemany(P, [
        ("pmain", "数据平台迁移", 1, "Q3 承诺：核心迁移 + 双写校验", now()),
        ("pside", "经营看板", 0, "Q3 承诺：看板一期只读", now()),
    ])

    PE = "INSERT INTO person(id,name,role,comm_style,memo,reaction_pattern,risk_flags) VALUES(?,?,?,?,?,?,?)"
    cur.executemany(PE, [
        ("pboss", "赵总", "boss", "high", "大老板，看季度结果", "", json.dumps([], ensure_ascii=False)),
        ("pmid", "王组长", "mid", "high", "重面子，怕项目出事", "上次暗示后自己收回了", json.dumps([], ensure_ascii=False)),
        ("ppeer", "小李", "peer", "low", "平级，常帮别组转达", "", json.dumps([], ensure_ascii=False)),
    ])

    R = ("INSERT INTO requirement(id,project_id,person_id,raw_text,source,motivation,"
         "should_accept,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)")
    cur.executemany(R, [
        ("r001", "pmain", "pmid", "顺手把报表导出权限也开了，这周一起上", "oral", "self_achievement", 0, "declined", now()),
        ("r002", "pmain", "pboss", "核心迁移预演排进本周，演示会给上面看", "meeting", "boss_press", 1, "accepted", now()),
        ("r003", "pside", "ppeer", "帮市场部临时拉个经营看板，很快", "message", "relay", 0, "pending", now()),
        ("r004", "pmain", "pmid", "数据质量复查这周做掉吧", "oral", "self_achievement", 0, "deferred", now()),
        ("r005", "pside", "pmid", "临时整理一份数据字典给新同事", "oral", "self_achievement", 0, "declined", now()),
    ])

    # r001 的估算（只给保守区间 + 口径假设，§8）
    E = ("INSERT INTO estimate_item(id,requirement_id,subtask,hours_low,hours_high,dependencies,"
         "risk_note,assumptions) VALUES(?,?,?,?,?,?,?,?)")
    cur.executemany(E, [
        ("e001", "r001", "权限模型梳理", 4, 8, "依赖老模块文档", "老模块耦合，返工风险偏高", "前提：权限口径沿用现方案"),
        ("e002", "r001", "导出链路改造", 6, 12, "待权限模型定", "演示会冲突", "前提：本周无新需求插入"),
        ("e003", "r001", "回归验证", 2, 4, "前两项完成", "", "前提：测试环境可用"),
    ])

    B = ("INSERT INTO baseline_item(id,project_id,period,item,base_hours,aligned_at) VALUES(?,?,?,?,?,?)")
    cur.executemany(B, [
        ("b001", "pmain", "Q3", "核心迁移", 60, "2026-09-01"),
        ("b002", "pmain", "Q3", "双写校验", 30, "2026-09-01"),
        ("b003", "pside", "Q3", "看板一期只读", 40, "2026-09-01"),
    ])

    C = ("INSERT INTO change_log(id,requirement_id,person_id,happened_at,content,impact,result,"
         "handed_to_person_id,warded_hours) VALUES(?,?,?,?,?,?,?,?,?)")
    cur.executemany(C, [
        ("c001", "r001", "pmid", now(), "口头加活：报表导出权限", "超出 Q3 承诺", "decline", None, 6),
        ("c002", "r002", "pboss", now(), "核心预演排期", "主线内调整", "accept", None, 0),
        ("c003", "r004", "pmid", now(), "数据质量复查", "待排期会", "park", None, 0),
        ("c004", "r005", "pmid", now(), "临时数据字典", "被挡后转派小李", "decline", "ppeer", 4),
    ])

    EN = ("INSERT INTO encounter(id,change_id,script_version,other_reaction,outcome,review_note) "
          "VALUES(?,?,?,?,?,?)")
    cur.executemany(EN, [
        ("n001", "c001", "safe_v0.1", "王组长沉默后说：那先排期会再说", "对方收回", "归因外置生效，建议记入预案本"),
        ("n002", "c004", "safe_v0.1", "活转给小李，小李不知情", "转派", "未附避坑交接，触发拒绝债提醒"),
    ])

    con.commit()
    print("[seed] 注入完成：projects=2 persons=3 requirements=5 estimates=3 baseline=3 changelog=4 encounters=2")


def seed_behavior(con):
    cur = con.cursor()
    if cur.execute("SELECT COUNT(*) FROM person_behavior").fetchone()[0] > 0:
        print("[skip] person_behavior 已有数据，跳过注入（幂等）")
        return
    cur.executemany(
        "INSERT INTO person_behavior(id,person_id,kind,evidence) VALUES(?,?,?,?)",
        [
            ("pb001", "ppeer", "kick_ball", "转达市场部看板：无范围、无数据、一句「很快」（今天 09:10）"),
            ("pb002", "pmid", "commit_kept", "上次延期任务按新排期按时交付"),
            ("pb003", "ppeer", "kick_ball", "历史：多次以「顺手/很快」转达别组需求"),
        ])
    con.commit()
    print("[seed] person_behavior 注入完成（3 条）")
    # 语言风格偏好种子（迁移 003；幂等 UPDATE）
    con.execute("UPDATE person SET speech_style='formal' WHERE id='pboss'")
    con.execute("UPDATE person SET speech_style='plain' WHERE id='pmid'")
    con.execute("UPDATE person SET speech_style='plain' WHERE id='ppeer'")
    con.commit()


def migrate(con):
    """按 PRAGMA user_version 版本门执行迁移（幂等、可升级）。"""
    v = con.execute("PRAGMA user_version").fetchone()[0]
    for mig in sorted(MIG_DIR.glob("*.sql")):
        idx = int(mig.name.split("_")[0])
        if idx <= v:
            continue
        con.executescript(mig.read_text(encoding="utf-8"))
        con.execute("PRAGMA user_version = %d" % idx)
        con.commit()
        print("[migrate] " + mig.name + " 执行 OK (user_version -> " + str(idx) + ")")


def main():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    try:
        migrate(con)
        seed(con)
        seed_behavior(con)
        # 自检统计
        for t in ("project", "person", "requirement", "estimate_item", "baseline_item", "change_log", "encounter", "person_behavior"):
            n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  [check] {t}: {n}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
