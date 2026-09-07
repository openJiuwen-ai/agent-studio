-- 回归测试种子数据：共享插件铃铛最新版本场景（配套 RelationShareLatestVersionTest）
-- version_id 使用真实数据形态：等长13位时间戳字符串
-- 场景1-3：插件 sv_plugin_1，活版本 1770000000000(v1)/1785000000000(v2)，软删版本 1776000000000(v3，曾共享后被删)
INSERT INTO t_release_version (id, version_id, version_name, version_note, app_id, app_type, status, creator, creator_id, released_on, extend1, dsl_path, ir_path, deleted)
VALUES ('sv_rv_1', '1770000000000', 'v1', 'test', 'sv_plugin_1', 'tool', 'normal', 'tester', 'tester', '2026-04-01 10:00:00', '', '', '', 0);
INSERT INTO t_release_version (id, version_id, version_name, version_note, app_id, app_type, status, creator, creator_id, released_on, extend1, dsl_path, ir_path, deleted)
VALUES ('sv_rv_2', '1785000000000', 'v2', 'test', 'sv_plugin_1', 'tool', 'normal', 'tester', 'tester', '2026-08-01 10:00:00', '', '', '', 0);
INSERT INTO t_release_version (id, version_id, version_name, version_note, app_id, app_type, status, creator, creator_id, released_on, extend1, dsl_path, ir_path, deleted)
VALUES ('sv_rv_3', '1776000000000', 'v3', 'test', 'sv_plugin_1', 'tool', 'normal', 'tester', 'tester', '2026-04-15 10:00:00', '', '', '', 1);

-- 场景4：插件 sv_plugin_2，活版本 1785500000000/1786000000000，共享快照指向从未存在的版本 1772000000000（客户现场场景）
INSERT INTO t_release_version (id, version_id, version_name, version_note, app_id, app_type, status, creator, creator_id, released_on, extend1, dsl_path, ir_path, deleted)
VALUES ('sv_rv_4', '1785500000000', 'v5_aug1', 'test', 'sv_plugin_2', 'tool', 'normal', 'tester', 'tester', '2026-08-05 10:00:00', '', '', '', 0);
INSERT INTO t_release_version (id, version_id, version_name, version_note, app_id, app_type, status, creator, creator_id, released_on, extend1, dsl_path, ir_path, deleted)
VALUES ('sv_rv_5', '1786000000000', 'v6_aug2', 'test', 'sv_plugin_2', 'tool', 'normal', 'tester', 'tester', '2026-08-20 10:00:00', '', '', '', 0);

-- 场景5：插件 sv_plugin_3（非共享），活版本 1780000000000，软删版本 1789000000000 为最大版本号
INSERT INTO t_release_version (id, version_id, version_name, version_note, app_id, app_type, status, creator, creator_id, released_on, extend1, dsl_path, ir_path, deleted)
VALUES ('sv_rv_6', '1780000000000', 'v7', 'test', 'sv_plugin_3', 'tool', 'normal', 'tester', 'tester', '2026-08-01 10:00:00', '', '', '', 0);
INSERT INTO t_release_version (id, version_id, version_name, version_note, app_id, app_type, status, creator, creator_id, released_on, extend1, dsl_path, ir_path, deleted)
VALUES ('sv_rv_7', '1789000000000', 'v9', 'test', 'sv_plugin_3', 'tool', 'normal', 'tester', 'tester', '2026-08-10 10:00:00', '', '', '', 1);

-- 共享记录：sv_plugin_1 快照含软删版本 1776000000000 与有效版本 1770000000000；sv_plugin_2 快照只含不存在的 1772000000000
INSERT INTO t_share_resource (resource_id, resource_name, resource_type, workspace_id, workspace_name, trace_id, version_list, project_id, tenant_id, creator_id, creator, create_time, updater_id, updater, update_time)
VALUES ('sv_plugin_1', 'sv_plugin_1', 'tool', 'default', 'default', NULL, '[{"version_id":"1776000000000","version_name":"v3"},{"version_id":"1770000000000","version_name":"v1"}]', 'test_project_id', 'system', 'tester', 'tester', CURRENT_TIMESTAMP, 'tester', 'tester', CURRENT_TIMESTAMP);
INSERT INTO t_share_resource (resource_id, resource_name, resource_type, workspace_id, workspace_name, trace_id, version_list, project_id, tenant_id, creator_id, creator, create_time, updater_id, updater, update_time)
VALUES ('sv_plugin_2', 'sv_plugin_2', 'tool', 'default', 'default', NULL, '[{"version_id":"1772000000000","version_name":"v4_april"}]', 'test_project_id', 'system', 'tester', 'tester', CURRENT_TIMESTAMP, 'tester', 'tester', CURRENT_TIMESTAMP);

-- 智能体（validateAppId 需 t_agent 存在）
INSERT INTO t_agent(agent_id, project_id, workspace_id, name, description, icon, status, creator, creator_id, created_on, updated_on, deleted)
VALUES ('sv_agent_1a', 'test_project_id', 'default', 'sv_agent_1a', 'share case current=v1', NULL, 'draft', 'tester', 'tester', '2026-08-01 10:00:00', '2026-08-01 10:00:00', 0);
INSERT INTO t_agent(agent_id, project_id, workspace_id, name, description, icon, status, creator, creator_id, created_on, updated_on, deleted)
VALUES ('sv_agent_1b', 'test_project_id', 'default', 'sv_agent_1b', 'share case current older than v1', NULL, 'draft', 'tester', 'tester', '2026-08-01 10:00:00', '2026-08-01 10:00:00', 0);
INSERT INTO t_agent(agent_id, project_id, workspace_id, name, description, icon, status, creator, creator_id, created_on, updated_on, deleted)
VALUES ('sv_agent_1c', 'test_project_id', 'default', 'sv_agent_1c', 'share case current=v2', NULL, 'draft', 'tester', 'tester', '2026-08-01 10:00:00', '2026-08-01 10:00:00', 0);
INSERT INTO t_agent(agent_id, project_id, workspace_id, name, description, icon, status, creator, creator_id, created_on, updated_on, deleted)
VALUES ('sv_agent_2a', 'test_project_id', 'default', 'sv_agent_2a', 'share snapshot all invalid', NULL, 'draft', 'tester', 'tester', '2026-08-01 10:00:00', '2026-08-01 10:00:00', 0);
INSERT INTO t_agent(agent_id, project_id, workspace_id, name, description, icon, status, creator, creator_id, created_on, updated_on, deleted)
VALUES ('sv_agent_3a', 'test_project_id', 'default', 'sv_agent_3a', 'direct reference soft-deleted max', NULL, 'draft', 'tester', 'tester', '2026-08-01 10:00:00', '2026-08-01 10:00:00', 0);

-- 关联映射：resource_id 带 # 触发去#预处理，tool 类型
INSERT INTO t_mapping (mapping_id, app_id, app_version, app_type, resource_id, resource_type, created_on, updated_on, app_name, resource_name, resource_version, resource_desc, valid, reference_type)
VALUES ('sv_map_1a', 'sv_agent_1a', NULL, 'agent', 'sv_plugin_1#0', 'tool', '2026-08-01 10:00:00', '2026-08-01 10:00:00', 'sv_agent_1a', 'sv_plugin_1', '1770000000000', NULL, 1, 'share');
INSERT INTO t_mapping (mapping_id, app_id, app_version, app_type, resource_id, resource_type, created_on, updated_on, app_name, resource_name, resource_version, resource_desc, valid, reference_type)
VALUES ('sv_map_1b', 'sv_agent_1b', NULL, 'agent', 'sv_plugin_1#0', 'tool', '2026-08-01 10:00:00', '2026-08-01 10:00:00', 'sv_agent_1b', 'sv_plugin_1', '1760000000000', NULL, 1, 'share');
INSERT INTO t_mapping (mapping_id, app_id, app_version, app_type, resource_id, resource_type, created_on, updated_on, app_name, resource_name, resource_version, resource_desc, valid, reference_type)
VALUES ('sv_map_1c', 'sv_agent_1c', NULL, 'agent', 'sv_plugin_1#0', 'tool', '2026-08-01 10:00:00', '2026-08-01 10:00:00', 'sv_agent_1c', 'sv_plugin_1', '1785000000000', NULL, 1, 'share');
INSERT INTO t_mapping (mapping_id, app_id, app_version, app_type, resource_id, resource_type, created_on, updated_on, app_name, resource_name, resource_version, resource_desc, valid, reference_type)
VALUES ('sv_map_2a', 'sv_agent_2a', NULL, 'agent', 'sv_plugin_2#0', 'tool', '2026-08-01 10:00:00', '2026-08-01 10:00:00', 'sv_agent_2a', 'sv_plugin_2', '1785500000000', NULL, 1, 'share');
INSERT INTO t_mapping (mapping_id, app_id, app_version, app_type, resource_id, resource_type, created_on, updated_on, app_name, resource_name, resource_version, resource_desc, valid, reference_type)
VALUES ('sv_map_3a', 'sv_agent_3a', NULL, 'agent', 'sv_plugin_3#0', 'tool', '2026-08-01 10:00:00', '2026-08-01 10:00:00', 'sv_agent_3a', 'sv_plugin_3', '1780000000000', NULL, 1, 'direct');
