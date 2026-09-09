# -*- coding: utf-8 -*-
"""PushIt · LLM 分层验证：快层（deepseek-chat）+ 推理层（deepseek-reasoner）各试一次。

前置：data/llm_config.json 已填 api_key（或已设环境变量 PUSHIT_API_KEY）。
"""
import sys
import time

sys.path.insert(0, "backend")

from services import llm  # noqa: E402


def main():
    print("base :", llm.BASE)
    print("key  :", ("已配置（" + llm.KEY[:6] + "…）") if llm.KEY else "未配置（请填 data/llm_config.json 的 api_key）")
    if not llm.available():
        print("RESULT: FAIL（未配置 key）")
        return

    t0 = time.time()
    fast = llm.fast_json(
        "你是职场向上管理助手。只输出 JSON：{\"text\":\"一段低损短句\",\"conclusion\":\"明确结论\"}。",
        "需求：顺手把报表导出权限也开了，这周一起上。打法：给两个能接受的选项。",
        max_tokens=300)
    t_fast = time.time() - t0
    print("[fast  层 deepseek-chat] %.1fs ->" % t_fast, fast)

    t0 = time.time()
    reason = llm.reason_json(
        "你是职场关系分析师。只输出 JSON：{\"summary\":\"画像\",\"tendency\":\"类型\",\"advice\":\"应对要点\"}。",
        "称呼：小李；角色：平级；事件：多次以「很快/顺手」转达别组需求。",
        max_tokens=500)
    t_reason = time.time() - t0
    print("[reason 层 deepseek-reasoner] %.1fs ->" % t_reason, reason)

    ok = bool(fast and fast.get("text")) and bool(reason and reason.get("summary"))
    print("RESULT:", "PASS（两层均正常）" if ok else "FAIL（请检查 key/模型名/余额）")


if __name__ == "__main__":
    main()
