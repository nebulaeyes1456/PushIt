# PushIt · MVP 数据契约草案（T8，M1 冻结用）

> 目的：A/C/E 三线对齐的数据形状。前端 mock（localStorage）与后端规则引擎
> （backend/services）输出同构，M2 接真接口/LLM 时只换实现、不改形状。

## 1. 核心对象：处理报告 report

后端 `pipeline.process(id)` 与前端 `mockProcess(text, person, source)` 输出同构：

```jsonc
{
  "requirement_id": "r001",          // 前端为前端生成 id，后端为 DB id
  "requirement": "原文/转写文本",     // 粘贴消息为主（§5.0）
  "project": "数据平台迁移",
  "person": { "name": "王组长", "role": "中层" },   // role∈大老板/中层/平级/其他
  "motivation": { "id": "self_achievement", "label": "中层要业绩 / 拍脑袋" },
  "should_accept": 0,                // §6.7 该接就接判定
  "verdict": "该拒 / 需对齐（走拒绝或重谈）",
  "estimate": {                      // §8 防反噬口径：只给区间
    "items": [{ "subtask": "", "hours_low": 3.6, "hours_high": 7.9,
                "dependencies": "", "risk_note": "", "assumptions": "" }],
    "total_low": 3.6, "total_high": 7.9, "scale": 1.8,
    "capacity": { "committed": 32, "cap": 40, "remaining": 8, "after_add_low": 4.4, "overload": false }
  },
  "strategy": {                      // C 线产物（含 script_fields 双质检）
    "tactic_id": "two_options", "tactic_name": "给两个能接受的选项",
    "text": "可照念的安全版话术……",
    "clarify_dial": "high",          // 明确度档位（§6.8）
    "conclusion": "请从 A/B 两案中选一；未选前不启动。",   // 先明确、后台阶
    "recall_test": "3 秒复述自检……",
    "redline_report": { "forbidden_hits": [], "ambiguous_hits": [], "passed": true },
    "guardrail_tags": ["attribution", "clarity_conclusion_first"],
    "safe_version": true
  }
}
```

## 2. 前端持久化：pushit_reqs_v1（localStorage）

```jsonc
[{ "id": "Rxxxxx", "text": "", "person": "王组长", "source": "口头",
   "status": "pending|aligned|accepted|declined",   // declined 可带 handed=同事
   "low": 3, "high": 6.6, "scale": 1.5, "motivation": "self_achievement",
   "at": "今天 14:20" }]
```

## 3. REST 草案（✅ 已实现于 backend/main.py，M2 冒烟通过）

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/v1/requirements` | POST | 新建台账（粘贴文本 + 人 + 来源） |
| `/api/v1/requirements/{id}/process` | POST | 生成处理报告（估/判/话术/双质检） |
| `/api/v1/requirements/{id}/result` | POST | 记结果（accept/decline/park + handed_to）→ change_log |
| `/api/v1/load` | GET | 承诺 vs 新增挤压（容量视图） |

## 4. 契约不变式（改口径纪律）
- 任何字段/阈值变更 = 口径变更：同步改 后端引擎 + 前端 mock + 本文件 + 任务板备注；
  前端 localStorage 结构升级需 bump key（现 `pushit_reqs_v1`）。
