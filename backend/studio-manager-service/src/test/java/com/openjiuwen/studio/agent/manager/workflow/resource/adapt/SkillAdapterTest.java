/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.workflow.resource.adapt;

import static com.openjiuwen.studio.agent.manager.workflow.resource.adapt.ResourceAdapter.getParentIdMap;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.RETURNS_DEEP_STUBS;
import static org.mockito.Mockito.any;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.bo.SkillDetails;
import com.openjiuwen.studio.agent.manager.entity.SkillEntity;
import com.openjiuwen.studio.agent.manager.mapper.SkillMapper;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ExportResourceUnit;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ExportResp;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ImportCheckResult;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ImportInfo;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ImportResourceResult;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Answers;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.MockitoAnnotations;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@MockitoSettings(strictness = Strictness.LENIENT)
class SkillAdapterTest {
    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private SkillMapper skillMapper;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private I18nUtil i18nUtil;

    @InjectMocks
    private SkillAdapter skillAdapter;

    private AutoCloseable mockitoCloseable;

    @BeforeEach
    void setUp() throws Exception {
        mockitoCloseable = MockitoAnnotations.openMocks(this);
    }

    @AfterEach
    void tearDown() throws Exception {
        mockitoCloseable.close();
    }

    @Test
    void test_parseExport_should_return_not_null() throws Exception {
        try (MockedStatic<ResourceAdapter> mockedStaticResourceAdapter = mockStatic(ResourceAdapter.class,
            RETURNS_DEEP_STUBS);
             MockedStatic<RequestContextUtils> mockedCtx = mockStatic(RequestContextUtils.class)) {
            // parseExport 内部 RequestContextUtils.getRequestUserDomainId() 取 domain 隔离（issue #1734）
            mockedCtx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("test-domain");
            // Given
            Map<String, List<String>> parentIdMap = new HashMap<>();
            List<String> list = new ArrayList<>();
            list.add("not_empty");
            parentIdMap.put("not_empty", list);
            mockedStaticResourceAdapter.when(() -> getParentIdMap(anyList())).thenReturn(parentIdMap);

            when(i18nUtil.getMessage(eq(StudioError.EXPORT_RESOURCE_NOT_EXISTS), anyString())).thenReturn("not_empty");

            List<SkillDetails> skillDetailsList = new ArrayList<>();
            SkillDetails skillDetails = new SkillDetails();
            skillDetailsList.add(skillDetails);
            when(skillMapper.searchBySkillIds(anyList(), eq("test-domain"))).thenReturn(skillDetailsList);

            List<ExportResourceUnit> exportResources = new ArrayList<>();
            ExportResourceUnit exportResourceUnit = new ExportResourceUnit();
            exportResources.add(exportResourceUnit);

            // When
            ExportResp result = skillAdapter.parseExport(exportResources);

            // Then
            assertNotNull(result);
        }
    }

    @Test
    void test_checkBeforeImport_should_not_throw_exception() throws Exception {
        assertDoesNotThrow(() -> {
            try (MockedStatic<JsonUtils> mockedStaticJsonUtils = mockStatic(JsonUtils.class, RETURNS_DEEP_STUBS)) {
                // Given
                SkillEntity skill = new SkillEntity();
                mockedStaticJsonUtils.when(() -> JsonUtils.objectToClassType(any(Object.class), eq(SkillEntity.class)))
                    .thenReturn(skill);

                SkillDetails skillDetails = new SkillDetails();
                when(skillMapper.search(any(SkillEntity.class), eq(0), eq(1), anyString(),anyString(),eq(0)).get(eq(0))).thenReturn(skillDetails);

                ImportCheckResult importCheckResult = new ImportCheckResult();

                ImportInfo importInfo = new ImportInfo();
                importInfo.setTargetDomainId("not_empty");
                Object metadata = new Object();
                importInfo.setMetadata(metadata);

                // When
                skillAdapter.checkBeforeImport(importCheckResult, importInfo);
            }
        });
    }

    @Test
    void test_parseImport_should_not_throw_exception() throws Exception {
        assertDoesNotThrow(() -> {
            try (MockedStatic<JsonUtils> mockedStaticJsonUtils = mockStatic(JsonUtils.class, RETURNS_DEEP_STUBS)) {
                // Given
                SkillEntity skill = new SkillEntity();
                mockedStaticJsonUtils.when(() -> JsonUtils.objectToClassType(any(Object.class), eq(SkillEntity.class)))
                    .thenReturn(skill);

                SkillDetails skillDetails = new SkillDetails();
                when(skillMapper.search(any(SkillEntity.class), eq(0), eq(1), anyString(),anyString(),eq(0)).get(eq(0))).thenReturn(skillDetails);

                ImportResourceResult importResourceResult = new ImportResourceResult();

                ImportInfo importInfo = new ImportInfo();
                importInfo.setTargetDomainId("not_empty");
                importInfo.setCreatorId("not_empty");
                Object metadata = new Object();
                importInfo.setMetadata(metadata);

                // When
                skillAdapter.parseImport(importResourceResult, importInfo);
            }
        });
    }

    @Test
    void test_checkBeforeImport_should_not_throw_exception_when_ResourceNotMatch() throws Exception {
        assertDoesNotThrow(() -> {
            try (MockedStatic<JsonUtils> mockedStaticJsonUtils = mockStatic(JsonUtils.class, RETURNS_DEEP_STUBS)) {
                // Given
                SkillEntity skill = new SkillEntity();
                mockedStaticJsonUtils.when(() -> JsonUtils.objectToClassType(any(Object.class), eq(SkillEntity.class)))
                    .thenReturn(skill);

                when(skillMapper.search(any(SkillEntity.class), eq(0), eq(1), anyString(), anyString(),
                    eq(0))).thenReturn(new ArrayList<>());

                ImportCheckResult importCheckResult = new ImportCheckResult();

                ImportInfo importInfo = new ImportInfo();
                importInfo.setTargetDomainId("not_empty");
                Object metadata = new Object();
                importInfo.setMetadata(metadata);

                // When
                skillAdapter.checkBeforeImport(importCheckResult, importInfo);
            }
        });
    }

}
