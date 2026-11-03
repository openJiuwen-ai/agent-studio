/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto.nl;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import org.springframework.validation.annotation.Validated;

import java.util.Map;

@Getter
@Setter
@NoArgsConstructor
@Validated
public class NLChatReq {
    @Valid
    @NotNull
    @Size(max = 10)
    private Map<String, Object> model;

    @NotNull
    private String query;

    private NLResource resource;
}
