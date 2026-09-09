-- PushIt「数据层」迁移 v3：语言风格偏好（画像维度：哪些人爱听尊敬话、哪些人觉得做作）
-- formal  = 爱听尊敬/正式措辞（“您/请示/汇报”）
-- plain   = 觉得太客套很做作，要平实直接
-- unknown = 暂未积累（由推理层从交锋记录逐步判定）
ALTER TABLE person ADD COLUMN speech_style TEXT NOT NULL DEFAULT 'unknown';
