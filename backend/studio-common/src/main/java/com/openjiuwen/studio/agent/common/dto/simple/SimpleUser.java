/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.dto.simple;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SimpleUser {
    private String userId;

    private String token;

    private String userName;

    private String projectId;

    // 默认0，可能根据业务修改
    private String domainId = "0";

    // 默认0，可根据业务修改
    private String domainName = "0";
}
