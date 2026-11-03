/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.simple;

import static com.openjiuwen.studio.agent.common.enums.StudioError.POC_AUTH_FAILED;

import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.simple.SimpleAuthUtils;

import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationContext;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;

@Component
@Slf4j
public class SimpleAuthService implements IAuthService {

    private static final String SUCCESS = "SUCCESS";

    @Autowired
    private ApplicationContext applicationContext;

    private String X_SUBJECT_TOKEN = "X-Subject-Token";

    /**
     * token校验
     *
     * @param token 待校验token
     * @return
     */
    public ResponseEntity<SimpleUser> validateToken(String token) {
        SimpleUser user = SimpleAuthUtils.tokenToUser(token);
        if (user != null) {
            return buildResp(user, token);
        } else {
            throw new AgentStudioException(POC_AUTH_FAILED, "token missing or not valid.");
        }
    }

    private ResponseEntity<SimpleUser> buildResp(SimpleUser simpleUser,
        String tokenStr) {
        return ResponseEntity.ok().header(X_SUBJECT_TOKEN, tokenStr).body(simpleUser);
    }
}
