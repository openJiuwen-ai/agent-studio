/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */


package com.openjiuwen.studio.agent.runtime.controller;

import com.openjiuwen.studio.agent.common.dto.run.RunToolRequestBody;
import com.openjiuwen.studio.agent.common.dto.tool.RunToolResponseBody;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;
import com.openjiuwen.studio.agent.runtime.dto.Base64ToImageReq;
import com.openjiuwen.studio.agent.runtime.dto.OcrRecognizeRsp;
import com.openjiuwen.studio.agent.runtime.dto.ResolveAudioFileReq;
import com.openjiuwen.studio.agent.runtime.dto.ResolveAudioFileRsp;
import com.openjiuwen.studio.agent.runtime.dto.ResolveDocumentReq;
import com.openjiuwen.studio.agent.runtime.dto.ResolveDocumentRsp;
import com.openjiuwen.studio.agent.runtime.dto.ToBase64Rsp;
import com.openjiuwen.studio.agent.runtime.dto.ToImageRsp;
import com.openjiuwen.studio.agent.runtime.dto.Url2Base64Req;
import com.openjiuwen.studio.agent.runtime.service.IToolRuntimeService;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

/**
 * ToolRuntime controller
 */
@RestController

public class ToolRuntimeApiController implements ToolRuntimeApi {
    private static final Logger log = LoggerFactory.getLogger(ToolRuntimeApiController.class);

    @Autowired
    private IToolRuntimeService toolRuntimeService;

    @Override
    public ResponseEntity<ToImageRsp> base64ToImage(Base64ToImageReq body) {
        return ResponseModel.success(toolRuntimeService.base64ToImage(body));
    }

    @Override
    public ResponseEntity<ToBase64Rsp> file2Base64(MultipartFile file, String mimetype, Boolean isDataUrl) {
        return ResponseModel.success(toolRuntimeService.file2Base64(file, mimetype, isDataUrl));
    }

    @Override
    public ResponseEntity<OcrRecognizeRsp> ocrRecognize(ResolveDocumentReq body) {
        return ResponseModel.success(toolRuntimeService.ocrRecognize(body));
    }

    @Override
    public ResponseEntity<ResolveAudioFileRsp> resolveAudioFile(ResolveAudioFileReq body) {
        return ResponseModel.success(toolRuntimeService.resolveAudioFile(body));
    }

    @Override
    public ResponseEntity<ResolveDocumentRsp> resolveDocument(ResolveDocumentReq body) {
        return ResponseModel.success(toolRuntimeService.resolveDocument(body));
    }

    @Override
    public ResponseEntity<RunToolResponseBody> runTool(String projectId, RunToolRequestBody body) {
        return ResponseModel.success(toolRuntimeService.runTool(projectId, body));
    }

    @Override
    public ResponseEntity<ToBase64Rsp> url2Base64(Url2Base64Req body) {
        return ResponseModel.success(toolRuntimeService.url2Base64(body));
    }
}