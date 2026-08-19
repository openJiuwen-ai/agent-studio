/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.annotations.ApiModel;

import java.io.Serializable;
import java.util.List;

/**
 * 模型导入预检响应（逐行解析+验签+冲突检测，不落库）。
 */
@ApiModel(description = "模型导入预检响应")
public class ModelImportPreviewRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("total_count")
    private Integer totalCount = 0;

    @JsonProperty("conflict_count")
    private Integer conflictCount = 0;

    @JsonProperty("items")
    private List<ModelImportPreviewItem> items;

    public Integer getTotalCount() {
        return totalCount;
    }

    public ModelImportPreviewRsp setTotalCount(Integer totalCount) {
        this.totalCount = totalCount;
        return this;
    }

    public Integer getConflictCount() {
        return conflictCount;
    }

    public ModelImportPreviewRsp setConflictCount(Integer conflictCount) {
        this.conflictCount = conflictCount;
        return this;
    }

    public List<ModelImportPreviewItem> getItems() {
        return items;
    }

    public ModelImportPreviewRsp setItems(List<ModelImportPreviewItem> items) {
        this.items = items;
        return this;
    }
}
