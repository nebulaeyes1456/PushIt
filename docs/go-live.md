# PushIt · 上线操作单（用户只需 3 步）

> 技术准备已全部完成：仓库含两个自动发布工作流，推送后**电脑版与手机版都会自动生成**。
> 你只需要做下面 3 步（第 3 步是一次性的）。

## 第 1 步：建 GitHub 仓库（约 1 分钟）
1. 打开 https://github.com/new
2. 仓库名填 `PushIt`（或任意），可见性选 **公开**（Pages 免费要求；想低调可先私有）
3. 建好后记下仓库地址：`https://github.com/<你的用户名>/PushIt.git`

## 第 2 步：推送代码（本地已初始化，跑 2 条命令）
```powershell
git remote add origin https://github.com/<你的用户名>/PushIt.git
git push -u origin main
```
> 提示需要登录时按提示用浏览器授权（或用 `gh auth login`）。

## 第 3 步：一次性设置（约 2 分钟）
1. **开 Pages**：仓库 → Settings → Pages → Source 选 **GitHub Actions**；
2. **出电脑版**：仓库 → Actions → 左侧 "Build Windows Release" → Run workflow →（或本地执行
   `git tag v0.1.0 && git push origin v0.1.0`，tag 会自动触发）；
3. 完成后：Release 页有 `PushIt-电脑版-安装包.zip` 下载链接；Pages 部署完成后
   手机访问 `https://<你的用户名>.github.io/PushIt/`。

## 推送后自动发生什么
```
git push
  ├─ pages.yml：frontend/ 自动部署 → 手机/网页版网址（打开即用，可添加到主屏幕）
  └─ release.yml（推 v* tag 时）：云端打包 PushIt.exe → Release 发布电脑版 zip
```

## 落地链接汇总（发帖用）
| 对象 | 链接 |
|---|---|
| 电脑用户 | `https://github.com/<你>/PushIt/releases/latest` |
| 手机用户 | `https://<你>.github.io/PushIt/` |

## 注意事项
- Windows SmartScreen 会提示"未知发布者"，帖子/教程里已说明（点"更多信息 → 仍要运行"）；
- exe 未签名：后续有余力可购代码签名证书；
- 手机版默认规则模式（零成本）；要 DeepSeek 增强需另部署后端（见 docs/distribution.md）；
- 网盘备选：把 `release/` 两个 zip 传到蓝奏云/夸克，帖子里贴网盘链接即可。
