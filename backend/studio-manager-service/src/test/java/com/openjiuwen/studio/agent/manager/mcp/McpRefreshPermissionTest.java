/* Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.mcp;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import org.junit.jupiter.api.Test;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.*;

class McpRefreshPermissionTest {
    @Test
    void refreshHasSamePermissionsAsModifyAndIsRegistered() throws Exception {
        try (InputStream input = getClass().getResourceAsStream("/role_permissions_interceptor.json")) {
            assertNotNull(input);
            JSONArray roles = JSON.parseArray(new String(input.readAllBytes(), StandardCharsets.UTF_8));
            boolean registered = false;
            boolean operatorChecked = false;
            for (int i = 0; i < roles.size(); i++) {
                JSONObject role = roles.getJSONObject(i);
                JSONArray permissions = role.getJSONArray("permissions");
                boolean refreshAllowed = permissions.contains("POST#/v1/{project_id}/mcp/service/tools/refresh/{id}");
                assertEquals(permissions.contains("PUT#/v1/{project_id}/mcp/service/modify"),
                    refreshAllowed, role.getString("roleName"));
                if ("REGISTERED_URIS".equals(role.getString("roleName"))) {
                    assertTrue(refreshAllowed);
                    registered = true;
                }
                if ("OPERATOR".equals(role.getString("roleName"))) {
                    assertFalse(refreshAllowed);
                    operatorChecked = true;
                }
            }
            assertTrue(registered);
            assertTrue(operatorChecked);
        }
    }
}
