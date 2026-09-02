/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Date;
import java.util.Objects;

/**
 * 应用版本通道信息。
 */
@ApiModel(description = "应用版本通道信息。")

@Validated

public class VersionChannelInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "通道ID", example = "channel-001", required = true)
    @NotBlank
    private String id = null;

    @JsonProperty("app_id")
    @Schema(description = "应用ID", example = "app-001")
    private String appId = null;

    @JsonProperty("app_type")
    @Schema(description = "应用类型", example = "web")
    private String appType = null;

    @JsonProperty("sub_type")
    @Schema(description = "子类型", example = "default")
    private String subType = null;

    @JsonProperty("version_id")
    @Schema(description = "版本ID", example = "v1.0.0", required = true)
    @NotBlank
    private String versionId = null;

    @JsonProperty("version_name")
    @Schema(description = "版本名称", example = "1.0.0")
    private String versionName = null;

    @JsonProperty("channel_type")
    @Schema(description = "通道类型", example = "production")
    private String channelType = null;

    @JsonProperty("entry_point")
    @Schema(description = "入口地址", example = "https://example.com/entry")
    private String entryPoint = null;

    @JsonProperty("qr_code")
    @Schema(description = "二维码", example = "https://example.com/qr.png")
    private String qrCode = null;

    @JsonProperty("short_code")
    @Schema(description = "短链接码", example = "abc123")
    private String shortCode = null;

    @JsonProperty("metadata")
    @Schema(description = "元数据", example = "{}")
    @Valid
    private Object metadata = null;

    @JsonProperty("status")
    @Schema(description = "状态", example = "published")
    private String status = null;

    @JsonProperty("release_time")
    @Schema(description = "发布时间", example = "2024-01-01T00:00:00.000+08:00")
    private Date releaseTime = null;

    @JsonProperty("url")
    @Schema(description = "访问地址", example = "https://example.com")
    private String url = null;

    @JsonProperty("visibility_scope")
    @Schema(description = "可见范围", example = "public")
    private String visibilityScope = null;

    @JsonProperty("call_count")
    @Schema(description = "调用次数", example = "1000")
    private Integer callCount = null;

    public String getId() {
        return id;
    }

    public VersionChannelInfo setId(String id) {
        this.id = id;
        return this;
    }

    public String getAppId() {
        return appId;
    }

    public VersionChannelInfo setAppId(String appId) {
        this.appId = appId;
        return this;
    }

    public String getAppType() {
        return appType;
    }

    public VersionChannelInfo setAppType(String appType) {
        this.appType = appType;
        return this;
    }

    public String getSubType() {
        return subType;
    }

    public VersionChannelInfo setSubType(String subType) {
        this.subType = subType;
        return this;
    }

    public String getVersionId() {
        return versionId;
    }

    public VersionChannelInfo setVersionId(String versionId) {
        this.versionId = versionId;
        return this;
    }

    public String getVersionName() {
        return versionName;
    }

    public VersionChannelInfo setVersionName(String versionName) {
        this.versionName = versionName;
        return this;
    }

    public String getChannelType() {
        return channelType;
    }

    public VersionChannelInfo setChannelType(String channelType) {
        this.channelType = channelType;
        return this;
    }

    public String getEntryPoint() {
        return entryPoint;
    }

    public VersionChannelInfo setEntryPoint(String entryPoint) {
        this.entryPoint = entryPoint;
        return this;
    }

    public String getQrCode() {
        return qrCode;
    }

    public VersionChannelInfo setQrCode(String qrCode) {
        this.qrCode = qrCode;
        return this;
    }

    public String getShortCode() {
        return shortCode;
    }

    public VersionChannelInfo setShortCode(String shortCode) {
        this.shortCode = shortCode;
        return this;
    }

    public Object getMetadata() {
        return metadata;
    }

    public VersionChannelInfo setMetadata(Object metadata) {
        this.metadata = metadata;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public VersionChannelInfo setStatus(String status) {
        this.status = status;
        return this;
    }

    public Date getReleaseTime() {
        return releaseTime;
    }

    public VersionChannelInfo setReleaseTime(Date releaseTime) {
        this.releaseTime = releaseTime;
        return this;
    }

    public String getUrl() {
        return url;
    }

    public VersionChannelInfo setUrl(String url) {
        this.url = url;
        return this;
    }

    public String getVisibilityScope() {
        return visibilityScope;
    }

    public VersionChannelInfo setVisibilityScope(String visibilityScope) {
        this.visibilityScope = visibilityScope;
        return this;
    }

    public Integer getCallCount() {
        return callCount;
    }

    public VersionChannelInfo setCallCount(Integer callCount) {
        this.callCount = callCount;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class VersionChannelInfo {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    appId: ").append(toIndentedString(appId)).append("\n");
        sb.append("    appType: ").append(toIndentedString(appType)).append("\n");
        sb.append("    subType: ").append(toIndentedString(subType)).append("\n");
        sb.append("    versionId: ").append(toIndentedString(versionId)).append("\n");
        sb.append("    versionName: ").append(toIndentedString(versionName)).append("\n");
        sb.append("    channelType: ").append(toIndentedString(channelType)).append("\n");
        sb.append("    entryPoint: ").append(toIndentedString(entryPoint)).append("\n");
        sb.append("    qrCode: ").append(toIndentedString(qrCode)).append("\n");
        sb.append("    shortCode: ").append(toIndentedString(shortCode)).append("\n");
        sb.append("    metadata: ").append(toIndentedString(metadata)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    releaseTime: ").append(toIndentedString(releaseTime)).append("\n");
        sb.append("    url: ").append(toIndentedString(url)).append("\n");
        sb.append("    visibilityScope: ").append(toIndentedString(visibilityScope)).append("\n");
        sb.append("    callCount: ").append(toIndentedString(callCount)).append("\n");
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
        VersionChannelInfo versionChannelInfo = (VersionChannelInfo) o;
        return Objects.equals(this.id, versionChannelInfo.id) && Objects.equals(this.appId, versionChannelInfo.appId)
            && Objects.equals(this.appType, versionChannelInfo.appType) && Objects.equals(this.subType,
            versionChannelInfo.subType) && Objects.equals(this.versionId, versionChannelInfo.versionId)
            && Objects.equals(this.versionName, versionChannelInfo.versionName) && Objects.equals(this.channelType,
            versionChannelInfo.channelType) && Objects.equals(this.entryPoint, versionChannelInfo.entryPoint)
            && Objects.equals(this.qrCode, versionChannelInfo.qrCode) && Objects.equals(this.shortCode,
            versionChannelInfo.shortCode) && Objects.equals(this.metadata, versionChannelInfo.metadata)
            && Objects.equals(this.status, versionChannelInfo.status) && Objects.equals(this.releaseTime,
            versionChannelInfo.releaseTime) && Objects.equals(this.url, versionChannelInfo.url) && Objects.equals(
            this.visibilityScope, versionChannelInfo.visibilityScope) && Objects.equals(this.callCount,
            versionChannelInfo.callCount);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, appId, appType, subType, versionId, versionName, channelType, entryPoint, qrCode,
            shortCode, metadata, status, releaseTime, url, visibilityScope, callCount);
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
