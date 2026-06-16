-- 五剧本视图联动数据表设计
-- 主键链路：play_id -> character_id / relation_id / scene_id / theme_id / flow_id

CREATE TABLE plays (
  play_id VARCHAR(32) PRIMARY KEY COMMENT '剧本唯一编号，来自 PDF 文件名前缀',
  title VARCHAR(64) NOT NULL COMMENT '剧本名称',
  source_file VARCHAR(255) COMMENT '原始 PDF 文件路径',
  flow_id VARCHAR(64) COMMENT '所属主视图闭环模式编号',
  summary TEXT COMMENT '剧本主题与核心人物概述',
  scene_count INT COMMENT '场次数',
  character_count INT COMMENT '人物数',
  relation_count INT COMMENT '人物关系数',
  main_theme_id VARCHAR(64) COMMENT '第一主题编号',
  main_theme VARCHAR(64) COMMENT '第一主题名称',
  narrative_mode VARCHAR(64) COMMENT '叙事模式名称',
  evolution_mode VARCHAR(64) COMMENT '关系演化模式名称',
  center_role VARCHAR(64) COMMENT '关系网络中心人物'
) COMMENT='剧本主表，所有小视图和主视图联动的剧本入口';

CREATE TABLE characters (
  character_id VARCHAR(64) PRIMARY KEY COMMENT '人物唯一编号，由 play_id 与角色名稳定生成',
  play_id VARCHAR(32) NOT NULL COMMENT '所属剧本编号',
  name VARCHAR(64) NOT NULL COMMENT '人物名称',
  trade VARCHAR(32) COMMENT '标准行当，用于图标与跨视图联动，如老生、小生、花旦',
  raw_trade VARCHAR(32) COMMENT 'PDF/剧本中抽取到的原始或细分行当，仅作溯源，如生、娃娃生、二旦',
  standard_trade VARCHAR(32) COMMENT '标准行当冗余字段，便于旧组件读取',
  major_trade VARCHAR(16) COMMENT '大类行当，由标准行当归并为生/旦/净/丑',
  role_level VARCHAR(16) COMMENT '网络人物层级编码：core/major/minor',
  role_level_label VARCHAR(32) COMMENT '网络人物层级名称：核心人物/主要人物/次要人物',
  network_rank INT COMMENT '人物网络排序，数值越小越核心',
  role_order INT COMMENT '主要角色表中的出现顺序',
  scene_count INT COMMENT '出现的场次数',
  speech_count INT COMMENT '台词行估算次数',
  mention_count INT COMMENT '文本中被提及次数',
  text_length INT COMMENT '人物文本量估算值',
  importance DECIMAL(8,4) COMMENT '人物重要度，0-1',
  scene_ids TEXT COMMENT '人物出现的场次 ID 列表',
  primary_scene_id VARCHAR(64) COMMENT '人物最主要场次 ID',
  linked_theme_ids TEXT COMMENT '人物关联主题 ID 列表',
  linked_themes TEXT COMMENT '人物关联主题名称列表',
  FOREIGN KEY (play_id) REFERENCES plays(play_id)
) COMMENT='人物表，供左上行当视图和右上角色网络共同使用';

CREATE TABLE relations (
  relation_id VARCHAR(64) PRIMARY KEY COMMENT '人物关系唯一编号',
  play_id VARCHAR(32) NOT NULL COMMENT '所属剧本编号',
  source_character_id VARCHAR(64) NOT NULL COMMENT '关系起点人物 ID',
  target_character_id VARCHAR(64) NOT NULL COMMENT '关系终点人物 ID',
  source VARCHAR(64) COMMENT '起点人物名称',
  target VARCHAR(64) COMMENT '终点人物名称',
  source_trade VARCHAR(32) COMMENT '起点人物标准行当',
  target_trade VARCHAR(32) COMMENT '终点人物标准行当',
  source_raw_trade VARCHAR(32) COMMENT '起点人物原始/细分行当，仅作溯源',
  target_raw_trade VARCHAR(32) COMMENT '终点人物原始/细分行当，仅作溯源',
  source_standard_trade VARCHAR(32) COMMENT '起点人物标准行当，用于网络节点联动',
  target_standard_trade VARCHAR(32) COMMENT '终点人物标准行当，用于网络节点联动',
  source_level VARCHAR(16) COMMENT '起点人物层级编码：core/major/minor',
  target_level VARCHAR(16) COMMENT '终点人物层级编码：core/major/minor',
  source_level_label VARCHAR(32) COMMENT '起点人物层级名称',
  target_level_label VARCHAR(32) COMMENT '终点人物层级名称',
  relation_type VARCHAR(32) COMMENT '关系类型编码，如 power/conflict/kinship/alliance',
  relation_label VARCHAR(64) COMMENT '关系类型展示名称',
  relation_desc TEXT COMMENT '关系说明',
  weight DECIMAL(8,2) COMMENT '关系权重',
  relation_rank INT COMMENT '该剧本内关系强弱排序，数值越小越重要',
  scene_ids TEXT COMMENT '关系出现的场次 ID 列表',
  first_scene_no INT COMMENT '关系首次出现的场序',
  last_scene_no INT COMMENT '关系最后出现的场序',
  evidence TEXT COMMENT '关系证据摘要',
  FOREIGN KEY (play_id) REFERENCES plays(play_id),
  FOREIGN KEY (source_character_id) REFERENCES characters(character_id),
  FOREIGN KEY (target_character_id) REFERENCES characters(character_id)
) COMMENT='人物关系表，驱动右上角色网络';

CREATE TABLE play_themes (
  play_id VARCHAR(32) NOT NULL COMMENT '所属剧本编号',
  theme_id VARCHAR(64) NOT NULL COMMENT '主题编号',
  theme VARCHAR(64) NOT NULL COMMENT '主题名称',
  score DECIMAL(10,2) COMMENT '主题得分',
  share DECIMAL(8,4) COMMENT '主题占比，0-1',
  rank INT COMMENT '主题排序',
  evidence VARCHAR(128) COMMENT '主题命中证据词或题材依据',
  PRIMARY KEY (play_id, theme_id),
  FOREIGN KEY (play_id) REFERENCES plays(play_id)
) COMMENT='剧本主题表，驱动右下主题组合图';

CREATE TABLE scenes (
  scene_id VARCHAR(64) PRIMARY KEY COMMENT '场次唯一编号',
  play_id VARCHAR(32) NOT NULL COMMENT '所属剧本编号',
  scene_no INT COMMENT '场序',
  scene_label VARCHAR(32) COMMENT '场次标签，如第一场',
  stage_type VARCHAR(32) COMMENT '五阶段类型：开端/发展/转折/高潮/结局',
  conflict_type VARCHAR(64) COMMENT '冲突类型',
  summary TEXT COMMENT '场次摘要',
  character_ids TEXT COMMENT '本场出现人物 ID 列表',
  relation_ids TEXT COMMENT '本场出现关系 ID 列表',
  performance_density DECIMAL(8,4) COMMENT '表演形式密度，0-1',
  role_activity DECIMAL(8,4) COMMENT '角色活跃度，0-1',
  conflict_strength DECIMAL(8,4) COMMENT '冲突强度，0-1',
  relation_change_strength DECIMAL(8,4) COMMENT '关系变化强度，0-1',
  emotion_strength DECIMAL(8,4) COMMENT '情绪强度，0-1',
  plot_strength DECIMAL(8,4) COMMENT '综合剧情强度，0-1',
  FOREIGN KEY (play_id) REFERENCES plays(play_id)
) COMMENT='场次动力学表，驱动中下水墨趋势图';

CREATE TABLE scene_characters (
  scene_id VARCHAR(64) NOT NULL COMMENT '场次 ID',
  play_id VARCHAR(32) NOT NULL COMMENT '剧本 ID',
  character_id VARCHAR(64) NOT NULL COMMENT '人物 ID',
  character_name VARCHAR(64) COMMENT '人物名称冗余字段，便于查询',
  PRIMARY KEY (scene_id, character_id),
  FOREIGN KEY (scene_id) REFERENCES scenes(scene_id),
  FOREIGN KEY (character_id) REFERENCES characters(character_id)
) COMMENT='场次-人物外联表';

CREATE TABLE scene_relations (
  scene_id VARCHAR(64) NOT NULL COMMENT '场次 ID',
  play_id VARCHAR(32) NOT NULL COMMENT '剧本 ID',
  relation_id VARCHAR(64) NOT NULL COMMENT '关系 ID',
  PRIMARY KEY (scene_id, relation_id),
  FOREIGN KEY (scene_id) REFERENCES scenes(scene_id),
  FOREIGN KEY (relation_id) REFERENCES relations(relation_id)
) COMMENT='场次-关系外联表';

CREATE TABLE main_flows (
  id VARCHAR(64) PRIMARY KEY COMMENT '主视图闭环模式 ID',
  relationType VARCHAR(64) COMMENT '主导关系类型',
  themeCombo VARCHAR(128) COMMENT '主题组合',
  narrativeType VARCHAR(64) COMMENT '叙事结构类型',
  evolutionType VARCHAR(64) COMMENT '关系演化类型',
  count INT COMMENT '该闭环模式包含剧本数',
  scripts TEXT COMMENT '剧本 ID 列表',
  narrativeCurve TEXT COMMENT '叙事曲线数组',
  evolutionCurve TEXT COMMENT '演化曲线数组',
  representativePlayId VARCHAR(32) COMMENT '代表剧本 ID'
) COMMENT='主视图闭环模式表';

CREATE TABLE main_flow_plays (
  flow_id VARCHAR(64) NOT NULL COMMENT '闭环模式 ID',
  play_id VARCHAR(32) NOT NULL COMMENT '剧本 ID',
  PRIMARY KEY (flow_id, play_id),
  FOREIGN KEY (flow_id) REFERENCES main_flows(id),
  FOREIGN KEY (play_id) REFERENCES plays(play_id)
) COMMENT='主视图闭环-剧本外联表';

CREATE TABLE role_trade_metrics (
  play_id VARCHAR(32) NOT NULL COMMENT '剧本 ID',
  character_id VARCHAR(64) NOT NULL COMMENT '人物 ID',
  script_name VARCHAR(64) COMMENT '剧本名称',
  role_name VARCHAR(64) COMMENT '角色名称',
  trade VARCHAR(32) COMMENT '标准行当，用于左上行当图标和跨视图匹配',
  raw_trade VARCHAR(32) COMMENT '原始或细分行当，仅作溯源',
  standard_trade VARCHAR(32) COMMENT '标准行当冗余字段，便于旧组件读取',
  major_trade VARCHAR(16) COMMENT '大类行当，由标准行当归并为生/旦/净/丑',
  role_level VARCHAR(16) COMMENT '网络人物层级编码：core/major/minor',
  role_level_label VARCHAR(32) COMMENT '网络人物层级名称',
  character_type VARCHAR(32) COMMENT '人物类型',
  total_scenes INT COMMENT '剧本总场次数',
  appearance_scenes INT COMMENT '人物出现场次数',
  appearance_ratio DECIMAL(8,4) COMMENT '出场占比',
  stage_span DECIMAL(8,4) COMMENT '阶段跨度',
  centrality DECIMAL(8,4) COMMENT '人物中心度',
  role_text_length INT COMMENT '人物文本量',
  lyric_density DECIMAL(8,4) COMMENT '唱念密度估算',
  emotion_intensity DECIMAL(8,4) COMMENT '情绪强度估算',
  action_intensity DECIMAL(8,4) COMMENT '行动强度估算',
  relation_strength DECIMAL(8,4) COMMENT '关系强度估算',
  primary_scene_id VARCHAR(64) COMMENT '主场次 ID',
  linked_theme_ids TEXT COMMENT '关联主题 ID 列表',
  PRIMARY KEY (play_id, character_id)
) COMMENT='左上行当特征视图用指标表';

CREATE TABLE trade_patterns (
  play_id VARCHAR(32) NOT NULL COMMENT '剧本 ID',
  script_name VARCHAR(64) COMMENT '剧本名称',
  trade VARCHAR(32) COMMENT '标准行当',
  raw_trades VARCHAR(255) COMMENT '聚合到该标准行当下的原始行当集合',
  role_count INT COMMENT '该行当人物数',
  avg_importance DECIMAL(8,4) COMMENT '该行当平均重要度',
  avg_presence DECIMAL(8,4) COMMENT '该行当平均出场占比',
  avg_relation DECIMAL(8,4) COMMENT '该行当平均关系强度',
  character_ids TEXT COMMENT '该行当人物 ID 列表',
  PRIMARY KEY (play_id, trade)
) COMMENT='剧本-行当聚合表';
