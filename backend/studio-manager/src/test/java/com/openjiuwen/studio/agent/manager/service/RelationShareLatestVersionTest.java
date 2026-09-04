/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static com.openjiuwen.studio.agent.manager.constant.Constants.TEST_PROJECT_ID;
import static com.openjiuwen.studio.agent.manager.constant.Constants.TEST_WORKSPACE_ID;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.Constants;
import com.openjiuwen.studio.agent.manager.dto.ListAppRelationsQo;
import com.openjiuwen.studio.agent.manager.dto.Relation;
import com.openjiuwen.studio.agent.manager.dto.RelationList;
import com.openjiuwen.studio.agent.manager.utils.BaseTest;
import com.openjiuwen.studio.agent.manager.utils.CommonUtil;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.MockitoAnnotations;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.transaction.annotation.Transactional;

import java.io.IOException;

/**
 * 共享插件铃铛"最新版本"回归测试（对应《插件版本更新问题分析》v2 第 6.3 节验收标准）：
 * 1. 共享快照含已软删/不存在版本时，铃铛只提示真实存在的共享最新版本；
 * 2. 当前版本已高于共享最新版本时，不提示降级；
 * 3. 共享快照全部失效时回退到真实最新版本（点击更新不报版本不存在）；
 * 4. 非共享插件的最大版本为软删行时，铃铛不显示软删版本。
 */
@Transactional
public class RelationShareLatestVersionTest extends BaseTest {
    private static MockedStatic<RequestContextUtils> mockedStatic;

    private static MockedStatic<CommonUtil> commonUtilMockedStatic;

    @Autowired
    private RelationManagementService relationManagementService;

    private AutoCloseable mockitoCloseable;

    @BeforeAll
    static void init() {
        mockedStatic = Mockito.mockStatic(RequestContextUtils.class);
        commonUtilMockedStatic = Mockito.mockStatic(CommonUtil.class);
        mockedStatic.when(RequestContextUtils::getRequestProjectId).thenReturn(Constants.TEST_PROJECT_ID);
        mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn(Constants.TEST_TOKEN);
        mockedStatic.when(RequestContextUtils::getRequestUserName).thenReturn(Constants.TEST_USER_NAME);
        mockedStatic.when(RequestContextUtils::getRequestUserId).thenReturn(Constants.TEST_CREATOR_ID);
        mockedStatic.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(TEST_WORKSPACE_ID);
        commonUtilMockedStatic.when(CommonUtil::getTenantId).thenReturn("system");
        commonUtilMockedStatic.when(CommonUtil::getDeptCode).thenReturn("system");
    }

    @AfterAll
    static void end() {
        mockedStatic.close();
        commonUtilMockedStatic.close();
    }

    @BeforeEach
    void setUp() throws IOException {
        mockitoCloseable = MockitoAnnotations.openMocks(this);
        when(RequestContextUtils.getRequestUserId()).thenReturn(Constants.TEST_CREATOR_ID);
    }

    @AfterEach
    void tearDown() throws Exception {
        mockitoCloseable.close();
    }

    private Relation findRelation(String appId, String resourceId) {
        ListAppRelationsQo qo = new ListAppRelationsQo();
        qo.setShowlatest(true);
        qo.setWorkspaceId(TEST_WORKSPACE_ID);
        RelationList relationList = relationManagementService.listAppRelations(TEST_PROJECT_ID, appId, qo);
        Assertions.assertNotNull(relationList);
        return relationList.getRelations().stream()
            .filter(relation -> resourceId.equals(relation.getResourceId()))
            .findFirst()
            .orElse(null);
    }

    /**
     * 验收1：共享快照含软删版本3000与有效版本1000，当前版本1000。
     * 铃铛最新版本应为真实存在的1000，而不是软删的3000（修复前会显示3000）。
     */
    @Test
    @Sql(scripts = {"classpath:sql/relation_share_latest_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testShareLatestVersionShouldSkipDeletedSnapshotVersion() {
        Relation relation = findRelation("sv_agent_1a", "sv_plugin_1");
        Assertions.assertNotNull(relation);
        Assertions.assertEquals("1770000000000", relation.getResourceVersion());
        Assertions.assertEquals("1770000000000", relation.getResourceLatestVersion());
        Assertions.assertEquals("v1", relation.getResourceLatestVersionName());
    }

    /**
     * 验收1：当前版本1760000000000低于共享有效最新版本1770000000000，应提示升级到真实存在的共享版本。
     */
    @Test
    @Sql(scripts = {"classpath:sql/relation_share_latest_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testShareLatestVersionShouldUpgradeToExistingShareVersion() {
        Relation relation = findRelation("sv_agent_1b", "sv_plugin_1");
        Assertions.assertNotNull(relation);
        Assertions.assertEquals("1760000000000", relation.getResourceVersion());
        Assertions.assertEquals("1770000000000", relation.getResourceLatestVersion());
    }

    /**
     * 验收2：当前版本1785000000000已高于共享有效最新版本1770000000000，不应被共享快照覆盖（不诱导降级），
     * 最新版本保持为真实最新版1785000000000（当前=最新，铃铛不出现）。
     */
    @Test
    @Sql(scripts = {"classpath:sql/relation_share_latest_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testShareSnapshotShouldNotOverrideWhenCurrentIsNewer() {
        Relation relation = findRelation("sv_agent_1c", "sv_plugin_1");
        Assertions.assertNotNull(relation);
        Assertions.assertEquals("1785000000000", relation.getResourceVersion());
        Assertions.assertEquals("1785000000000", relation.getResourceLatestVersion());
    }

    /**
     * 验收3（客户现场场景）：共享快照只含从未存在的版本1772000000000（当前版本1785500000000）。
     * 快照整体失效应回退到真实最新版本1786000000000，铃铛提示1786000000000而非1772000000000（点击更新不再报02401042）。
     */
    @Test
    @Sql(scripts = {"classpath:sql/relation_share_latest_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testAllInvalidShareSnapshotShouldFallBackToLiveLatest() {
        Relation relation = findRelation("sv_agent_2a", "sv_plugin_2");
        Assertions.assertNotNull(relation);
        Assertions.assertEquals("1785500000000", relation.getResourceVersion());
        Assertions.assertEquals("1786000000000", relation.getResourceLatestVersion());
        Assertions.assertEquals("v6_aug2", relation.getResourceLatestVersionName());
    }

    /**
     * 验收4：非共享插件最大版本号1789000000000为软删行，铃铛最新版本应为真实存在的1780000000000。
     */
    @Test
    @Sql(scripts = {"classpath:sql/relation_share_latest_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testLatestVersionShouldExcludeSoftDeletedForDirectReference() {
        Relation relation = findRelation("sv_agent_3a", "sv_plugin_3");
        Assertions.assertNotNull(relation);
        Assertions.assertEquals("1780000000000", relation.getResourceVersion());
        Assertions.assertEquals("1780000000000", relation.getResourceLatestVersion());
    }
}
