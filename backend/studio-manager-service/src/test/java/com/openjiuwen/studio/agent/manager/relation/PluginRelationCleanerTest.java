/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.relation;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.RETURNS_DEEP_STUBS;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.mapper.ShareResourceMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareScopeMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolCredentialMapper;
import com.openjiuwen.studio.agent.manager.mapper.ros.ResourceCleanMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;

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
import java.util.List;

@MockitoSettings(strictness = Strictness.LENIENT)
class PluginRelationCleanerTest {
    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private MgObsService obsService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private ResourceCleanMapper dataCleanMapper;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private ShareScopeMapper shareScopeMapper;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private ShareResourceMapper shareResourceMapper;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private ToolCredentialMapper toolCredentialMapper;

    @InjectMocks
    private com.openjiuwen.studio.agent.manager.ros.relation.PluginRelationCleaner pluginRelationCleaner;

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
    void test_clean_should_not_throw_exception() throws Exception {
        assertDoesNotThrow(() -> {
            try (MockedStatic<RequestContextUtils> mockedStaticRequestContextUtils = mockStatic(
                RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
                // Given
                mockedStaticRequestContextUtils.when(() -> RequestContextUtils.getRequestAuthToken())
                    .thenReturn("not_empty");
                mockedStaticRequestContextUtils.when(() -> RequestContextUtils.getRequestProjectId())
                    .thenReturn("not_empty");

                when(shareResourceMapper.deleteByPrimaryKey(anyString())).thenReturn(0);
                when(shareScopeMapper.deleteByResourceId(anyString())).thenReturn(0);

                when(obsService.deleteByPrefix(anyString())).thenReturn(true);

                List<String> ids = new ArrayList<>();
                ids.add("not_empty");

                // When
                pluginRelationCleaner.clean(ids, "not_empty");
            }
        });
    }

    @Test
    void test_clean_should_not_throw_exception2() throws Exception {
        assertDoesNotThrow(() -> {
            try (MockedStatic<RequestContextUtils> mockedStaticRequestContextUtils = mockStatic(
                RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
                // Given
                mockedStaticRequestContextUtils.when(() -> RequestContextUtils.getRequestAuthToken()).thenReturn("");
                mockedStaticRequestContextUtils.when(() -> RequestContextUtils.getRequestProjectId()).thenReturn("");

                when(obsService.deleteByPrefix(anyString())).thenReturn(true);

                List<String> ids = new ArrayList<>();
                ids.add("");

                // When
                pluginRelationCleaner.clean(ids, "");
            }
        });
    }

    @Test
    void test_clean_should_not_throw_exception4() throws Exception {
        assertDoesNotThrow(() -> {
            try (MockedStatic<RequestContextUtils> mockedStaticRequestContextUtils = mockStatic(
                RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
                // Given
                mockedStaticRequestContextUtils.when(() -> RequestContextUtils.getRequestAuthToken()).thenReturn(null);
                mockedStaticRequestContextUtils.when(() -> RequestContextUtils.getRequestProjectId()).thenReturn(null);

                when(obsService.deleteByPrefix(anyString())).thenReturn(false);

                // When
                pluginRelationCleaner.clean(null, null);
            }
        });
    }
}
