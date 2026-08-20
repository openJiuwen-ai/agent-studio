/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONWriter;
import com.openjiuwen.studio.agent.manager.constant.Constants;
import com.openjiuwen.studio.agent.manager.dto.WorkflowVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowValidationVO;
import com.openjiuwen.studio.agent.manager.service.nodes.ParamExtractionNodeService;
import com.openjiuwen.studio.agent.manager.utils.BaseTest;
import com.openjiuwen.studio.agent.manager.utils.TestUtil;

import lombok.extern.slf4j.Slf4j;

import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.annotation.Transactional;

/**
 * CustomModelManagementService测试类
 *
 */
@Transactional
@MockitoSettings(strictness = Strictness.LENIENT)
@Slf4j
public class ParamExtractionNodeServiceTest extends BaseTest {

    @Autowired
    ParamExtractionNodeService paramExtractionNodeService;

    @Autowired
    WorkflowValidationService workflowValidationService;

    @Test
    void testAdaptedParamExtractionNode() {
        String jsonContent = TestUtil.getStringFromFile("classpath:flow_dsl/param_extraction_dsl.json");
        WorkflowVO workflowVO = JSON.parseObject(jsonContent, WorkflowVO.class);
        WorkflowVO newWorkflow = paramExtractionNodeService.adaptParamExtractionNode(workflowVO);
        WorkflowValidationVO res = workflowValidationService.validate("1", "1", workflowVO);
        Assertions.assertFalse(res.isSuccess());
        String adaptedDsl = TestUtil.getStringFromFile("classpath:flow_dsl/param_extraction_ir.json");
        WorkflowVO adaptedWorkflow = JSON.parseObject(adaptedDsl, WorkflowVO.class);
        Assertions.assertEquals(JSON.toJSONString(adaptedWorkflow, JSONWriter.Feature.WriteMapNullValue).length(),
            JSON.toJSONString(newWorkflow, JSONWriter.Feature.WriteMapNullValue).length());
    }

    @Test
    void testExceptionBranchNode() {
        String jsonContent = TestUtil.getStringFromFile("classpath:flow_dsl/validate_exception_branch.json");
        WorkflowVO workflowVO = JSON.parseObject(jsonContent, WorkflowVO.class);
        WorkflowValidationVO res = workflowValidationService.validate("1", "1", workflowVO);
        Assertions.assertEquals(6, res.getErrors().size());
    }

    @Test
    void testExceptionNodeError() {
        String jsonContent = TestUtil.getStringFromFile("classpath:flow_dsl/validate_exception_node.json");
        WorkflowVO workflowVO = JSON.parseObject(jsonContent, WorkflowVO.class);
        WorkflowValidationVO res = workflowValidationService.validate(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID, workflowVO);
        Assertions.assertFalse(res.isSuccess());
    }
}
