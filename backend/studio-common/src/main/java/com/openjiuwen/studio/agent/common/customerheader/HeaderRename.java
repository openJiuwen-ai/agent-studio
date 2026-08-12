/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.customerheader;

import java.util.HashMap;
import java.util.Map;

/**
 * Header rename 工具类 — 按配置执行 cust-* → userId/token 的 rename
 *
 * <p>使用示例：
 * <pre>
 * Map<String, String> captured = Map.of("cust-userid", "123456", "cust-token", "xxx");
 * Map<String, String> renamed = HeaderRename.resolve(captured, profile);
 * // 结果: {"userId": "123456", "token": "xxx"}
 * </pre>
 */
public final class HeaderRename {

    private HeaderRename() {
    }

    /**
     * 按配置执行 header rename
     *
     * @param captured 请求中捕获的 cust-* headers
     * @param profile 配置
     * @return rename 后的 headers
     */
    public static Map<String, String> resolve(Map<String, String> captured, CustomerHeaderProfile profile) {
        if (!profile.isEnabled() || profile.getMappings().isEmpty()) {
            return Map.of();
        }

        Map<String, String> result = new HashMap<>();
        for (Map.Entry<String, String> mapping : profile.getMappings().entrySet()) {
            String fromKey = mapping.getKey();
            String toKey = mapping.getValue();

            // 尝试从 captured 中取值（大小写不敏感）
            String value = captured.get(fromKey);
            if (value == null) {
                value = captured.get(fromKey.toLowerCase());
            }

            if (value != null && !value.isEmpty()) {
                result.put(toKey, value);
            }
        }

        return result;
    }

    /**
     * 获取入站捕获白名单
     *
     * @param profile 配置
     * @return mappings 的所有 from_key
     */
    public static String[] getCaptureKeys(CustomerHeaderProfile profile) {
        if (!profile.isEnabled() || profile.getMappings().isEmpty()) {
            return new String[0];
        }
        return profile.getMappings().keySet().toArray(new String[0]);
    }
}
