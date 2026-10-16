/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import com.openjiuwen.studio.agent.common.utils.simple.SimpleAuthUtils;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.service.simple.IAuthService;
import com.openjiuwen.studio.agent.manager.service.simple.SimpleAuthService;

import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiResponse;
import io.swagger.annotations.ApiResponses;
import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.ApplicationContext;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

import javax.annotation.PostConstruct;

/**
 * AuthController
 *
 */
@RestController
@Validated
@Slf4j
public class AuthController {

    @Autowired
    private ApplicationContext applicationContext;

    private IAuthService authService;

    @Value("${poc.auth-type:normal}")
    private String authType;

    @PostConstruct
    private void init() {
        authService = applicationContext.getBean(SimpleAuthService.class);
    }

    @ApiOperation(value = "token校验", nickname = "validateToken", notes = "校验token并返回对应用户信息",
        response = SimpleUser.class, tags = {"validateToken"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "用户信息", response = SimpleUser.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 未鉴权", response = ErrorRsp.class)})
    @RequestMapping(value = "/v3/auth/tokens", produces = {"application/json"}, method = RequestMethod.GET)
    public ResponseEntity<SimpleUser> validateToken(
        @RequestHeader("X-Subject-Token") String token,
        @RequestParam(value = "nocatalog", required = false) String nocatalog) {
        return authService.validateToken(token);
    }

    /**
     * 获取 mock token
     *
     * @param userId String
     * @param projectId String
     * @return token
     */
    @ApiOperation(value = "get token", nickname = "getToken", notes = "获取 mock token", response = Map.class)
    @ApiResponses(value = {@ApiResponse(code = 200, message = "OK", response = String.class),
        @ApiResponse(code = 400, message = "Error response", response = ErrorRsp.class)})
    @RequestMapping(value = "/auth/token", method = RequestMethod.GET)
    public Map<String, String> getToken(@RequestParam(value = "user_id", required = false) String userId,
        @RequestParam(value = "project_id", required = false) String projectId) {
        String token = SimpleAuthUtils.getToken(userId, projectId);
        Map<String, String> tokenMap = new HashMap<>();
        tokenMap.put("auth_token", token);
        return tokenMap;
    }
}
