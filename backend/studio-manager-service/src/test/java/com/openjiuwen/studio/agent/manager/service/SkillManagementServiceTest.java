/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.bo.SkillDetails;
import com.openjiuwen.studio.agent.manager.dto.ExportStudioSkillResponseBody;
import com.openjiuwen.studio.agent.manager.dto.GetStudioSkillDetailsResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ImportStudioSkillResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListStudioSkillsQo;
import com.openjiuwen.studio.agent.manager.dto.ListStudioSkillsResponseBody;
import com.openjiuwen.studio.agent.manager.dto.StudioSkillInfo;
import com.openjiuwen.studio.agent.manager.entity.SkillEntity;
import com.openjiuwen.studio.agent.manager.entity.SkillVersionEntity;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.SkillMapper;
import com.openjiuwen.studio.agent.manager.mapper.SkillVersionMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.utils.MultipartFileToZipUtils;
import com.openjiuwen.studio.agent.manager.utils.ZipValidationUtils;


import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@ExtendWith(MockitoExtension.class)
public class SkillManagementServiceTest {
    @Mock
    private SkillMapper skillMapper;

    @Mock
    private SkillVersionMapper skillVersionMapper;

    @Mock
    private MgObsService mgObsService;

    @Mock
    private MappingMapper mappingMapper;

    @InjectMocks
    private SkillManagementService skillManagementService;


    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(skillManagementService, "mgObsService", mgObsService);
        ReflectionTestUtils.setField(skillManagementService, "skillMapper", skillMapper);
        ReflectionTestUtils.setField(skillManagementService, "mappingMapper", mappingMapper);
    }


    @Test
    void testDeleteSkill_Success() {
        String skillId = "test-skill-001";
        SkillVersionEntity skillVersionEntity = new SkillVersionEntity();
        skillVersionEntity.setObsPath("obs://test-bucket/test-folder/test-file.zip");

        try (MockedStatic<RequestContextUtils> mockedReq = mockStatic(RequestContextUtils.class)) {
            mockedReq.when(RequestContextUtils::getRequestUserDomainId).thenReturn("mock-domain-id");
            when(mappingMapper.updateValidByResourceId(anyString())).thenReturn(1);
            when(skillMapper.searchBySkillIdAndDomainId(skillId, RequestContextUtils.getRequestUserDomainId())).thenReturn(new SkillDetails());
            when(skillVersionMapper.searchBySkillId(skillId, 0, Integer.MAX_VALUE)).thenReturn(List.of(skillVersionEntity));
            skillManagementService.deleteStudioSkill(skillId, "mock-workspace-id", "mock-project-id");

            verify(skillMapper, times(1)).delete(skillId);
            verify(skillVersionMapper, times(1)).deleteBySkillId(skillId);
            verify(mgObsService, times(1)).deleteObsObjects(anyString());
        }
    }

    @Test
    void testDeleteSkill_Fail() {
        String skillId = "test-skill-001";

        try (MockedStatic<RequestContextUtils> mockedReq = mockStatic(RequestContextUtils.class)) {
            mockedReq.when(RequestContextUtils::getRequestUserDomainId).thenReturn("mock-domain-id");
            when(skillMapper.searchBySkillIdAndDomainId(skillId, RequestContextUtils.getRequestUserDomainId())).thenReturn(null);

            assertThrows(AgentStudioException.class, () -> {
                skillManagementService.deleteStudioSkill(skillId, "mock-workspace-id", "mock-project-id");
            });
        }
    }

    @Test
    void testDeleteSkill_NoVersion() {
        String skillId = "empty-skill";

        try (MockedStatic<RequestContextUtils> mockedReq = mockStatic(RequestContextUtils.class)) {
            mockedReq.when(RequestContextUtils::getRequestUserDomainId).thenReturn("mock-domain-id");
            when(mappingMapper.updateValidByResourceId(anyString())).thenReturn(1);
            when(skillMapper.searchBySkillIdAndDomainId(eq(skillId), anyString())).thenReturn(new SkillDetails());
            when (skillVersionMapper.searchBySkillId(eq(skillId), anyInt(), anyInt())).thenReturn(new ArrayList<>());
            skillManagementService.deleteStudioSkill(skillId, "mock-workspace-id", "mock-project-id");

            verify(skillMapper).delete(eq(skillId));
            verify(skillVersionMapper).deleteBySkillId(eq(skillId));
        }
    }

    @Test
    void testGetSkillDetails_Success() {
        String skillId = "skill-123";
        SkillDetails mockSkill = new SkillDetails();
        mockSkill.setSkillId(skillId);
        mockSkill.setDomainId("domain-001");
        mockSkill.setName("Test Skill");
        mockSkill.setIcon("icon-path.png");
        mockSkill.setStatus("developed");
        mockSkill.setSource("custom");
        mockSkill.setDescription("Description");
        mockSkill.setCreatorName("Admin");
        mockSkill.setCreatedAt(System.currentTimeMillis());
        mockSkill.setUpdatedAt(System.currentTimeMillis());
        mockSkill.setLatestVersion("v1.0.1");

        when(skillMapper.searchBySkillId(skillId)).thenReturn(mockSkill);

        lenient().when(mgObsService.getTemporaryGetRsp(anyBoolean(), anyString(), anyLong()))
            .thenReturn("https://obs-url.com");
        mockSkill.setObsPath("https://obs-url.com");

        GetStudioSkillDetailsResponseBody result = skillManagementService.showStudioSkillDetail(skillId, "mock"
            + "-workspace-id", "mock-project-id");
        assert result != null;
        assertEquals(skillId, result.getSkillInfo().getSkillId());
        assertEquals("Test Skill", result.getSkillInfo().getSkillName());
        assertEquals("DEVELOPED", result.getSkillInfo().getStatus().toString());
        verify(skillMapper, times(1)).searchBySkillId(skillId);
    }

    @Test
    void testListSkill_Success() {
        try (MockedStatic<RequestContextUtils> mockedReq = mockStatic(RequestContextUtils.class)) {
            mockedReq.when(RequestContextUtils::getRequestUserDomainId).thenReturn("TEST_DOMAIN_ID");
            ListStudioSkillsQo qo = new ListStudioSkillsQo();
            qo.setName("AI_");
            qo.setDescription("desc_");
            qo.setOffset(0);
            qo.setLimit(10);
            qo.setWorkspaceId("mock-workspace-id");
            qo.setTagId("tag-001");
            qo.setPublishedAsset(0);
            SkillDetails skill = new SkillDetails();
            skill.setSkillId("id-1");
            skill.setName("AI Skill");
            skill.setCreatedAt(System.currentTimeMillis());
            skill.setUpdatedAt(System.currentTimeMillis());
            skill.setStatus("deploy");

            List<SkillDetails> mockList = List.of(skill);

            when(skillMapper.search(any(SkillEntity.class), anyInt(), anyInt(), any(), anyString(),
                anyInt())).thenReturn(mockList);

            ListStudioSkillsResponseBody response = skillManagementService.listStudioSkills("mock-project-id", qo);

            assertNotNull(response);
            assertEquals(1, response.getItems().size());
            StudioSkillInfo item = response.getItems().get(0);
            assertEquals("id-1", item.getSkillId());
            verify(skillMapper, times(1)).search(any(SkillEntity.class), eq(0), eq(10), any(), anyString(), anyInt());
            qo.setPublishedAsset(1);
            response = skillManagementService.listStudioSkills("mock-project-id", qo);
        }
    }

    @Test
    void testImportStudioSkill_Success() throws Exception {
        MultipartFile mockMultipartFile = mock(MultipartFile.class);

        File tempZipFile = File.createTempFile("agentBuilder-import-test-", ".zip");
        java.nio.file.Files.write(tempZipFile.toPath(), "mock-zip-content".getBytes(StandardCharsets.UTF_8));
        tempZipFile.deleteOnExit();

        Map<String, Object> mockFrontmatter = new HashMap<>();
        mockFrontmatter.put("name", "Test Skill");
        mockFrontmatter.put("description", "A test skill");

        try (MockedStatic<MultipartFileToZipUtils> mockedZipUtil = mockStatic(MultipartFileToZipUtils.class);
            MockedStatic<ZipValidationUtils> mockedValidationUtil = mockStatic(ZipValidationUtils.class);
            MockedStatic<RequestContextUtils> mockedReq = mockStatic(RequestContextUtils.class)) {

            mockedReq.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-001");
            mockedReq.when(RequestContextUtils::getRequestUserId).thenReturn("user-001");
            mockedReq.when(RequestContextUtils::getRequestUserName).thenReturn("tester");
            mockedZipUtil.when(() -> MultipartFileToZipUtils.convertToZipFile(any())).thenReturn(tempZipFile);
            mockedValidationUtil.when(() -> ZipValidationUtils.validateZipFile(any(File.class))).thenAnswer(i -> null);
            mockedValidationUtil.when(ZipValidationUtils::getFrontmatter).thenReturn(mockFrontmatter);
            when(skillMapper.insert(any(SkillEntity.class))).thenReturn(1);
            when(skillVersionMapper.insert(any(SkillVersionEntity.class))).thenReturn(1);
            lenient().when(mgObsService.uploadObsFile(anyString(), any(InputStream.class), anyInt()))
                .thenReturn("user-001/skills/a1bc4d53-9965-4ff7-bb8c-4ec9649fc808/a1bc4d53-9965-4ff7-bb8c-4ec9649fc808/agentBuilder-import-test-13846229055125705451.zip");
            lenient().when(mgObsService.getTemporaryGetRsp(anyBoolean(), anyString(), anyLong()))
                .thenReturn("https://obs-url.com");
            ImportStudioSkillResponseBody result = skillManagementService.importStudioSkill("mock-workspace-id",
                "mock-project-id", mockMultipartFile);

            assertNotNull(result);
            assertEquals("Test Skill", result.getSkillName());
            assertEquals("A test skill", result.getDescription());
            assertNotNull(result.getVersionName());
            assertEquals(7, result.getVersionName().length());
            verify(skillMapper, times(1)).insert(any(SkillEntity.class));
            verify(skillVersionMapper, times(1)).insert(any(SkillVersionEntity.class));
        }
    }

    @Test
    void testImportStudioSkill_ValidationFailed() throws Exception {
        MultipartFile mockFile = mock(MultipartFile.class);

        // Mock ZipValidationUtils.validateZipFile 抛出异常
        try (MockedStatic<MultipartFileToZipUtils> mockedZipUtil = mockStatic(MultipartFileToZipUtils.class);
            MockedStatic<ZipValidationUtils> mockedValidationUtil = mockStatic(ZipValidationUtils.class)) {

            File mockZipFile = mock(File.class);
            lenient().when(mockZipFile.getName()).thenReturn("test-skill.zip");
            mockedZipUtil.when(() -> MultipartFileToZipUtils.convertToZipFile(any()))
                .thenReturn(mockZipFile);

            mockedValidationUtil.when(() -> ZipValidationUtils.validateZipFile(any(File.class)))
                .thenThrow(new AgentStudioException(StudioError.SKILL_MD_IS_MISSING));

            // 验证异常
            assertThrows(AgentStudioException.class, () -> {
                skillManagementService.importStudioSkill("mock-workspace-id", "mock-project-id", mockFile);
            });
        }
    }

    @Test
    void testImportStudioSkill_UploadToOBSFailed() throws Exception {
        MultipartFile mockFile = mock(MultipartFile.class);
        lenient().when(mockFile.getOriginalFilename()).thenReturn("test-skill.zip");
        lenient().when(mockFile.getInputStream()).thenReturn(mock(InputStream.class));

        try (MockedStatic<MultipartFileToZipUtils> mockedZipUtil = mockStatic(MultipartFileToZipUtils.class);
            MockedStatic<ZipValidationUtils> mockedValidationUtil = mockStatic(ZipValidationUtils.class);
            MockedStatic<RequestContextUtils> mockedReq = mockStatic(RequestContextUtils.class)) {

            // Mock RequestContextUtils
            mockedReq.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-001");
            mockedReq.when(RequestContextUtils::getRequestUserId).thenReturn("user-001");
            mockedReq.when(RequestContextUtils::getRequestUserName).thenReturn("tester");

            File mockZipFile = mock(File.class);
            lenient().when(mockZipFile.getName()).thenReturn("test-skill.zip");
            mockedZipUtil.when(() -> MultipartFileToZipUtils.convertToZipFile(any()))
                .thenReturn(mockZipFile);

            mockedValidationUtil.when(() -> ZipValidationUtils.validateZipFile(any(File.class))).thenAnswer(invocation -> {
                Map<String, Object> frontmatter = new HashMap<>();
                frontmatter.put("name", "Test Skill");
                frontmatter.put("description", "A test skill");
                return null;
            });

            // Mock ZipValidationUtils.getFrontmatter
            mockedValidationUtil.when(ZipValidationUtils::getFrontmatter).thenAnswer(invocation -> {
                Map<String, Object> frontmatter = new HashMap<>();
                frontmatter.put("name", "Test Skill");
                frontmatter.put("description", "A test skill");
                return frontmatter;
            });

            // 验证异常
            AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
                skillManagementService.importStudioSkill("mock-workspace-id", "mock-project-id", mockFile);
            });

            // 验证异常类型
            assertEquals(StudioError.UPLOAD_FILE_TO_OBS_FAILED, exception.getErrorCode());

            // 验证虽然OBS上传失败，但只有OBS服务被调用，数据库没有插入数据
            verify(mgObsService, times(0))
                .uploadObsFile(anyString(), any(InputStream.class), anyInt());
            verify(skillMapper, never()).insert(any(SkillEntity.class));
            verify(skillVersionMapper, never()).insert(any(SkillVersionEntity.class));
        }
    }

    @Test
    void testExportStudioSkill_Success() {
        String skillId = "test-skill-001";
        String skillVersion = "v1.0.0";

        // 创建模拟的 SkillDetails
        SkillDetails mockSkill = new SkillDetails();
        mockSkill.setSkillId(skillId);
        mockSkill.setDomainId("domain-001");
        mockSkill.setName("Test Skill");
        mockSkill.setStatus("developed");
        mockSkill.setLatestVersion(skillVersion);

        // 创建模拟的 SkillVersionEntity
        SkillVersionEntity mockVersion = new SkillVersionEntity();
        mockVersion.setId("version-001");
        mockVersion.setSkillId(skillId);
        mockVersion.setVersionName(skillVersion);
        mockVersion.setObsPath("obs://test-bucket/test-file.zip");

        when(skillMapper.searchBySkillId(skillId)).thenReturn(mockSkill);
        when(skillVersionMapper.searchByVersionId(skillVersion)).thenReturn(mockVersion);

        lenient().when(mgObsService.getTemporaryGetRsp(anyBoolean(), anyString(), anyLong()))
                .thenReturn("https://obs-temp-url.com/skill.zip");

        // 执行测试
        ExportStudioSkillResponseBody result = skillManagementService.exportStudioSkill(skillId,"mock-workspace-id", "mock-project-id");

        // 验证结果
        assertNotNull(result);
        assertEquals("https://obs-temp-url.com/skill.zip", result.getObsUrl());
        assertEquals("Test Skill", result.getSkillName());
        assertEquals("v1.0.0", result.getVersionName());
        assertEquals(skillId, result.getSkillId());

        // 验证方法调用
        verify(skillMapper, times(1)).searchBySkillId(skillId);
        verify(skillVersionMapper, times(1)).searchByVersionId(skillVersion);
        verify(mgObsService, times(1)).getTemporaryGetRsp(false, "obs://test-bucket/test-file.zip", 600L);
    }

    @Test
    void testExportStudioSkill_SkillIdEmpty() {
        // 验证空skillId
        assertThrows(AgentStudioException.class, () -> {
            skillManagementService.exportStudioSkill("", "mock-workspace-id", "mock-project-id");
        }, "skillId is empty");

        assertThrows(AgentStudioException.class, () -> {
            skillManagementService.exportStudioSkill(null, "mock-workspace-id", "mock-project-id");
        }, "skillId is empty");
    }

    @Test
    void testExportStudioSkill_SkillNotFound() {
        String skillId = "non-existent-skill";
        String skillVersion = "v1.0.0";

        when(skillMapper.searchBySkillId(skillId)).thenReturn(null);

        // 验证异常
        assertThrows(AgentStudioException.class, () -> {
            skillManagementService.exportStudioSkill(skillId,"mock-workspace-id", "mock-project-id");
        }, "skill not found");
    }

    @Test
    void testExportStudioSkill_VersionNotLatest() {
        String skillId = "test-skill-001";
        String skillVersion = "v1.0.0";
        String latestVersion = "v2.0.0";

        SkillDetails mockSkill = new SkillDetails();
        mockSkill.setSkillId(skillId);
        mockSkill.setName("Test Skill");
        mockSkill.setStatus("developed");
        mockSkill.setLatestVersion(latestVersion);

        when(skillMapper.searchBySkillId(skillId)).thenReturn(mockSkill);
        when(skillVersionMapper.searchByVersionId(latestVersion)).thenReturn(null);

        // 验证异常
        assertThrows(AgentStudioException.class, () -> {
            skillManagementService.exportStudioSkill(skillId,"mock-workspace-id", "mock-project-id");
        });
    }

    @Test
    void testExportStudioSkill_ObsUrlEmpty() {
        String skillId = "test-skill-001";
        String skillVersion = "v1.0.0";

        SkillDetails mockSkill = new SkillDetails();
        mockSkill.setSkillId(skillId);
        mockSkill.setName("Test Skill");
        mockSkill.setStatus("developed");
        mockSkill.setLatestVersion(skillVersion);

        SkillVersionEntity mockVersion = new SkillVersionEntity();
        mockVersion.setId("version-001");
        mockVersion.setSkillId(skillId);
        mockVersion.setVersionName(skillVersion);
        mockVersion.setObsPath(""); // 空的 OBS URL

        when(skillMapper.searchBySkillId(skillId)).thenReturn(mockSkill);
        when(skillVersionMapper.searchByVersionId(skillVersion)).thenReturn(mockVersion);

        // 验证异常
        assertThrows(AgentStudioException.class, () -> {
            skillManagementService.exportStudioSkill(skillId,"mock-workspace-id", "mock-project-id");
        }, "obsUrl is empty");
    }

    @Test
    void testExportStudioSkill_GetTempUrlFailed() {
        String skillId = "test-skill-001";
        String skillVersion = "v1.0.0";

        SkillDetails mockSkill = new SkillDetails();
        mockSkill.setSkillId(skillId);
        mockSkill.setName("Test Skill");
        mockSkill.setStatus("developed");
        mockSkill.setLatestVersion(skillVersion);

        SkillVersionEntity mockVersion = new SkillVersionEntity();
        mockVersion.setId("version-001");
        mockVersion.setSkillId(skillId);
        mockVersion.setVersionName(skillVersion);
        mockVersion.setObsPath("obs://test-bucket/test-file.zip");

        when(skillMapper.searchBySkillId(skillId)).thenReturn(mockSkill);
        when(skillVersionMapper.searchByVersionId(skillVersion)).thenReturn(mockVersion);

        // Mock mgObsService 返回 null
        lenient().doReturn(null)
            .when(mgObsService)
            .getTemporaryGetRsp(anyBoolean(), anyString(), anyLong());

        // 验证异常
        assertThrows(AgentStudioException.class, () -> {
            skillManagementService.exportStudioSkill(skillId,"mock-workspace-id", "mock-project-id");
        }, "failed to generate temporary URL");
    }


}
