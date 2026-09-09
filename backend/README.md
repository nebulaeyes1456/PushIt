# backend（API / 逻辑层）

方向：FastAPI（复用既有工程经验）；MVP 先本地、mock 优先、LLM 双模（规则兜底 + 受限增强，§10.3）。

## 目录规划（对应分工线）
- `schema/migrations/` —— D 线：SQLite 迁移（001_init.sql 已落地）
- `services/understand/` 需求理解（§10.1 Agent1，A 线）
- `services/estimate/`   代价估算（A 线）
- `services/strategy/`   策略选择（B 线）
- `services/script/`     话术生成（C 线）
- `services/redline/`    红线检测 + 明确性校验（C 线）
- `services/review/`     复盘校准（复盘 Agent）
- `routers/`             接口层（M1 起，契约见任务板 T8）

> 推进状态见 `docs/tasks/backlog.md`。
