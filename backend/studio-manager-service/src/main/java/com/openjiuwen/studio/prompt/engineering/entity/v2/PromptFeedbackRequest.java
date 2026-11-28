/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.entity.v2;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.experimental.SuperBuilder;

import java.util.List;
import java.util.Map;

@Data
@SuperBuilder
@NoArgsConstructor
@AllArgsConstructor
public class PromptFeedbackRequest {

    private String prompt;

    private ExecConfig modelInfo;

    private String feedback;

    private List<Integer> selected_content_index;

    private Integer insert_pos_index;

    @JsonProperty(access = JsonProperty.Access.READ_ONLY)
    private Map<String, String> extension_info;
}
