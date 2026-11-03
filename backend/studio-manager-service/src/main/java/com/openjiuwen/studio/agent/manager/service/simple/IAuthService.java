/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.simple;

import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;

import org.springframework.http.ResponseEntity;

public interface IAuthService {

    ResponseEntity<SimpleUser> validateToken(String token);
}
