/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.runtime.controller;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.dto.run.RunToolRequestBody;
import com.openjiuwen.studio.agent.common.dto.tool.RunToolResponseBody;
import com.openjiuwen.studio.agent.runtime.dto.Base64ToImageReq;
import com.openjiuwen.studio.agent.runtime.dto.OcrRecognizeRsp;
import com.openjiuwen.studio.agent.runtime.dto.ResolveAudioFileReq;
import com.openjiuwen.studio.agent.runtime.dto.ResolveAudioFileRsp;
import com.openjiuwen.studio.agent.runtime.dto.ResolveDocumentReq;
import com.openjiuwen.studio.agent.runtime.dto.ResolveDocumentRsp;
import com.openjiuwen.studio.agent.runtime.dto.ToBase64Rsp;
import com.openjiuwen.studio.agent.runtime.dto.ToImageRsp;
import com.openjiuwen.studio.agent.runtime.dto.Url2Base64Req;

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
import jakarta.validation.constraints.Size;

import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.multipart.MultipartFile;

@Api(value = "ToolRuntime", description = "the ToolRuntime API")
@Validated

/**
 * ToolRuntimeApi interface
 */
public interface ToolRuntimeApi {
    @ApiOperation(value = "base64转Image", nickname = "base64ToImage", notes = "base64转Image",
        response = ToImageRsp.class, tags = {"ToolRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "图片base64格式字符串", response = ToImageRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/inner-tools/image-convert/base64ToImage", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<ToImageRsp> base64ToImage(
        @NotNull @ApiParam(value = "base64字符串", required = true) @Valid @RequestBody Base64ToImageReq body);

    @ApiOperation(value = "图片转base64", nickname = "file2Base64", notes = "图片转base64",
        response = ToBase64Rsp.class, tags = {"ToolRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "图片base64格式字符串", response = ToBase64Rsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/inner-tools/image-convert/file2base64", produces = {"application/json"},
        consumes = {"multipart/form-data"}, method = RequestMethod.POST)
    ResponseEntity<ToBase64Rsp> file2Base64(
        @Parameter(description = "file detail") @Valid @RequestPart(value = "file", required = true) MultipartFile file,
        @ApiParam(value = "图片类型") @RequestParam(value = "mimetype", required = false) String mimetype,
        @ApiParam(value = "输出是否携带DataUrl前缀") @RequestParam(value = "isDataUrl", required = false)
        Boolean isDataUrl);

    @ApiOperation(value = "OCR识别", nickname = "ocrRecognize", notes = "OCR识别", response = OcrRecognizeRsp.class,
        tags = {"ToolRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "文件内容", response = OcrRecognizeRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/inner-tools/document/ocr-recognize", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<OcrRecognizeRsp> ocrRecognize(
        @NotNull @ApiParam(value = "OCR识别请求体", required = true) @Valid @RequestBody ResolveDocumentReq body);

    @ApiOperation(value = "音频文件识别", nickname = "resolveAudioFile", notes = "音频文件识别",
        response = ResolveAudioFileRsp.class, tags = {"ToolRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "识别结果", response = ResolveAudioFileRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/inner-tools/document/resolve-audio", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<ResolveAudioFileRsp> resolveAudioFile(
        @NotNull @ApiParam(value = "音频文件识别请求体", required = true) @Valid @RequestBody ResolveAudioFileReq body);

    @ApiOperation(value = "文档生成", nickname = "resolveDocument", notes = "文档生成",
        response = ResolveDocumentRsp.class, tags = {"ToolRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "文件内容", response = ResolveDocumentRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/inner-tools/document/resolve", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<ResolveDocumentRsp> resolveDocument(
        @NotNull @ApiParam(value = "文档解析请求体", required = true) @Valid @RequestBody ResolveDocumentReq body);

    @ApiOperation(value = "工具执行", nickname = "runTool", notes = "执行一个工具",
        response = RunToolResponseBody.class, tags = {"ToolRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "工具运行结果", response = RunToolResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/tools/{tool_id}", produces = {"application/json"},
        consumes = {"application/json;charset=utf-8"}, method = RequestMethod.POST)
    ResponseEntity<RunToolResponseBody> runTool(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @ApiParam(value = "执行工具请求参数", required = true) @Valid @RequestBody RunToolRequestBody body);

    @ApiOperation(value = "URL转base64", nickname = "url2Base64", notes = "URL转base64", response = ToBase64Rsp.class,
        tags = {"ToolRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "图片base64格式字符串", response = ToBase64Rsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/inner-tools/image-convert/url2base64", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<ToBase64Rsp> url2Base64(
        @NotNull @ApiParam(value = "图片url", required = true) @Valid @RequestBody Url2Base64Req body);

}
