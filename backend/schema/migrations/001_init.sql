-- PushIt「数据层」初始迁移 v1（对应项目书附录 A 数据模型草案）
-- 实体：project / person / requirement / estimate_item / baseline_item / change_log / encounter
-- 设计要点：
--   · 「项目承诺」为主轴、「提出人」为副轴（requirement 必挂两者）
--   · change_log.handed_to_person_id → 支撑 §6.9 拒绝债/转嫁监测
--   · person.comm_style → 支撑 §6.8 明确度档位（高/低语境）
--   · requirement.should_accept → 支撑 §6.7 该接就接判定

CREATE TABLE IF NOT EXISTS project (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    is_mainline   INTEGER NOT NULL DEFAULT 0,
    period_commit TEXT,                -- 当前周期承诺文本
    created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS person (
    id               TEXT PRIMARY KEY,
    name             TEXT NOT NULL,    -- 用户手输称呼，不解析真实身份（§15.2）
    role             TEXT NOT NULL CHECK (role IN ('boss','mid','peer','other')),
    comm_style       TEXT NOT NULL DEFAULT 'low' CHECK (comm_style IN ('high','low')),  -- 高/低语境 → 明确度档位
    memo             TEXT,             -- 关系记忆
    reaction_pattern TEXT,             -- 被拒反应模式（主观笔记）
    risk_flags       TEXT,             -- 风险标记 json（仅本地、禁止外发，§6.6）
    created_at       TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS requirement (
    id             TEXT PRIMARY KEY,
    project_id     TEXT NOT NULL REFERENCES project(id),
    person_id      TEXT NOT NULL REFERENCES person(id),
    raw_text       TEXT NOT NULL,      -- 原文/转写（粘贴消息为主，§5.0）
    source         TEXT NOT NULL CHECK (source IN ('oral','message','meeting','oneone')),
    motivation     TEXT NOT NULL CHECK (motivation IN ('boss_press','self_achievement','relay','other')),
    should_accept  INTEGER NOT NULL DEFAULT 0,  -- 该接就接判定结果（1=建议接，§6.7）
    status         TEXT NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending','aligned','accepted','declined','deferred','canceled')),
    created_at     TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at     TEXT
);

CREATE TABLE IF NOT EXISTS estimate_item (
    id             TEXT PRIMARY KEY,
    requirement_id TEXT NOT NULL REFERENCES requirement(id),
    subtask        TEXT NOT NULL,
    hours_low      REAL NOT NULL,      -- 防反噬口径：只给保守区间（§8）
    hours_high     REAL NOT NULL,
    dependencies   TEXT,               -- 依赖
    risk_note      TEXT,               -- 技术债/返工风险标注
    assumptions    TEXT,               -- 口径/前提假设（让领导砍假设而非信用）
    actual_hours   REAL,               -- P1 校准用（估 vs 实际）
    created_at     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS baseline_item (
    id         TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES project(id),
    period     TEXT NOT NULL,          -- 周/季
    item       TEXT NOT NULL,
    base_hours REAL NOT NULL,
    aligned_at TEXT                    -- 对齐时间（留痕）
);

CREATE TABLE IF NOT EXISTS change_log (
    id                  TEXT PRIMARY KEY,
    requirement_id      TEXT REFERENCES requirement(id),
    person_id           TEXT NOT NULL REFERENCES person(id),   -- 发起人
    happened_at         TEXT NOT NULL,
    content             TEXT NOT NULL,                          -- 变更内容
    impact              TEXT,                                   -- 对基线影响
    result              TEXT NOT NULL CHECK (result IN ('decline','accept','resched','cut','done','park')),
    handed_to_person_id TEXT REFERENCES person(id),             -- 转派对象（NULL=未转派）→ 拒绝债监测
    warded_hours        REAL DEFAULT 0,                         -- 赢回工时（复利曲线净账分母）
    created_at          TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS encounter (
    id             TEXT PRIMARY KEY,
    change_id      TEXT NOT NULL REFERENCES change_log(id),
    script_version TEXT,               -- 所用话术版本
    other_reaction TEXT,               -- 对方反应（客观事件 + 主观感受，§6.6）
    outcome        TEXT NOT NULL,      -- 结果（对方撤回/改期/接受/僵持…）
    review_note    TEXT,               -- 复盘标注 → 校准画像与策略有效性
    created_at     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_req_project ON requirement(project_id);
CREATE INDEX IF NOT EXISTS idx_req_person  ON requirement(person_id);
CREATE INDEX IF NOT EXISTS idx_change_req  ON change_log(requirement_id);
CREATE INDEX IF NOT EXISTS idx_change_hand  ON change_log(handed_to_person_id);
