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
 * App列表响应体。
 */
@ApiModel(description = "App列表响应体。")

@Validated

public class AppListRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("count")
    @Schema(description = "数量", example = "1")
    private Long count = null;

    @JsonProperty("app_list")
    @Schema(description = "应用列表", example = "[]")
    @Valid
    @Size()
    private List<AppInfo> appList = null;

    public Long getCount() {
        return count;
    }

    public AppListRsp setCount(Long count) {
        this.count = count;
        return this;
    }

    public List<AppInfo> getAppList() {
        return appList;
    }

    public AppListRsp setAppList(List<AppInfo> appList) {
        this.appList = appList;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AppListRsp {\n");

        sb.append("    count: ").append(toIndentedString(count)).append("\n");
        sb.append("    appList: ").append(toIndentedString(appList)).append("\n");
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
        AppListRsp appListRsp = (AppListRsp) o;
        return Objects.equals(this.count, appListRsp.count) && Objects.equals(this.appList, appListRsp.appList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(count, appList);
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
