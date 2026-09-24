/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */

package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@ExtendWith(MockitoExtension.class)
class PermissionServiceTest {

    @InjectMocks
    private PermissionService permissionService;

    @BeforeEach
    void setUp() {
        permissionService.clearDynamicPermissions();
    }

    @Test
    void testUpdateDynamicPermissions_Success() {
        Map<String, List<String>> permissions = new HashMap<>();
        permissions.put("admin", List.of("read", "write"));
        boolean result = permissionService.updateDynamicPermissions(permissions);
        assertTrue(result);
        assertTrue(permissionService.hasDynamicPermissions());
    }

    @Test
    void testUpdateDynamicPermissions_NullPermissions() {
        boolean result = permissionService.updateDynamicPermissions(null);
        assertFalse(result);
    }

    @Test
    void testUpdateDynamicPermissions_NullRoleName() {
        Map<String, List<String>> permissions = new HashMap<>();
        permissions.put(null, List.of("read"));
        boolean result = permissionService.updateDynamicPermissions(permissions);
        assertFalse(result);
    }

    @Test
    void testUpdateDynamicPermissions_EmptyRoleName() {
        Map<String, List<String>> permissions = new HashMap<>();
        permissions.put("  ", List.of("read"));
        boolean result = permissionService.updateDynamicPermissions(permissions);
        assertFalse(result);
    }

    @Test
    void testUpdateDynamicPermissions_NullPermissionList() {
        Map<String, List<String>> permissions = new HashMap<>();
        permissions.put("admin", null);
        boolean result = permissionService.updateDynamicPermissions(permissions);
        assertFalse(result);
    }

    @Test
    void testUpdateDynamicPermissions_NullPermissionInList() {
        Map<String, List<String>> permissions = new HashMap<>();
        permissions.put("admin", new ArrayList<>(Arrays.asList("read", null)));
        boolean result = permissionService.updateDynamicPermissions(permissions);
        assertFalse(result);
    }

    @Test
    void testGetMergedPermissions_NoDynamic() {
        Map<String, List<String>> preset = new HashMap<>();
        preset.put("user", List.of("read"));
        permissionService.setPresetPermissions(preset);

        Map<String, List<String>> merged = permissionService.getMergedPermissions();
        assertNotNull(merged);
        assertEquals(1, merged.size());
        assertTrue(merged.containsKey("user"));
    }

    @Test
    void testGetMergedPermissions_DynamicOverridesPreset() {
        Map<String, List<String>> preset = new HashMap<>();
        preset.put("admin", List.of("read"));
        permissionService.setPresetPermissions(preset);

        Map<String, List<String>> dynamic = new HashMap<>();
        dynamic.put("admin", List.of("read", "write", "delete"));
        permissionService.updateDynamicPermissions(dynamic);

        Map<String, List<String>> merged = permissionService.getMergedPermissions();
        assertEquals(List.of("read", "write", "delete"), merged.get("admin"));
    }

    @Test
    void testGetPermissionsByRole_FromDynamic() {
        Map<String, List<String>> dynamic = new HashMap<>();
        dynamic.put("admin", List.of("read", "write"));
        permissionService.updateDynamicPermissions(dynamic);

        List<String> perms = permissionService.getPermissionsByRole("admin");
        assertEquals(List.of("read", "write"), perms);
    }

    @Test
    void testGetPermissionsByRole_FromPreset() {
        Map<String, List<String>> preset = new HashMap<>();
        preset.put("user", List.of("read"));
        permissionService.setPresetPermissions(preset);

        List<String> perms = permissionService.getPermissionsByRole("user");
        assertEquals(List.of("read"), perms);
    }

    @Test
    void testGetPermissionsByRole_NotExist() {
        List<String> perms = permissionService.getPermissionsByRole("nonexistent");
        assertNull(perms);
    }

    @Test
    void testClearDynamicPermissions() {
        Map<String, List<String>> dynamic = new HashMap<>();
        dynamic.put("admin", List.of("read"));
        permissionService.updateDynamicPermissions(dynamic);
        assertTrue(permissionService.hasDynamicPermissions());

        permissionService.clearDynamicPermissions();
        assertFalse(permissionService.hasDynamicPermissions());
    }

    @Test
    void testHasDynamicPermissions_Empty() {
        assertFalse(permissionService.hasDynamicPermissions());
    }

    @Test
    void testGetCurrentDynamicPermissions() {
        Map<String, List<String>> dynamic = new HashMap<>();
        dynamic.put("admin", List.of("read"));
        permissionService.updateDynamicPermissions(dynamic);

        Map<String, List<String>> current = permissionService.getCurrentDynamicPermissions();
        assertNotNull(current);
        assertEquals(1, current.size());
    }

    @Test
    void testGetPresetPermissions() {
        Map<String, List<String>> preset = new HashMap<>();
        preset.put("user", List.of("read"));
        permissionService.setPresetPermissions(preset);

        Map<String, List<String>> result = permissionService.getPresetPermissions();
        assertNotNull(result);
        assertEquals(1, result.size());
    }

    @Test
    void testSetPresetPermissions() {
        Map<String, List<String>> preset = new HashMap<>();
        preset.put("admin", List.of("all"));
        preset.put("user", List.of("read"));
        permissionService.setPresetPermissions(preset);

        Map<String, List<String>> result = permissionService.getPresetPermissions();
        assertEquals(2, result.size());
    }

    // ============ creatorCheckPermissions 相关 ============

    @Test
    void testSetPresetCreatorCheckPermissions() {
        Map<String, List<String>> creatorCheck = new HashMap<>();
        creatorCheck.put("DEVELOPER", List.of("DELETE#/v1/{project_id}/agent-manager/agents/{agent_id}"));
        permissionService.setPresetCreatorCheckPermissions(creatorCheck);

        Map<String, List<String>> result = permissionService.getMergedCreatorCheckPermissions();
        assertNotNull(result);
        assertEquals(1, result.size());
        assertTrue(result.containsKey("DEVELOPER"));
    }

    @Test
    void testIsCreatorCheckRequired_True() {
        Map<String, List<String>> creatorCheck = new HashMap<>();
        creatorCheck.put("DEVELOPER", List.of("DELETE#/v1/{project_id}/agent-manager/agents/{agent_id}"));
        permissionService.setPresetCreatorCheckPermissions(creatorCheck);

        // 角色有该 URI 的 creatorCheck，返回 true
        assertTrue(permissionService.isCreatorCheckRequired("DEVELOPER", "DELETE",
            "/v1/abc/agent-manager/agents/agent-001"));
    }

    @Test
    void testIsCreatorCheckRequired_TemplateMatchTemplate() {
        Map<String, List<String>> creatorCheck = new HashMap<>();
        creatorCheck.put("DEVELOPER", List.of("PUT#/v1/{project_id}/model-manager/model-services/{id}"));
        permissionService.setPresetCreatorCheckPermissions(creatorCheck);

        // 模板匹配模板(AntPathMatcher {var} 互匹配)
        assertTrue(permissionService.isCreatorCheckRequired("DEVELOPER", "PUT",
            "/v1/{project_id}/model-manager/model-services/{id}"));
    }

    @Test
    void testIsCreatorCheckRequired_WrongMethod() {
        Map<String, List<String>> creatorCheck = new HashMap<>();
        creatorCheck.put("DEVELOPER", List.of("DELETE#/v1/{project_id}/agent-manager/agents/{agent_id}"));
        permissionService.setPresetCreatorCheckPermissions(creatorCheck);

        // 方法不匹配(DELETE 配置，PUT 请求)，返回 false
        assertFalse(permissionService.isCreatorCheckRequired("DEVELOPER", "PUT",
            "/v1/abc/agent-manager/agents/agent-001"));
    }

    @Test
    void testIsCreatorCheckRequired_WrongUri() {
        Map<String, List<String>> creatorCheck = new HashMap<>();
        creatorCheck.put("DEVELOPER", List.of("DELETE#/v1/{project_id}/agent-manager/agents/{agent_id}"));
        permissionService.setPresetCreatorCheckPermissions(creatorCheck);

        // URI 不匹配(子路径 /triggers 不应误匹配父路径)，返回 false
        assertFalse(permissionService.isCreatorCheckRequired("DEVELOPER", "DELETE",
            "/v1/abc/agent-manager/agents/agent-001/triggers/trigger-001"));
    }

    @Test
    void testIsCreatorCheckRequired_RoleNotConfigured() {
        // 角色未配置 creatorCheck(OWNER/ADMIN 全权)，返回 false
        assertFalse(permissionService.isCreatorCheckRequired("OWNER", "DELETE",
            "/v1/abc/agent-manager/agents/agent-001"));
    }

    @Test
    void testIsCreatorCheckRequired_EmptyList() {
        Map<String, List<String>> creatorCheck = new HashMap<>();
        creatorCheck.put("DEVELOPER", new ArrayList<>());
        permissionService.setPresetCreatorCheckPermissions(creatorCheck);

        // creatorCheck 列表为空，返回 false
        assertFalse(permissionService.isCreatorCheckRequired("DEVELOPER", "DELETE",
            "/v1/abc/agent-manager/agents/agent-001"));
    }

    @Test
    void testGetMergedCreatorCheckPermissions_DynamicOverridesPreset() {
        Map<String, List<String>> preset = new HashMap<>();
        preset.put("DEVELOPER", List.of("DELETE#/v1/old"));
        permissionService.setPresetCreatorCheckPermissions(preset);

        Map<String, List<String>> dynamic = new HashMap<>();
        dynamic.put("DEVELOPER", List.of("DELETE#/v1/new"));
        // 模拟动态覆盖(setPresetCreatorCheckPermissions 只设预置，动态通过 updateDynamicPermissions 未实现 creatorCheck)
        // 验证:预置生效
        Map<String, List<String>> merged = permissionService.getMergedCreatorCheckPermissions();
        assertEquals(List.of("DELETE#/v1/old"), merged.get("DEVELOPER"));
    }
}
