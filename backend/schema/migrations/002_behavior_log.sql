-- PushIt「数据层」迁移 v2：人员行为日志（§6 第 10 条「画像驱动」，F 线消费）
-- kind 语义：
--   kick_ball   对方踢皮球（无前置/无信息/“很快·顺便”式转派）
--   deflect     甩锅行为
--   reliable    可靠（交付/承诺兑现）
--   commit_kept 承诺兑现
--   hostile     公开质疑/针对（对应 §6.6 风险标记）
-- 合规：evidence 为客观事件 + 主观感受的本地笔记，禁止外发（§6.6/§15）

CREATE TABLE IF NOT EXISTS person_behavior (
    id         TEXT PRIMARY KEY,
    person_id  TEXT NOT NULL REFERENCES person(id),
    kind       TEXT NOT NULL CHECK (kind IN ('kick_ball','deflect','reliable','commit_kept','hostile')),
    evidence   TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_beh_person ON person_behavior(person_id);
