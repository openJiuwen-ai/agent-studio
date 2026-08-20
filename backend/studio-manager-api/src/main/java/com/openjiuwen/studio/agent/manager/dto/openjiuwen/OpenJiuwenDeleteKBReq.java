/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto.openjiuwen;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

/**
 * 删除 openjiuwen 知识库请求。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class OpenJiuwenDeleteKBReq implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("kb_id")
    private String kbId;
}
