/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * GetObsObjectReq
 */

@Validated
public class GetObsObjectReq implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("path")
    @Schema(description = "路径", example = "示例文本")
    private String path = null;

    @JsonProperty("bucket")
    @Schema(description = "桶", example = "示例文本")
    private String bucket = null;

    public String getPath() {
        return path;
    }

    public GetObsObjectReq setPath(String path) {
        this.path = path;
        return this;
    }

    public String getBucket() {
        return bucket;
    }

    public GetObsObjectReq setBucket(String bucket) {
        this.bucket = bucket;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class GetObsObjectReq {\n");
        sb.append("    path: ").append(toIndentedString(path)).append("\n");
        sb.append("    bucket: ").append(toIndentedString(bucket)).append("\n");
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
        GetObsObjectReq getObsObjectReq = (GetObsObjectReq) o;
        return Objects.equals(this.path, getObsObjectReq.path) && Objects.equals(this.bucket, getObsObjectReq.bucket);
    }

    @Override
    public int hashCode() {
        return Objects.hash(path, bucket);
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
