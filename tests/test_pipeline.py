# -*- coding: utf-8 -*-
"""PushIt · 端到端验收测试（M1 mock 链路）。

运行：python -m unittest discover -s tests
依赖：backend 与 scripts 加入 sys.path；data/pushit.db 由 seed_mock 保证存在（幂等）。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))


def setUpModule():
    import os
    os.environ["PUSHIT_DEMO"] = "1"  # 测试需要演示种子数据
    os.environ["PUSHIT_DATA_DIR"] = str(ROOT / "data" / "test_pushit.db")  # 测试库与正式库隔离
    import seed_mock
    seed_mock.main()  # 幂等：确保迁移与 mock 数据存在


class TestPipeline(unittest.TestCase):
    def test_r001_decline_flow(self):
        """r001（该拒：报表导出权限，中层要业绩）→ 拒绝链路 + 双质检通过。"""
        from services import pipeline as P
        rep = P.process("r001")
        self.assertIn("该拒", rep["verdict"])
        self.assertEqual(rep["motivation"]["id"], "self_achievement")
        # 估算：保守区间存在且 low<=high
        est = rep["estimate"]
        self.assertGreater(est["total_low"], 0)
        self.assertLessEqual(est["total_low"], est["total_high"])
        self.assertIn("capacity", est)
        # 话术：默认安全版 + 明确结论 + 复述自检通过
        s = rep["strategy"]
        self.assertTrue(s["safe_version"])
        self.assertTrue(s["redline_report"]["passed"])
        self.assertTrue(s["conclusion"].startswith("结论："))
        self.assertIn("复述", s["recall_test"])
        self.assertEqual(s["tactic_id"], "two_options")

    def test_r002_should_accept(self):
        """r002（该接：核心迁移预演，老板亲抓）→ 走 accept_pretty。"""
        from services import pipeline as P
        rep = P.process("r002")
        self.assertEqual(rep["should_accept"], 1)
        self.assertIn("该接", rep["verdict"])
        self.assertEqual(rep["strategy"]["tactic_id"], "accept_pretty")

    def test_relay_kick_ball(self):
        """r003（平级转达，含「很快/临时」）→ 皮球判定 → ball_return 应对。"""
        from services import pipeline as P
        rep = P.process("r003")
        self.assertEqual(rep["motivation"]["id"], "relay")
        self.assertTrue(rep["kick_ball"])
        self.assertEqual(rep["strategy"]["tactic_id"], "ball_return")
        self.assertIn("球", rep["strategy"]["tactic_name"])

    def test_commit_idempotent(self):
        """交锋结果写回 change_log 幂等（用无既有记录的 r003）。"""
        import sqlite3
        from services import pipeline as P
        con = sqlite3.connect(str(P.DB))
        con.execute("DELETE FROM change_log WHERE id='c_r003_decline'")
        con.commit()
        con.close()
        self.assertTrue(P.commit_result("r003", "decline", warded_hours=4)["committed"])
        self.assertFalse(P.commit_result("r003", "decline", warded_hours=4)["committed"])


if __name__ == "__main__":
    unittest.main()
