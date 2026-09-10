# PushIt（推它）

> 面向广义知识工作者的多端工具：把领导“一句话加活”翻译成代价账，
> 让不合理需求自己消失，拒绝全程零流血、不结仇、不穿小鞋。
> 名字释义：把该推回去的活，体面地“推”回去。

## 文档
- [项目书 v1.0](./项目书.md) —— 立项草案（9 轮修订；已定名、形态已拍板，M0 开工中）

## 状态
- 2026-09-09：**正式名 PushIt（推它）**；**形态拍板：手机/桌面/网页三端同源，重点手机端，Android 先于 iOS**（§9）。
- 核心结论：靶心对象＝中层领导；三大支柱＝策略引擎 / 激活层 / 安全层。
- 关键护栏：「当场 vs 事后」时刻模型、“该接就接”过滤器、明确性护栏（§6.8）、拒绝债（§6.9）、纯本地优先 + 可选 E2EE 同步。
- **M1 端到端 mock 已通**：后端 pipeline 4 项测试全绿；前端三端同源可演示（粘贴→处理报告→挡掉→避坑交接→负载/净账联动）。契约草案 `docs/contract.md`。
- **v1.1（2026-09-10）**：反踢皮球双向护栏（§6.10）、人员行为画像（person_behavior 迁移 002）、LLM 分层架构（规则/快模型/推理模型）。

## 目录规划
```
docs/tasks/    任务板（分工 A–E 唯一事实源）
backend/       逻辑层（FastAPI；schema 迁移、services 按线分目录）
frontend/      前端（响应式 Web，三端同源；手机优先、Android 优先）
data/          本地数据与策略知识库（纯本地）
scripts/       种子/导入/验收脚本
tests/         单元与验收测试
```

## 下载（最新 v0.1.7，GitHub Releases）
- 电脑版（Windows exe，解压双击即用）：https://github.com/nebulaeyes1456/PushIt/releases/download/v0.1.7/PushIt-win64.zip
- 手机版（网页资源包）：https://github.com/nebulaeyes1456/PushIt/releases/download/v0.1.7/PushIt-mobile.zip

### 国内下载加速（GitHub 直连慢/断时用）
- **手机版稳定直链**（jsDelivr CDN，随仓库自动更新）：https://cdn.jsdelivr.net/gh/nebulaeyes1456/PushIt@main/dist/PushIt-mobile.zip
- **任意 Release 文件走镜像前缀**（任选其一，实测可用）：`https://ghproxy.net/`、`https://gh-proxy.com/`；用法＝镜像前缀拼原链接，例如：
  - 电脑版加速：https://ghproxy.net/https://github.com/nebulaeyes1456/PushIt/releases/download/v0.1.7/PushIt-win64.zip

## 交付物（release/）
- `PushIt-电脑版-安装包.zip`：解压双击 `PushIt.exe` 即用（内置服务自动开浏览器；数据存 exe 旁 data\；详细见包内安装教程）
- `PushIt-手机版.zip`：离线演示版（浏览器打开 index.html）；完整手机安装方式见《手机版使用教程》（安卓添加到主屏幕；微信小程序需开发者账号/审核，暂缓）

## 运行演示
- 后端（M2 已实现）：`.venv/Scripts/python -m uvicorn backend.main:app --app-dir . --port 8765`
  - 验收：`.venv/Scripts/python -m unittest discover -s tests`（4 项）＋ `.venv/Scripts/python scripts/smoke_api.py`（6/6）
  - LLM（可选）：把 DeepSeek key 填入 `data/llm_config.json` 的 `api_key`（默认 https://api.deepseek.com，快层 deepseek-chat / 推理层 deepseek-reasoner；已入 .gitignore，勿提交）；填好后运行 `.venv/Scripts/python scripts/check_llm.py` 验证两层。未配置自动降级规则引擎
- 前端（三端同源，手机优先）：`python -m http.server 8123 --directory frontend`，浏览器开 http://127.0.0.1:8123
  - 纯 mock 演示：直接开；**真后端模式：http://127.0.0.1:8123/?api=1**（后端不可用自动回落 mock）
  - 手机：同一局域网访问 `http://<电脑IP>:8123`；iOS Safari 不适配时先保 Android 与桌面浏览器（§9）
- 数据：`scripts/seed_mock.py` 生成 `data/pushit.db`（幂等）；策略库 `data/strategy_lib.json`
