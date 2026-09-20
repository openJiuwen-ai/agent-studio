/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 版本引用信息
 */
@ApiModel(description = "版本引用信息")

@Validated

public class VersionReference implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("version_id")
    @Schema(description = "版本ID", example = "1787901244768", required = true)
    @NotNull
    private String versionId = null;

    @JsonProperty("version_name")
    @Schema(description = "版本名称", example = "v1.0.0")
    private String versionName = null;

    @JsonProperty("reference_count")
    @Schema(description = "引用数量", example = "2", required = true)
    @NotNull
    private Long referenceCount = null;

    @JsonProperty("is_shared")
    @Schema(description = "是否已共享到资产广场", example = "false", required = true)
    @NotNull
    private Boolean isShared = null;

    @JsonProperty("is_latest")
    @Schema(description = "是否最新版本", example = "true", required = true)
    @NotNull
    private Boolean isLatest = null;

    public String getVersionId() {
        return versionId;
    }

    public VersionReference setVersionId(String versionId) {
        this.versionId = versionId;
        return this;
    }

    public String getVersionName() {
        return versionName;
    }

    public VersionReference setVersionName(String versionName) {
        this.versionName = versionName;
        return this;
    }

    public Long getReferenceCount() {
        return referenceCount;
    }

    public VersionReference setReferenceCount(Long referenceCount) {
        this.referenceCount = referenceCount;
        return this;
    }

    public Boolean getIsShared() {
        return isShared;
    }

    public VersionReference setIsShared(Boolean isShared) {
        this.isShared = isShared;
        return this;
    }

    public Boolean getIsLatest() {
        return isLatest;
    }

    public VersionReference setIsLatest(Boolean isLatest) {
        this.isLatest = isLatest;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class VersionReference {\n");

        sb.append("    versionId: ").append(toIndentedString(versionId)).append("\n");
        sb.append("    versionName: ").append(toIndentedString(versionName)).append("\n");
        sb.append("    referenceCount: ").append(toIndentedString(referenceCount)).append("\n");
        sb.append("    isShared: ").append(toIndentedString(isShared)).append("\n");
        sb.append("    isLatest: ").append(toIndentedString(isLatest)).append("\n");
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
        VersionReference versionReference = (VersionReference) o;
        return Objects.equals(this.versionId, versionReference.versionId)
            && Objects.equals(this.versionName, versionReference.versionName)
            && Objects.equals(this.referenceCount, versionReference.referenceCount)
            && Objects.equals(this.isShared, versionReference.isShared)
            && Objects.equals(this.isLatest, versionReference.isLatest);
    }

    @Override
    public int hashCode() {
        return Objects.hash(versionId, versionName, referenceCount, isShared, isLatest);
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
