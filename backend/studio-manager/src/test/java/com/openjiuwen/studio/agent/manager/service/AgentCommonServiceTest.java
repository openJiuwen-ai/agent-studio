/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.manager.entity.HistoryReleaseVersionEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.mapper.HistoryReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

import java.util.List;

/**
 * AgentCommonServiceTest - 使用 MyBatis Mapper 进行单元测试
 * 不启动 Spring 上下文，纯 Mockito 单元测试
 */
public class AgentCommonServiceTest {

    @Mock
    private ReleaseVersionMapper releaseVersionMapper;

    @Mock
    private HistoryReleaseVersionMapper historyReleaseVersionMapper;

    @InjectMocks
    private AgentCommonService agentCommonService;

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
    }

    @Test
    public void test_softDeleteReleaseVersionByAppId_not_exist() throws Exception {
        ReleaseVersion releaseVersion = mock(ReleaseVersion.class);
        when(releaseVersion.getVersionId()).thenReturn("v1.0");
        when(releaseVersion.getAppId()).thenReturn("testAppId");

        when(releaseVersionMapper.selectByAppId("testAppId")).thenReturn(List.of(releaseVersion));
        when(releaseVersionMapper.deleteByAppId("testAppId")).thenReturn(0);
        // MyBatis 返回 null 而不是 Optional.empty()
        when(historyReleaseVersionMapper.findByAppIdAndVersionId("testAppId", "v1.0")).thenReturn(null);

        agentCommonService.softDeleteReleaseVersionByAppId("testAppId");

        verify(releaseVersionMapper, times(1)).selectByAppId("testAppId");
        verify(historyReleaseVersionMapper, times(1)).findByAppIdAndVersionId("testAppId", "v1.0");
        verify(historyReleaseVersionMapper, times(1)).insertBatch(anyList());
        verify(releaseVersionMapper, times(1)).deleteByAppId("testAppId");
    }

    @Test
    public void test_softDeleteReleaseVersionByAppId_exist() throws Exception {
        ReleaseVersion releaseVersion = mock(ReleaseVersion.class);
        when(releaseVersion.getVersionId()).thenReturn("v1.0");
        when(releaseVersion.getAppId()).thenReturn("testAppId");

        HistoryReleaseVersionEntity existingHistory = mock(HistoryReleaseVersionEntity.class);

        when(releaseVersionMapper.selectByAppId("testAppId")).thenReturn(List.of(releaseVersion));
        when(releaseVersionMapper.deleteByAppId("testAppId")).thenReturn(0);
        // 当记录已存在时，返回实体对象（不插入新记录）
        when(historyReleaseVersionMapper.findByAppIdAndVersionId("testAppId", "v1.0")).thenReturn(existingHistory);

        agentCommonService.softDeleteReleaseVersionByAppId("testAppId");

        verify(releaseVersionMapper, times(1)).selectByAppId("testAppId");
        verify(historyReleaseVersionMapper, times(1)).findByAppIdAndVersionId("testAppId", "v1.0");
        // 已存在时不插入
        verify(historyReleaseVersionMapper, times(0)).insertBatch(anyList());
        verify(releaseVersionMapper, times(1)).deleteByAppId("testAppId");
    }

    @Test
    public void test_softDeleteReleaseVersionById() throws Exception {
        ReleaseVersion releaseVersion = mock(ReleaseVersion.class);
        when(releaseVersion.getId()).thenReturn("id-123");
        when(releaseVersion.getVersionId()).thenReturn("v1.0");
        when(releaseVersion.getVersionName()).thenReturn("Version v1.0");
        when(releaseVersion.getAppId()).thenReturn("testAppId");
        when(releaseVersion.getAppType()).thenReturn("agent");
        when(releaseVersion.getStatus()).thenReturn("published");

        when(historyReleaseVersionMapper.findByAppIdAndVersionId("testAppId", "v1.0")).thenReturn(null);
        when(historyReleaseVersionMapper.insert(any(HistoryReleaseVersionEntity.class))).thenReturn(1);
        when(releaseVersionMapper.deleteByPrimaryKey("id-123")).thenReturn(1);

        agentCommonService.softDeleteReleaseVersionById(releaseVersion);

        verify(historyReleaseVersionMapper, times(1)).findByAppIdAndVersionId("testAppId", "v1.0");
        verify(historyReleaseVersionMapper, times(1)).insert(any(HistoryReleaseVersionEntity.class));
        verify(releaseVersionMapper, times(1)).deleteByPrimaryKey("id-123");
    }

    @Test
    public void test_softDeleteReleaseVersionById_historyExist() throws Exception {
        // 版本删除后又被导入重建（同appId+versionId），再次删除时历史表已有归档记录，应跳过插入避免唯一索引冲突
        ReleaseVersion releaseVersion = mock(ReleaseVersion.class);
        when(releaseVersion.getId()).thenReturn("id-123");
        when(releaseVersion.getVersionId()).thenReturn("v1.0");
        when(releaseVersion.getAppId()).thenReturn("testAppId");

        HistoryReleaseVersionEntity existingHistory = mock(HistoryReleaseVersionEntity.class);
        when(historyReleaseVersionMapper.findByAppIdAndVersionId("testAppId", "v1.0")).thenReturn(existingHistory);
        when(releaseVersionMapper.deleteByPrimaryKey("id-123")).thenReturn(1);

        agentCommonService.softDeleteReleaseVersionById(releaseVersion);

        verify(historyReleaseVersionMapper, times(1)).findByAppIdAndVersionId("testAppId", "v1.0");
        verify(historyReleaseVersionMapper, times(0)).insert(any(HistoryReleaseVersionEntity.class));
        verify(releaseVersionMapper, times(1)).deleteByPrimaryKey("id-123");
    }
}