/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * CommonDeleteRsp
 */

@Validated

public class CommonDeleteRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "ID", example = "example-id-123")
    private String id = null;

    @JsonProperty("version_id")
    @Schema(description = "版本ID", example = "example-id-123")
    private String versionId = null;

    public String getId() {
        return id;
    }

    public CommonDeleteRsp setId(String id) {
        this.id = id;
        return this;
    }

    public String getVersionId() {
        return versionId;
    }

    public CommonDeleteRsp setVersionId(String versionId) {
        this.versionId = versionId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CommonDeleteRsp {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    versionId: ").append(toIndentedString(versionId)).append("\n");
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
        CommonDeleteRsp commonDeleteRsp = (CommonDeleteRsp) o;
        return Objects.equals(this.id, commonDeleteRsp.id) && Objects.equals(this.versionId, commonDeleteRsp.versionId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, versionId);
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
