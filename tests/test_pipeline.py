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


class TestTreehole(unittest.TestCase):
    """情绪树洞：共情回应 + 隐形画像 + 隐私隔离。测试环境无 LLM key → 走规则降级。"""

    def setUp(self):
        from services import pipeline as P
        P.treehole_clear()

    def test_rule_reply_and_persist(self):
        """无 LLM：规则共情回应，user/assistant 两条落库。"""
        from services import pipeline as P
        out = P.treehole_post("王组长今天又给我甩了个烂活，气得想摔键盘。", use_llm=True)
        self.assertTrue(out["reply"])
        self.assertEqual(out["mode"], "rule")
        self.assertFalse(out["absorbed"])  # 无 LLM 时不吸收画像
        msgs = P.treehole_list()
        self.assertEqual(len(msgs), 2)
        self.assertEqual([m["role"] for m in msgs], ["user", "assistant"])
        self.assertIn("摔键盘", msgs[0]["content"])

    def test_clear_isolated(self):
        """清空树洞只删树洞，不触碰台账/人物/画像事实。"""
        import sqlite3
        from services import pipeline as P
        P.treehole_post("又被甩锅了。", use_llm=False)
        n_reqs = P.list_requirements().__len__()
        n_persons = len(P.persons_view())
        n = P.treehole_clear()
        self.assertGreater(n, 0)
        self.assertEqual(P.treehole_list(), [])
        self.assertEqual(len(P.list_requirements()), n_reqs)
        self.assertEqual(len(P.persons_view()), n_persons)
        con = sqlite3.connect(str(P.DB))
        try:
            self.assertEqual(con.execute(
                "SELECT COUNT(*) FROM treehole_message").fetchone()[0], 0)
        finally:
            con.close()

    def test_export_excludes_treehole(self):
        """隐私隔离：业务导出不混入树洞倾诉内容。"""
        from services import pipeline as P
        P.treehole_post("树洞里的私密吐槽。", use_llm=False)
        data = P.export_all()
        self.assertNotIn("treehole_message", data)
        self.assertIn("person", data)
        P.treehole_clear()

    def test_profile_invisible_in_view(self):
        """隐形画像：吸收后不出现在 persons_view，但能从库中读到。"""
        import json
        import sqlite3
        from unittest import mock
        from services import pipeline as P
        fake = {"person_name": "王组长",
                "facts": ["两次在演示会前一天临时加需求", "上次被拒后自己收回了"],
                "advice": "提前一周对齐排期"}
        with mock.patch("services.llm.extract_profile", return_value=fake):
            self.assertTrue(P._absorb_profile("王组长又临时加活，上次被拒后他自己收回了。"))
        # 界面视图不带 auto_profile
        for d in P.persons_view():
            self.assertNotIn("auto_profile", d)
        # 库中已写入结构化事实
        con = sqlite3.connect(str(P.DB))
        try:
            raw = con.execute(
                "SELECT auto_profile FROM person WHERE name='王组长'").fetchone()[0]
            pid = con.execute(
                "SELECT id FROM person WHERE name='王组长'").fetchone()[0]
        finally:
            con.close()
        prof = json.loads(raw)
        self.assertIn("两次在演示会前一天临时加需求", prof["facts"])
        # 后台画像事实可被读取
        self.assertIn("两次在演示会前一天临时加需求", P._profile_facts_of(pid))

    def test_absorb_ignores_emotional_noise(self):
        """情绪化内容不落库：没有具体人物或没有可核实事实时不写入。"""
        from unittest import mock
        from services import pipeline as P
        with mock.patch("services.llm.extract_profile",
                        return_value={"person_name": "", "facts": [], "advice": ""}):
            self.assertFalse(P._absorb_profile("今天真的好累，什么都不想干。"))
        with mock.patch("services.llm.extract_profile",
                        return_value={"person_name": "张总", "facts": [], "advice": ""}):
            self.assertFalse(P._absorb_profile("张总总是这样！烦死了！"))  # 只有情绪没有事实


if __name__ == "__main__":
    unittest.main()
