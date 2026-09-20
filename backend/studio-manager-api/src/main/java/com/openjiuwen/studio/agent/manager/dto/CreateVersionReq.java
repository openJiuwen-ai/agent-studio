/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 创建应用版本请求体
 */
@ApiModel(description = "创建应用版本请求体")

@Validated

public class CreateVersionReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("version_name")
    @Schema(description = "版本名称", example = "示例名称")
    @Length(max = 64)
    private String versionName = null;

    @JsonProperty("version_note")
    @Schema(description = "版本号", example = "1.0.0")
    @Length(max = 1024)
    private String versionNote = null;

    public String getVersionName() {
        return versionName;
    }

    public CreateVersionReq setVersionName(String versionName) {
        this.versionName = versionName;
        return this;
    }

    public String getVersionNote() {
        return versionNote;
    }

    public CreateVersionReq setVersionNote(String versionNote) {
        this.versionNote = versionNote;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreateVersionReq {\n");

        sb.append("    versionName: ").append(toIndentedString(versionName)).append("\n");
        sb.append("    versionNote: ").append(toIndentedString(versionNote)).append("\n");
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
        CreateVersionReq createVersionReq = (CreateVersionReq) o;
        return Objects.equals(this.versionName, createVersionReq.versionName) && Objects.equals(this.versionNote,
            createVersionReq.versionNote);
    }

    @Override
    public int hashCode() {
        return Objects.hash(versionName, versionNote);
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
