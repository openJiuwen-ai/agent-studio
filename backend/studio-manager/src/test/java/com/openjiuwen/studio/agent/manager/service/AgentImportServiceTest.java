/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2018-2020. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Answers.RETURNS_DEEP_STUBS;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.RequestHeaderHolderUtils;
import com.openjiuwen.studio.agent.manager.constant.Constants;
import com.openjiuwen.studio.agent.manager.dto.ImportListInfo;
import com.openjiuwen.studio.agent.manager.dto.ImportRsp;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.utils.BaseTest;
import com.openjiuwen.studio.agent.manager.utils.TestUtil;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ImportExportStatusEnum;

import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Answers;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.MockitoAnnotations;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.context.jdbc.Sql;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;

@MockitoSettings(strictness = Strictness.LENIENT)
@Sql(scripts = {"classpath:sql/after_test_clear_db.sql"}, executionPhase = Sql.ExecutionPhase.AFTER_TEST_CLASS)
public class AgentImportServiceTest extends BaseTest {

    private MockMultipartFile testFile;

    private MockMultipartFile testSpaciousFile;

    private String importJson;

    private String importSpaciousJson;

    private static MockedStatic<RequestContextUtils> mockedStatic;

    private static MockedStatic<RequestHeaderHolderUtils> mockedHeaderStatic;

    private AutoCloseable mockitoCloseable;

    @Autowired
    private AgentImportService agentImportService;

    @MockitoBean
    private MgObsService obsService;

    @Mock(answer = RETURNS_DEEP_STUBS)
    private MgObsService mgObsService;

    @BeforeAll
    public static void init() {
        RequestContextUtils.setRequestAuthTokenAndProjectId(Constants.TEST_TOKEN, Constants.TEST_PROJECT_ID);
        mockedStatic = Mockito.mockStatic(RequestContextUtils.class);
        mockedHeaderStatic = Mockito.mockStatic(RequestHeaderHolderUtils.class);
        mockedHeaderStatic.when(RequestHeaderHolderUtils::getRequestLanguage).thenReturn("zh-cn");
        mockedStatic.when(RequestContextUtils::getRequestProjectId).thenReturn(Constants.TEST_PROJECT_ID);
        mockedStatic.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(Constants.TEST_WORKSPACE_ID);
        mockedStatic.when(RequestContextUtils::getRequestWorkspaceName).thenReturn(Constants.TEST_WORKSPACE_ID);
        mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn(Constants.TEST_TOKEN);
        mockedStatic.when(RequestContextUtils::getRequestUserDomainId).thenReturn(Constants.TEST_DOMAIN_ID);
        mockedStatic.when(RequestContextUtils::getRequestUserName).thenReturn(Constants.TEST_USER_NAME);
        mockedStatic.when(RequestContextUtils::getRequestUserId).thenReturn(Constants.TEST_USER_ID);
        mockedHeaderStatic.when(RequestHeaderHolderUtils::getRequestLanguage).thenReturn("zh-cn");

    }

    @AfterAll
    static void end() {
        mockedStatic.close();
        mockedHeaderStatic.close();
    }

    @AfterEach
    void tearDown() throws Exception {
        mockitoCloseable.close();
    }

    @BeforeEach
    void setUp() {
        mockitoCloseable = MockitoAnnotations.openMocks(this);

        try {
            importJson = TestUtil.getStringFromFile("classpath:import/agent_import_all.json");
            testFile = createTestFile();
            importSpaciousJson = TestUtil.getStringFromFile("classpath:import/spacious_import.json");
            testSpaciousFile = createSpaciousTestFile();
        } catch (Exception e) {
            throw new AgentStudioException("Failed to set up test data");
        }
    }

    private MockMultipartFile createTestFile() {
        return new MockMultipartFile("file", "test.jsonl", "text/plain", importJson.getBytes(StandardCharsets.UTF_8));
    }

    private MockMultipartFile createSpaciousTestFile() {
        return new MockMultipartFile("file", "test1.jsonl", "text/plain",
            importSpaciousJson.getBytes(StandardCharsets.UTF_8));
    }

    @Test
    void testCheckBeforeImportResolveFile() {
        assertThrows(AgentStudioException.class, () -> {
            MockMultipartFile file = new MockMultipartFile("file",  // 参数名
                "test.jsonl",  // 原始文件名
                "text/plain",  // MIME类型
                "{".getBytes(StandardCharsets.UTF_8)  // 文件内容
            );
            // run test
            agentImportService.checkBeforeImportFile(Constants.TEST_WORKSPACE_ID, Constants.TEST_PROJECT_ID, file);
        });
    }

    @Test
    void testCheckBeforeImport() {
        // When
        List<ImportListInfo> list = agentImportService.checkBeforeImportFile(Constants.TEST_WORKSPACE_ID,
            Constants.TEST_PROJECT_ID, testFile);
        // Then
        assertEquals(0, list.stream().filter(v -> StringUtils.isEmpty(v.getImportDescription())).count());
    }

    /**
     * 测试资源新增场景
     * @throws IOException
     */
    @Test
    @Sql(scripts = {"classpath:sql/after_test_clear_db.sql"}, executionPhase = Sql.ExecutionPhase.AFTER_TEST_METHOD)
    void testImportFileNewResource() {
        // When
        when(obsService.uploadObsFile(any(), any(), any(), any(), any())).thenReturn("test_dsl_path");

        ImportRsp importRsp = agentImportService.importFile(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID,
            testFile, null);
        // Then
        assertEquals(0, importRsp.getImportList()
            .stream()
            .filter(v -> Strings.CS.equals(v.getStatus(), ImportExportStatusEnum.FAILED.getCode()))
            .count());
    }

    @Test
    @Sql(scripts = {"classpath:sql/init_import_resource_db_pacious.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    @Sql(scripts = {"classpath:sql/after_test_clear_db.sql"}, executionPhase = Sql.ExecutionPhase.AFTER_TEST_METHOD)
    void testImportFileNewResourceSpacious() {
        // When
        when(obsService.uploadObsFile(any(), any(), any(), any(), any())).thenReturn("test_dsl_path");

        ImportRsp importRsp = agentImportService.importFile(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID,
            testSpaciousFile, "SPACIOUS");
        // Then
        assertEquals(2, importRsp.getImportList()
            .stream()
            .filter(v -> Strings.CS.equals(v.getStatus(), ImportExportStatusEnum.SUCCESS.getCode()))
            .count());
    }

    @Test
    @Sql(scripts = {"classpath:sql/init_import_resource_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    @Sql(scripts = {"classpath:sql/after_test_clear_db.sql"}, executionPhase = Sql.ExecutionPhase.AFTER_TEST_METHOD)
    void testImportFileSubController() {
        String importFile = TestUtil.getStringFromFile("classpath:import/sub_controller_import.json");
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            importFile.getBytes(StandardCharsets.UTF_8)  // 文件内容
        );

        // When
        when(obsService.uploadObsFile(any(), any(), any(), any(), any())).thenReturn("test_dsl_path");
        ImportRsp importRsp = agentImportService.importFile(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID,
            file, "SPACIOUS");
        // Then
        assertEquals(0, importRsp.getImportList()
            .stream()
            .filter(v -> Strings.CS.equals(v.getStatus(), ImportExportStatusEnum.FAILED.getCode()))
            .count());
    }

    /**
     * 测试资源更新/发布新版本场景
     * @throws IOException
     */
    @Test
    @Sql(scripts = {"classpath:sql/init_import_resource_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    @Sql(scripts = {"classpath:sql/after_test_clear_db.sql"}, executionPhase = Sql.ExecutionPhase.AFTER_TEST_METHOD)
    void testImportFileUpdateResource() {
        // When
        when(obsService.uploadObsFile(any(), any(), any(), any(), any())).thenReturn("test_dsl_path");
        ImportRsp importRsp = agentImportService.importFile(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID,
            testFile, null);
        // Then
        assertEquals(0, importRsp.getImportList()
            .stream()
            .filter(v -> Strings.CS.equals(v.getStatus(), ImportExportStatusEnum.FAILED.getCode()))
            .count());
    }

}
