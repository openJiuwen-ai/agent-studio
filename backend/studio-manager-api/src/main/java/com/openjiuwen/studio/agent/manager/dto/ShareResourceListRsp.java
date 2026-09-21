/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * ShareResourceListRsp
 */

@Validated

public class ShareResourceListRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("count")
    @Schema(description = "数量", example = "10")
    private Integer count = null;

    @JsonProperty("resource_list")
    @Schema(description = "资源", example = "[]")
    @Valid
    @Size()
    private List<ShareResourceInfo> resourceList = null;

    public Integer getCount() {
        return count;
    }

    public ShareResourceListRsp setCount(Integer count) {
        this.count = count;
        return this;
    }

    public List<ShareResourceInfo> getResourceList() {
        return resourceList;
    }

    public ShareResourceListRsp setResourceList(List<ShareResourceInfo> resourceList) {
        this.resourceList = resourceList;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ShareResourceListRsp {\n");

        sb.append("    count: ").append(toIndentedString(count)).append("\n");
        sb.append("    resourceList: ").append(toIndentedString(resourceList)).append("\n");
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
        ShareResourceListRsp shareResourceListRsp = (ShareResourceListRsp) o;
        return Objects.equals(this.count, shareResourceListRsp.count) && Objects.equals(this.resourceList,
            shareResourceListRsp.resourceList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(count, resourceList);
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
