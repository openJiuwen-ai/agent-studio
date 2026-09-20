/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
public class ParamExtractionIndex {
    @Schema(description = "参数提取完成节点信息", example = "{}")
    private com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfo paramFinishNode;

    @Schema(description = "索引序号", example = "0")
    int index;
}
