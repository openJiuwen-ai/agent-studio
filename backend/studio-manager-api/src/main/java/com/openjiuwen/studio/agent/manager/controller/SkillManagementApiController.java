/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.ExportStudioSkillResponseBody;
import com.openjiuwen.studio.agent.manager.dto.GetStudioSkillDetailsResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ImportStudioSkillResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListStudioSkillsQo;
import com.openjiuwen.studio.agent.manager.dto.ListStudioSkillsResponseBody;
import com.openjiuwen.studio.agent.manager.service.ISkillManagementService;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import java.io.InputStream;

/**
 * SkillManagement controller
 */
@RestController

public class SkillManagementApiController implements SkillManagementApi {
    private static final Logger log = LoggerFactory.getLogger(SkillManagementApiController.class);

    @Autowired
    private ISkillManagementService skillManagementService;

    @Override
    public ResponseEntity<Void> deleteStudioSkill(String skillId, String workspaceId, String projectId) {
        return ResponseModel.success(skillManagementService.deleteStudioSkill(skillId, workspaceId, projectId));
    }

    @Override
    public ResponseEntity<ExportStudioSkillResponseBody> exportStudioSkill(String skillId, String workspaceId,
        String projectId) {
        return ResponseModel.success(skillManagementService.exportStudioSkill(skillId, workspaceId, projectId));
    }

    @Override
    public ResponseEntity<ImportStudioSkillResponseBody> importStudioSkill(String workspaceId, String projectId,
        MultipartFile file) {
        return ResponseModel.success(skillManagementService.importStudioSkill(workspaceId, projectId, file));
    }

    @Override
    public ResponseEntity<ListStudioSkillsResponseBody> listStudioSkills(String projectId,
        ListStudioSkillsQo listStudioSkillsQo) {
        return ResponseModel.success(skillManagementService.listStudioSkills(projectId, listStudioSkillsQo));
    }

    @Override
    public ResponseEntity<GetStudioSkillDetailsResponseBody> showStudioSkillDetail(String skillId, String workspaceId,
        String projectId) {
        return ResponseModel.success(skillManagementService.showStudioSkillDetail(skillId, workspaceId, projectId));
    }

    @Override
    public ResponseEntity<StreamingResponseBody> getSkillPackageContent(String skillId, String workspaceId,
        String projectId) {
        InputStream obsStream = skillManagementService.getSkillPackageContent(skillId, workspaceId, projectId);
        StreamingResponseBody body = outputStream -> {
            try (InputStream in = obsStream) {
                byte[] buffer = new byte[8192];
                int bytesRead;
                while ((bytesRead = in.read(buffer)) != -1) {
                    outputStream.write(buffer, 0, bytesRead);
                    outputStream.flush();
                }
            }
        };
        HttpHeaders headers = new HttpHeaders();
        // 与接口声明 produces = {"application/zip"} 保持一致，避免 Content-Type 与 Accept 协商不一致
        headers.setContentType(MediaType.parseMediaType("application/zip"));
        headers.set(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + skillId + ".zip\"");
        return ResponseEntity.ok().headers(headers).body(body);
    }
}