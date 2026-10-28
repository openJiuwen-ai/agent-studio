/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * MCP 工具清单差异项
 */
@Schema(description = "MCP 工具清单差异项")
public class McpToolDiffItem implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "工具名称", example = "search-tool")
    private String name = null;

    @JsonProperty("referenced")
    @Schema(description = "下线工具是否仍被智能体/工作流引用", example = "false")
    private Boolean referenced = Boolean.FALSE;

    @JsonProperty("references")
    @Schema(description = "引用方清单，仅下线且被引用时返回")
    private List<McpToolReferenceItem> references = new ArrayList<>();

    public String getName() {
        return name;
    }

    public McpToolDiffItem setName(String name) {
        this.name = name;
        return this;
    }

    public Boolean getReferenced() {
        return referenced;
    }

    public McpToolDiffItem setReferenced(Boolean referenced) {
        this.referenced = referenced;
        return this;
    }

    public List<McpToolReferenceItem> getReferences() {
        return references;
    }

    public McpToolDiffItem setReferences(List<McpToolReferenceItem> references) {
        this.references = references;
        return this;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (o == null || getClass() != o.getClass()) {
            return false;
        }
        McpToolDiffItem that = (McpToolDiffItem) o;
        return Objects.equals(name, that.name) && Objects.equals(referenced, that.referenced)
            && Objects.equals(references, that.references);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, referenced, references);
    }

    @Override
    public String toString() {
        return "McpToolDiffItem{" + "name='" + name + '\'' + ", referenced=" + referenced + ", references="
            + references + '}';
    }
}
