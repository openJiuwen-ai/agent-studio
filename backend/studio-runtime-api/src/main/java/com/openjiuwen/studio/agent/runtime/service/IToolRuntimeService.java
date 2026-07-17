/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */


package com.openjiuwen.studio.agent.runtime.service;

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

import org.springframework.web.multipart.MultipartFile;


/**
 * ToolRuntime service
 */

public interface IToolRuntimeService {

    /**
     * base64ToImage
     *
     * @param body body
     */
    ToImageRsp base64ToImage(Base64ToImageReq body) ;

    /**
     * file2Base64
     *
     * @param file file
     * @param mimetype mimetype
     * @param isDataUrl isDataUrl
     */
    ToBase64Rsp file2Base64(MultipartFile file, String mimetype, Boolean isDataUrl) ;

    /**
     * ocrRecognize
     *
     * @param body body
     */
    OcrRecognizeRsp ocrRecognize(ResolveDocumentReq body) ;

    /**
     * resolveAudioFile
     *
     * @param body body
     */
    ResolveAudioFileRsp resolveAudioFile(ResolveAudioFileReq body) ;

    /**
     * resolveDocument
     *
     * @param body body
     */
    ResolveDocumentRsp resolveDocument(ResolveDocumentReq body) ;

    /**
     * runTool
     *
     * @param projectId projectId
     * @param body body
     */
    RunToolResponseBody runTool(String projectId, RunToolRequestBody body) ;

    /**
     * url2Base64
     *
     * @param body body
     */
    ToBase64Rsp url2Base64(Url2Base64Req body) ;
}