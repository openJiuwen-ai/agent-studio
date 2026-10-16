/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

-- 智能体test_agent_id的第三个发布版本，专用于共享场景（版本号与test_version_id无前缀包含关系，
-- 避免t_share_resource.version_list的contains语义产生歧义）
INSERT INTO t_release_version(id, version_id, version_name, version_note, app_id, app_type, status, dsl_path, ir_path, creator, creator_id, released_on)
VALUES ('uuid6', 'test_shared_version_id', 'test_shared_version_name', 'note', 'test_agent_id', 'agent', 'normal', 'test_dsl_path', 'test_ir_path', 'user', 'user_id', '2024-08-13 17:30:28');

-- test_version_id被本空间(default)的智能体直接引用，计入引用统计
INSERT INTO t_mapping(mapping_id, app_id, app_type, app_name, resource_id, resource_type, resource_name, resource_version, valid, reference_type, resource_workspace_id, app_workspace_id, created_on, updated_on, extends)
VALUES ('test_ref_mapping_agent_v1', 'test_agent_id2', 'agent', '测试Agent2', 'test_agent_id', 'agent', '测试Agent', 'test_version_id', 1, 'direct', 'default', 'default', '2024-08-12 20:34:00', '2024-08-12 20:34:00', null);

-- test_version_id被本空间(default)的工作流直接引用，计入引用统计
INSERT INTO t_mapping(mapping_id, app_id, app_type, app_name, resource_id, resource_type, resource_name, resource_version, valid, reference_type, resource_workspace_id, app_workspace_id, created_on, updated_on, extends)
VALUES ('test_ref_mapping_agent_v1_wf', 'test_workflow_id', 'workflow', 'questions测试', 'test_agent_id', 'agent', '测试Agent', 'test_version_id', 1, 'direct', 'default', 'default', '2024-08-12 20:34:00', '2024-08-12 20:34:00', null);

-- test_version_id被跨空间共享引用（引用方在default_1空间，资源原空间为default），计入引用统计
INSERT INTO t_mapping(mapping_id, app_id, app_type, app_name, resource_id, resource_type, resource_name, resource_version, valid, reference_type, resource_workspace_id, app_workspace_id, created_on, updated_on, extends)
VALUES ('test_ref_mapping_agent_v1_share', 'test_agent_id9', 'controller', 'test_multi_agent', 'test_agent_id', 'agent', '测试Agent', 'test_version_id', 1, 'share', 'default', 'default_1', '2024-08-12 20:34:00', '2024-08-12 20:34:00', null);

-- test_version_id被default_1空间的工作流直接引用，不计入default空间引用统计
INSERT INTO t_mapping(mapping_id, app_id, app_type, app_name, resource_id, resource_type, resource_name, resource_version, valid, reference_type, resource_workspace_id, app_workspace_id, created_on, updated_on, extends)
VALUES ('test_ref_mapping_agent_v1_other_ws', 'test_workflow_id14', 'workflow', '验证1', 'test_agent_id', 'agent', '测试Agent', 'test_version_id', 1, 'direct', 'default', 'default_1', '2024-08-12 20:34:00', '2024-08-12 20:34:00', null);

-- 无效引用（valid=0），不计入引用统计
INSERT INTO t_mapping(mapping_id, app_id, app_type, app_name, resource_id, resource_type, resource_name, resource_version, valid, reference_type, resource_workspace_id, app_workspace_id, created_on, updated_on, extends)
VALUES ('test_ref_mapping_agent_invalid', 'test_agent_id2', 'agent', '测试Agent2', 'test_agent_id', 'agent', '测试Agent', 'test_version_id', 0, 'direct', 'default', 'default', '2024-08-12 20:34:00', '2024-08-12 20:34:00', null);

-- test_version_id1被本空间的智能体直接引用，计入引用统计
INSERT INTO t_mapping(mapping_id, app_id, app_type, app_name, resource_id, resource_type, resource_name, resource_version, valid, reference_type, resource_workspace_id, app_workspace_id, created_on, updated_on, extends)
VALUES ('test_ref_mapping_agent_v2', 'test_agent_id3', 'agent', '测试Agent3', 'test_agent_id', 'agent', '测试Agent', 'test_version_id1', 1, 'direct', 'default', 'default', '2024-08-12 20:34:00', '2024-08-12 20:34:00', null);

-- 工作流test_workflow_id的test_version_id2被本空间智能体直接引用，计入引用统计
INSERT INTO t_mapping(mapping_id, app_id, app_type, app_name, resource_id, resource_type, resource_name, resource_version, valid, reference_type, resource_workspace_id, app_workspace_id, created_on, updated_on, extends)
VALUES ('test_ref_mapping_workflow_v2', 'test_agent_id2', 'agent', '测试Agent2', 'test_workflow_id', 'workflow', 'questions测试', 'test_version_id2', 1, 'direct', 'default', 'default', '2024-08-12 20:34:00', '2024-08-12 20:34:00', null);

-- 工作流test_workflow_id的test_version_id3被本空间工作流直接引用，计入引用统计
INSERT INTO t_mapping(mapping_id, app_id, app_type, app_name, resource_id, resource_type, resource_name, resource_version, valid, reference_type, resource_workspace_id, app_workspace_id, created_on, updated_on, extends)
VALUES ('test_ref_mapping_workflow_v3', 'test_llm_workflow_id', 'workflow', '大厨师_', 'test_workflow_id', 'workflow', 'questions测试', 'test_version_id3', 1, 'direct', 'default', 'default', '2024-08-12 20:34:00', '2024-08-12 20:34:00', null);

-- 智能体test_agent_id的test_shared_version_id已共享到资产广场，不允许直接删除
INSERT INTO t_share_resource(resource_id, resource_name, resource_type, workspace_id, workspace_name, trace_id, version_list, project_id, tenant_id, creator_id, creator, updater_id, updater)
VALUES ('test_agent_id', '测试Agent', 'agent', 'default', 'default', null, 'test_shared_version_id', 'test_project_id', 'test_tenant_id', 'test_creator_id', 'test_creator', 'test_creator_id', 'test_creator');

-- 工作流test_workflow_id的test_version_id3已共享到资产广场，不允许直接删除
INSERT INTO t_share_resource(resource_id, resource_name, resource_type, workspace_id, workspace_name, trace_id, version_list, project_id, tenant_id, creator_id, creator, updater_id, updater)
VALUES ('test_workflow_id', 'questions测试', 'workflow', 'default', 'default', null, 'test_version_id3', 'test_project_id', 'test_tenant_id', 'test_creator_id', 'test_creator', 'test_creator_id', 'test_creator');
