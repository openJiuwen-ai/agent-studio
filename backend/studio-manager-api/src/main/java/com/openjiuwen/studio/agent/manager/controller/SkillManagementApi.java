/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.ExportStudioSkillResponseBody;
import com.openjiuwen.studio.agent.manager.dto.GetStudioSkillDetailsResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ImportStudioSkillResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListStudioSkillsQo;
import com.openjiuwen.studio.agent.manager.dto.ListStudioSkillsResponseBody;

import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import io.swagger.annotations.ApiResponse;
import io.swagger.annotations.ApiResponses;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.enums.ParameterIn;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;

import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.multipart.MultipartFile;

@Api(value = "SkillManagement", description = "the SkillManagement API")
@Validated

/**
 * SkillManagementApi interface
 */ public interface SkillManagementApi {
    @ApiOperation(value = "删除Skill", nickname = "deleteStudioSkill", notes = "删除Skill。", tags = {"SkillManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 204, message = "删除成功，无响应返回。"),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/skills/{skill_id}", produces = {"application/json"},
        method = RequestMethod.DELETE)
    ResponseEntity<Void> deleteStudioSkill(
        @Pattern(regexp = "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
        @Parameter(in = ParameterIn.PATH, description = "Skill ID。", required = true, schema = @Schema())
        @PathVariable("skill_id") String skillId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$")
        @Parameter(in = ParameterIn.QUERY, description = "空间ID", required = true, schema = @Schema())
        @ApiParam(value = "空间ID", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "项目ID", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId);

    @ApiOperation(value = "导出Skill", nickname = "exportStudioSkill", notes = "导出指定Skill的最新版本。",
        response = ExportStudioSkillResponseBody.class, tags = {"SkillManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "导出成功，返回带有鉴权信息的obs_url。",
            response = ExportStudioSkillResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/skills/{skill_id}/export", produces = {"application/json"},
        method = RequestMethod.POST)
    ResponseEntity<ExportStudioSkillResponseBody> exportStudioSkill(
        @Pattern(regexp = "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
        @Parameter(in = ParameterIn.PATH, description = "Skill ID。", required = true, schema = @Schema())
        @PathVariable("skill_id") String skillId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$")
        @Parameter(in = ParameterIn.QUERY, description = "空间ID", required = true, schema = @Schema())
        @ApiParam(value = "空间ID", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "项目ID", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId);

    @ApiOperation(value = "导入Skill", nickname = "importStudioSkill", notes = "导入Skill，支持上传zip包或obs分享文件。",
        response = ImportStudioSkillResponseBody.class, tags = {"SkillManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "导入成功，返回导入的Skill信息。",
            response = ImportStudioSkillResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/skills/import", produces = {"application/json"},
        consumes = {"multipart/form-data"}, method = RequestMethod.POST)
    ResponseEntity<ImportStudioSkillResponseBody> importStudioSkill(
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$")
        @Parameter(in = ParameterIn.QUERY, description = "空间ID", required = true, schema = @Schema())
        @ApiParam(value = "空间ID", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "项目ID", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(description = "file detail") @Valid @RequestPart(value = "file", required = true)
        MultipartFile file);

    @ApiOperation(value = "查询Skill列表", nickname = "listStudioSkills", notes = "查询Skill列表，支持多种过滤条件。",
        response = ListStudioSkillsResponseBody.class, tags = {"SkillManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "查询成功。", response = ListStudioSkillsResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/skills", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ListStudioSkillsResponseBody> listStudioSkills(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "项目ID", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "ListStudioSkillsQo: converted from multi query params") @Valid
        ListStudioSkillsQo listStudioSkillsQo);

    @ApiOperation(value = "查询Skill详情", nickname = "showStudioSkillDetail", notes = "查询Skill详细信息。",
        response = GetStudioSkillDetailsResponseBody.class, tags = {"SkillManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "查询成功。", response = GetStudioSkillDetailsResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/skills/{skill_id}", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<GetStudioSkillDetailsResponseBody> showStudioSkillDetail(
        @Pattern(regexp = "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
        @Parameter(in = ParameterIn.PATH, description = "Skill ID。", required = true, schema = @Schema())
        @PathVariable("skill_id") String skillId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$")
        @Parameter(in = ParameterIn.QUERY, description = "空间ID", required = true, schema = @Schema())
        @ApiParam(value = "空间ID", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "项目ID", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId);

}
