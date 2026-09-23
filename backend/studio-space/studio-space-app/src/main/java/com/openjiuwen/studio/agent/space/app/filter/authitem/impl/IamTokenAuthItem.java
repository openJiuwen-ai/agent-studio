/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2021-2022. All rights reserved.
 */

package com.openjiuwen.studio.agent.space.app.filter.authitem.impl;


import com.alibaba.fastjson2.JSON;
import com.openjiuwen.studio.agent.space.api.auth.IamTokenAuth;
import com.openjiuwen.studio.agent.space.api.client.IamConsoleFeignClient;
import com.openjiuwen.studio.agent.space.app.filter.authitem.AuthItem;
import com.openjiuwen.studio.agent.space.app.model.iam.IamTokenValidateResp;
import com.openjiuwen.studio.agent.space.app.model.iam.Project;
import com.openjiuwen.studio.agent.space.app.model.iam.Token;
import com.openjiuwen.studio.agent.space.app.model.iam.User;
import com.openjiuwen.studio.agent.space.app.util.BuildResponseUtil;
import com.openjiuwen.studio.agent.space.common.constant.ContextConstants;
import com.openjiuwen.studio.agent.space.common.constant.HeaderConstant;
import com.openjiuwen.studio.agent.space.common.context.ContextUtils;
import com.openjiuwen.studio.agent.space.common.context.InvocationContext;
import com.openjiuwen.studio.agent.space.common.exception.AgentSpaceErrorCodes;
import com.openjiuwen.studio.agent.space.common.exception.AgentSpaceException;
import com.openjiuwen.studio.agent.space.common.utils.StringUtil;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.method.HandlerMethod;
import org.springframework.web.servlet.HandlerExecutionChain;
import org.springframework.web.servlet.mvc.method.annotation.RequestMappingHandlerMapping;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

/**
 * iam鉴权校验
 */
@Component
@Slf4j
public class IamTokenAuthItem implements AuthItem {

    @Autowired
    private RequestMappingHandlerMapping requestMappingHandlerMapping;

    @Autowired
    private IamConsoleFeignClient iamConsoleFeignClient;

    @Override
    public boolean isMatch(HttpServletRequest request, String urlPath) {
        log.info("Start IamAuthItem isMatch urlPath={}", urlPath);
        try {
            // 获取当前请求对应的处理器信息
            HandlerExecutionChain handler = requestMappingHandlerMapping.getHandler(request);

            if (handler != null && handler.getHandler() instanceof HandlerMethod handlerMethod) {
                Method method = handlerMethod.getMethod();
                return method.isAnnotationPresent(IamTokenAuth.class);
            } else {
                log.error("IamAuthItem::isMatch Not Found handlerMethod!");
                throw new AgentSpaceException(AgentSpaceErrorCodes.SYSTEM_ERROR);
            }
        } catch (Exception e) {
            log.error("IamAuthItem::isMatch Get IamTokenAuth Annotation failed!", e);
            throw new AgentSpaceException(AgentSpaceErrorCodes.SYSTEM_ERROR);
        }
    }

    @Override
    public boolean auth(HttpServletRequest request, HttpServletResponse response) {
        log.info("IamAuthItem Enter afterReceiveRequest.");
        try {
            String iamToken = request.getHeader(HeaderConstant.HEADER_X_AUTH_TOKEN);
            if (StringUtil.isEmptyString(iamToken)) {
                log.error("iamToken not found.");
                BuildResponseUtil.createOpenApiErrResponse(response, HttpServletResponse.SC_UNAUTHORIZED,
                        "iamToken not found.");
                return false;
            }
            Map<String, String> header = new HashMap<>();
            header.put(HeaderConstant.HEADER_X_AUTH_TOKEN, iamToken);
            header.put(HeaderConstant.HEADER_X_SUBJECT_TOKEN, iamToken);
            ResponseEntity<String> responseEntity = iamConsoleFeignClient.ValidateToken(header);
            int status = responseEntity.getStatusCode().value();
            if (status >= 300) {
                log.error("Verify iamToken failed. code: {}", status);
                BuildResponseUtil.createOpenApiErrResponse(response, HttpServletResponse.SC_UNAUTHORIZED,
                        "Verify iamToken failed.");
                return false;
            }
            IamTokenValidateResp iamTokenValidateResp = JSON.parseObject(responseEntity.getBody(), IamTokenValidateResp.class);
            Token token = iamTokenValidateResp.getToken();
            if (token == null) {
                log.error("Verify iamToken failed. token info is null.");
                BuildResponseUtil.createOpenApiErrResponse(response, HttpServletResponse.SC_UNAUTHORIZED,
                        "Verify iamToken failed.");
                return false;
            }
            Project project = token.getProject();
            if (project == null || project.getDomain() == null) {
                log.error("Verify iamToken failed. project info is null.");
                BuildResponseUtil.createOpenApiErrResponse(response, HttpServletResponse.SC_UNAUTHORIZED,
                        "Verify iamToken failed.");
                return false;
            }
            User tokenUser = token.getUser();

            InvocationContext context = ContextUtils.getInvocationContext();
            context.addContext(ContextConstants.AGENT_SPACE_USER_ID, tokenUser.getId());
            context.addContext(ContextConstants.AGENT_SPACE_USER_NAME, tokenUser.getName());
            context.addContext(ContextConstants.AGENT_SPACE_PROJECT_ID, project.getId());
            context.addContext(ContextConstants.AGENT_SPACE_DOMAIN_NAME, project.getDomain().getName());
            context.addContext(ContextConstants.AGENT_SPACE_DOMAIN_ID, project.getDomain().getId());
            context.addContext(ContextConstants.AGENT_SPACE_IAM_TOKEN, iamToken);
            if (token.getRoles() != null) {
                context.addContext(ContextConstants.AGENT_SPACE_USER_ROLES, JSON.toJSONString(token.getRoles()));
            }

            return true;
        } catch (Exception e) {
            log.error("IamAuthItem afterReceiveRequest, Exception Occurred: ", e);
            BuildResponseUtil.createOpenApiErrResponse(response, HttpServletResponse.SC_INTERNAL_SERVER_ERROR,
                    "Verify iamToken failed.");
            return false;
        }
    }

}
