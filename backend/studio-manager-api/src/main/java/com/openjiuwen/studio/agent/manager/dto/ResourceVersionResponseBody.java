/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * 资源可用版本信息返回。
 */
@ApiModel(description = "资源可用版本信息返回。")

@Validated

public class ResourceVersionResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("versions")
    private List<VersionInfo> versions = new ArrayList<VersionInfo>();

    public List<VersionInfo> getVersions() {
        return versions;
    }

    public ResourceVersionResponseBody setVersions(List<VersionInfo> versions) {
        this.versions = versions;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ResourceVersionResponseBody {\n");
        sb.append("    versions: ").append(toIndentedString(versions)).append("\n");
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
        ResourceVersionResponseBody resourceVersionResponseBody = (ResourceVersionResponseBody) o;
        return Objects.equals(this.versions, resourceVersionResponseBody.versions);
    }

    @Override
    public int hashCode() {
        return Objects.hash(versions);
    }

    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }
}
