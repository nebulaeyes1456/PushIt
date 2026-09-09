# data（运行时数据，纯本地）

- `pushit.db` —— SQLite 本地库（由 `scripts/seed_mock.py` 生成；幂等，可随时重跑）。
- `strategy_lib.json` —— B 线策略知识库（任务板 T4，源资产，暂存本地便于 mock/打包引用）。
- 隐私原则（§15）：纯本地、不上传；后续一键导出/彻底删除。
- mock 口径变更后：删 `pushit.db` 重跑种子即可（幂等种子以 requirement 是否为空判断）。

> 注意：本目录内容为运行时产物，加入 .gitignore（若建仓）；策略知识库 `strategy_lib.json` 由线 B 产出（任务板 T4）。
