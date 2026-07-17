/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.ros;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.constant.Constants;
import com.openjiuwen.studio.agent.manager.dto.NotifyReq;
import com.openjiuwen.studio.agent.manager.dto.NotifyResp;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.ros.ResourceCleanMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.ros.service.CleanResourceServiceImpl;
import com.openjiuwen.studio.agent.manager.utils.BaseTest;

import lombok.SneakyThrows;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.transaction.annotation.Transactional;

import java.util.Arrays;

@Slf4j
public class CleanResourceServiceTest extends BaseTest {

    @Autowired
    private CleanResourceServiceImpl cleanResourceService;

    @Autowired
    private ResourceCleanMapper resourceCleanMapper;

    @MockitoBean
    private MgObsService obsService;

    @Autowired
    private WorkflowMapper workflowMapper;

    private static MockedStatic<RequestContextUtils> mockedStatic;

    @Autowired
    private ResourceCleanMaster resourceCleanMaster;

    @BeforeAll
    public static void init() {
        mockedStatic = Mockito.mockStatic(RequestContextUtils.class);
        mockedStatic.when(RequestContextUtils::getRequestProjectId).thenReturn("fake_user_project_id");
        mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn("fake_user_token");
        mockedStatic.when(RequestContextUtils::getRequestUserId).thenReturn("fake_user_id");
    }

    @Test
    @SneakyThrows
    public void testCleanNotify_Success() {
        mockedStatic.when(RequestContextUtils::getRequestUserDomainName).thenReturn("fakeOpDomainName");
        // Arrange
        NotifyReq body = new NotifyReq();
        body.setDomainId(Constants.TEST_DOMAIN_ID);
        body.setTaskId(Constants.TEST_TASK_ID);
        NotifyResp response = cleanResourceService.cleanNotify(RosConstants.MODULE_NAME, body);
        assertEquals(CommonConstant.SUCCESS, response.getResMsg());
        assertEquals(CommonConstant.SUCCESS, response.getResult());
    }

    @Test
    @SneakyThrows
    public void testCleanNotify_notopsvc_failed() {
        mockedStatic.when(RequestContextUtils::getRequestUserDomainName).thenReturn("fakeOpDomainName1");
        // Arrange
        NotifyReq body = new NotifyReq();
        body.setDomainId(Constants.TEST_DOMAIN_ID);
        body.setTaskId(Constants.TEST_TASK_ID);
        assertThrows(AgentStudioException.class, () -> {
            cleanResourceService.cleanNotify(RosConstants.MODULE_NAME, body);
        });
    }

    @Test
    @Sql(scripts = {"classpath:sql/ros/resource_clean_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    @Transactional
    public void testClean_outoftime_failed() {
        when(obsService.deleteByPrefix(any())).thenReturn(true);
        ReflectionTestUtils.setField(resourceCleanMaster, "timeWindow", Arrays.asList(0, 0));
        NotifyReq req = new NotifyReq();
        req.setDomainId(Constants.TEST_DOMAIN_ID);
        req.setTaskId(Constants.TEST_TASK_ID);
        NotifyResp notifyResp = resourceCleanMaster.clean(req);
        log.info("errorInfo:{}", notifyResp.getResult());
        assertTrue(StringUtils.isNotEmpty(notifyResp.getResult()));
    }

    @AfterAll
    static void end() {
        mockedStatic.close();
    }
}
