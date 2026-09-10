-- 004：情绪树洞（隐私隔离）+ 隐形画像
-- treehole_message：树洞对话独立存储，与台账/流水账物理隔离；
--   person 表不加外键关联，清空树洞不影响任何业务数据。
-- person.auto_profile：由「画像分析模型」从树洞倾诉与交锋记录中提取的
--   隐形画像（JSON 文本）。只在生成话术时作为背景注入，不向界面暴露。
CREATE TABLE IF NOT EXISTS treehole_message (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  role TEXT NOT NULL,          -- user | assistant
  content TEXT NOT NULL
);
ALTER TABLE person ADD COLUMN auto_profile TEXT NOT NULL DEFAULT '';
