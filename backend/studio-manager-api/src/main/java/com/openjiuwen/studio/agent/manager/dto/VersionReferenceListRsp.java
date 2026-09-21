/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * 版本引用数量列表
 */
@ApiModel(description = "版本引用数量列表")

@Validated

public class VersionReferenceListRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("version_references")
    @Schema(description = "版本引用数量列表", example = "[]")
    private List<VersionReference> versionReferences = new ArrayList<>();

    public List<VersionReference> getVersionReferences() {
        return versionReferences;
    }

    public VersionReferenceListRsp setVersionReferences(List<VersionReference> versionReferences) {
        this.versionReferences = versionReferences;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class VersionReferenceListRsp {\n");

        sb.append("    versionReferences: ").append(toIndentedString(versionReferences)).append("\n");
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
        VersionReferenceListRsp versionReferenceListRsp = (VersionReferenceListRsp) o;
        return Objects.equals(this.versionReferences, versionReferenceListRsp.versionReferences);
    }

    @Override
    public int hashCode() {
        return Objects.hash(versionReferences);
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
