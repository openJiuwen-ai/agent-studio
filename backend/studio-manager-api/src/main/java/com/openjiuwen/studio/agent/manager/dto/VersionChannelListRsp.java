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
 * 应用版本通道列表响应体。
 */
@ApiModel(description = "应用版本通道列表响应体。")

@Validated

public class VersionChannelListRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("count")
    @Schema(description = "数量", example = "10")
    private Integer count = null;

    @JsonProperty("latest_version_id")
    @Schema(description = "最新版本", example = "example-id-123")
    private String latestVersionId = null;

    @JsonProperty("channel_list")
    @Schema(description = "渠道", example = "[]")
    @Valid
    @Size()
    private List<VersionChannelInfo> channelList = null;

    public Integer getCount() {
        return count;
    }

    public VersionChannelListRsp setCount(Integer count) {
        this.count = count;
        return this;
    }

    public String getLatestVersionId() {
        return latestVersionId;
    }

    public VersionChannelListRsp setLatestVersionId(String latestVersionId) {
        this.latestVersionId = latestVersionId;
        return this;
    }

    public List<VersionChannelInfo> getChannelList() {
        return channelList;
    }

    public VersionChannelListRsp setChannelList(List<VersionChannelInfo> channelList) {
        this.channelList = channelList;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class VersionChannelListRsp {\n");

        sb.append("    count: ").append(toIndentedString(count)).append("\n");
        sb.append("    latestVersionId: ").append(toIndentedString(latestVersionId)).append("\n");
        sb.append("    channelList: ").append(toIndentedString(channelList)).append("\n");
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
        VersionChannelListRsp versionChannelListRsp = (VersionChannelListRsp) o;
        return Objects.equals(this.count, versionChannelListRsp.count) && Objects.equals(this.latestVersionId,
            versionChannelListRsp.latestVersionId) && Objects.equals(this.channelList,
            versionChannelListRsp.channelList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(count, latestVersionId, channelList);
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
