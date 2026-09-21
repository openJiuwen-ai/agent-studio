/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import io.swagger.annotations.ApiModel;

import java.io.Serializable;
import java.util.Objects;

/**
 * 版本引用数量统计结果
 */
@ApiModel(description = "版本引用数量统计结果")
public class VersionReferenceCount implements Serializable {
    private static final long serialVersionUID = 1L;

    private String resourceVersion;

    private Long referenceCount;

    public String getResourceVersion() {
        return resourceVersion;
    }

    public VersionReferenceCount setResourceVersion(String resourceVersion) {
        this.resourceVersion = resourceVersion;
        return this;
    }

    public Long getReferenceCount() {
        return referenceCount;
    }

    public VersionReferenceCount setReferenceCount(Long referenceCount) {
        this.referenceCount = referenceCount;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class VersionReferenceCount {\n");

        sb.append("    resourceVersion: ").append(toIndentedString(resourceVersion)).append("\n");
        sb.append("    referenceCount: ").append(toIndentedString(referenceCount)).append("\n");
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
        VersionReferenceCount versionReferenceCount = (VersionReferenceCount) o;
        return Objects.equals(this.resourceVersion, versionReferenceCount.resourceVersion)
            && Objects.equals(this.referenceCount, versionReferenceCount.referenceCount);
    }

    @Override
    public int hashCode() {
        return Objects.hash(resourceVersion, referenceCount);
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
