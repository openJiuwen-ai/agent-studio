/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.utils.ResponseModel;
import com.openjiuwen.studio.agent.manager.a2a.A2aRegistrationService;
import com.openjiuwen.studio.agent.manager.entity.AgentRdcRegistrationEntity;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.enums.ParameterIn;

import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

/**
 * A2A 注册状态管理 Controller
 *
 * <p>FEAT-131: 注册状态查询 + 重试入口</p>
 */
@Slf4j
@RestController
@RequestMapping("/{project_id}/agent-manager")
public class A2aRegistrationController {

    @Autowired
    private A2aRegistrationService a2aRegistrationService;

    /**
     * 查询应用注册状态
     */
    @GetMapping("/agents/{agent_id}/registration")
    @Operation(summary = "查询 A2A 注册状态")
    public ResponseEntity<Map<String, Object>> getRegistrationStatus(
        @Parameter(in = ParameterIn.PATH, name = "project_id") @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.PATH, name = "agent_id") @PathVariable("agent_id") String agentId) {

        AgentRdcRegistrationEntity entity = a2aRegistrationService.getRegistration(agentId);
        Map<String, Object> result = new HashMap<>();
        if (entity == null) {
            result.put("status", "NONE");
            result.put("description", "未注册");
        } else {
            result.put("status", entity.getStatus().name());
            result.put("description", entity.getStatus().getDescription());
            result.put("instanceId", entity.getInstanceId());
            result.put("updatedAt", entity.getUpdatedOn());
        }
        return ResponseModel.success(result);
    }

    /**
     * 重试注册
     */
    @PostMapping("/agents/{agent_id}/registration/retry")
    @Operation(summary = "重试 A2A 注册")
    public ResponseEntity<Map<String, Object>> retryRegistration(
        @Parameter(in = ParameterIn.PATH, name = "project_id") @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.PATH, name = "agent_id") @PathVariable("agent_id") String agentId) {

        boolean success = a2aRegistrationService.retryRegistration(agentId);
        Map<String, Object> result = new HashMap<>();
        result.put("success", success);
        if (success) {
            result.put("message", "重试注册成功");
        } else {
            result.put("message", "重试注册失败，请稍后再试");
        }
        return ResponseModel.success(result);
    }

    /**
     * 重试注销
     */
    @PostMapping("/agents/{agent_id}/deregistration/retry")
    @Operation(summary = "重试 A2A 注销")
    public ResponseEntity<Map<String, Object>> retryDeregistration(
        @Parameter(in = ParameterIn.PATH, name = "project_id") @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.PATH, name = "agent_id") @PathVariable("agent_id") String agentId) {

        boolean success = a2aRegistrationService.retryDeregistration(agentId);
        Map<String, Object> result = new HashMap<>();
        result.put("success", success);
        if (success) {
            result.put("message", "重试注销成功");
        } else {
            result.put("message", "重试注销失败，请稍后再试");
        }
        return ResponseModel.success(result);
    }
}
