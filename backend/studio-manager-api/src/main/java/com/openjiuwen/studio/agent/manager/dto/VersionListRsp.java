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
 * 应用版本列表响应体
 */
@ApiModel(description = "应用版本列表响应体")

@Validated

public class VersionListRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("count")
    @Schema(description = "数量", example = "10")
    private Integer count = null;

    @JsonProperty("version_list")
    @Schema(description = "版本列表", example = "[]")
    @Valid
    @Size()
    private List<VersionInfo> versionList = null;

    public Integer getCount() {
        return count;
    }

    public VersionListRsp setCount(Integer count) {
        this.count = count;
        return this;
    }

    public List<VersionInfo> getVersionList() {
        return versionList;
    }

    public VersionListRsp setVersionList(List<VersionInfo> versionList) {
        this.versionList = versionList;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class VersionListRsp {\n");

        sb.append("    count: ").append(toIndentedString(count)).append("\n");
        sb.append("    versionList: ").append(toIndentedString(versionList)).append("\n");
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
        VersionListRsp versionListRsp = (VersionListRsp) o;
        return Objects.equals(this.count, versionListRsp.count) && Objects.equals(this.versionList,
            versionListRsp.versionList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(count, versionList);
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
