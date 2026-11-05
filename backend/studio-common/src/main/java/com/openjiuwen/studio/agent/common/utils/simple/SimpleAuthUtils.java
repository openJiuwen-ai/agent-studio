/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.utils.simple;


import com.openjiuwen.studio.agent.common.constant.SimpleConstants;
import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.service.simple.PocConfig;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;

import jakarta.servlet.http.HttpServletRequest;

import org.apache.commons.collections4.MapUtils;
import org.apache.commons.lang3.ArrayUtils;
import org.apache.commons.lang3.StringUtils;

import java.util.Map;

public class SimpleAuthUtils {
    /**
     * token转用户信息
     *
     * @param token token
     * @return
     */
    public static SimpleUser tokenToUser(String token) {
        if (StringUtils.isEmpty(token)) {
            throw new AgentStudioException(StudioError.POC_AUTH_FAILED);
        }

        String[] ary = token.split("\\|");
        if (ArrayUtils.isEmpty(ary)) {
            throw new AgentStudioException(StudioError.POC_AUTH_FAILED);
        }
        SimpleUser user = null;
        String userId = ary[0];
        if (!StringUtils.isEmpty(userId)) {
            user = new SimpleUser();
            PocConfig pocConfig = SpringBeanUtils.getBean(PocConfig.class);
            user.setDomainId(pocConfig.getDefaultDomain());
            user.setUserId(userId);
            user.setUserName(userId);
            user.setToken(token);
        } else {
            // userId为空则认为user信息无效，返回空
            throw new AgentStudioException(StudioError.POC_AUTH_FAILED);
        }

        if (ary.length > 1) {
            String projectId = ary[1];
            if (!StringUtils.isEmpty(projectId)) {
                user.setProjectId(projectId);
            }
        } else {
            throw new AgentStudioException(StudioError.POC_AUTH_FAILED);
        }
        return user;
    }

    /**
     * 用户信息转成token
     *
     * @param httpRequest
     * @return
     */
    public static String paramToToken(HttpServletRequest httpRequest, String existToken) {
        // 获取userId忽略大小写
        Map<String, String[]> params = httpRequest.getParameterMap();
        String userId = "";
        String projectId = "";
        if (!MapUtils.isEmpty(params)) {
            for (Map.Entry<String, String[]> entry : params.entrySet()) {
                if (entry.getKey().equalsIgnoreCase(SimpleConstants.UserInfo.USER_FIELD)) {
                    if (entry.getValue() != null && entry.getValue().length > 0) {
                        userId = entry.getValue()[0];
                    }
                }
                if (entry.getKey().equalsIgnoreCase(SimpleConstants.UserInfo.PROJECT_FIELD)) {
                    if (entry.getValue() != null && entry.getValue().length > 0) {
                        projectId = entry.getValue()[0];
                    }
                }
            }
        }
        if (StringUtils.isEmpty(userId)) {
            userId = httpRequest.getHeader(SimpleConstants.UserInfo.USER_FIELD);
        }
        if (StringUtils.isEmpty(projectId)) {
            projectId = httpRequest.getHeader(SimpleConstants.UserInfo.PROJECT_FIELD);
        }

        String token = "";
        PocConfig pocConfig = SpringBeanUtils.getBean(PocConfig.class);
        // userId和projectId都为空则认为没有传输登陆信息,使用默认登录信息
        if (StringUtils.isEmpty(userId) && StringUtils.isEmpty(projectId)) {
            // 如果没有历史token才用默认值
            if (StringUtils.isEmpty(existToken)) {
                userId = pocConfig.getDefaultUserId();
                projectId = pocConfig.getDefaultProject();
            } else {
                // 否则返回空
                return token;
            }
        }
        return getToken(userId, projectId);
    }

    /**
     * mock token构造
     *
     * @param userId String
     * @param projectId String
     * @return token
     */
    public static String getToken(String userId, String projectId) {
        PocConfig pocConfig = SpringBeanUtils.getBean(PocConfig.class);
        return String.format("%s|%s", StringUtils.isEmpty(userId) ? "" : userId,
            StringUtils.isEmpty(projectId) ? pocConfig.getDefaultProject() : projectId);
    }
}
