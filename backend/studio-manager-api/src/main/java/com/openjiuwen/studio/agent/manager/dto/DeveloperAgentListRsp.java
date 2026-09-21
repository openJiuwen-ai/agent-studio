/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 开发者空间查询agent列表响应
 */
@ApiModel(description = "开发者空间查询agent列表响应")

@Validated

public class DeveloperAgentListRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("data")
    @Schema(description = "数据", example = "[]")
    @Valid
    @Size()
    private List<DeveloperAgentInfo> data = null;

    @JsonProperty("page_info")
    @Schema(description = "页码", example = "{}")
    @Valid
    private DeveloperSpacePage pageInfo = null;

    public List<DeveloperAgentInfo> getData() {
        return data;
    }

    public DeveloperAgentListRsp setData(List<DeveloperAgentInfo> data) {
        this.data = data;
        return this;
    }

    public DeveloperSpacePage getPageInfo() {
        return pageInfo;
    }

    public DeveloperAgentListRsp setPageInfo(DeveloperSpacePage pageInfo) {
        this.pageInfo = pageInfo;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class DeveloperAgentListRsp {\n");

        sb.append("    data: ").append(toIndentedString(data)).append("\n");
        sb.append("    pageInfo: ").append(toIndentedString(pageInfo)).append("\n");
        sb.append("}");
        return sb.toString();
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (o == null || getClass() != o.getClass()) {
            return false;
        }
        DeveloperAgentListRsp developerAgentListRsp = (DeveloperAgentListRsp) o;
        return Objects.equals(this.data, developerAgentListRsp.data) && Objects.equals(this.pageInfo,
            developerAgentListRsp.pageInfo);
    }

    @Override
    public int hashCode() {
        return Objects.hash(data, pageInfo);
    }

    /**
     * Convert the given object to string with each line indented by 4 spaces
     * (except the first line).
     */
    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }
}
