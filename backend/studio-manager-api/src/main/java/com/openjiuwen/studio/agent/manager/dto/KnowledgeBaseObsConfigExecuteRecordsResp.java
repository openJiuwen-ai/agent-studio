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
 * OBS执行记录列表。
 */
@ApiModel(description = "OBS执行记录列表。")

@Validated

public class KnowledgeBaseObsConfigExecuteRecordsResp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("data")
    @Schema(description = "数据", example = "[]")
    @Valid
    @Size()
    private List<KnowledgeBaseObsConfigExecuteRecord> data = null;

    @JsonProperty("total")
    @Schema(description = "总数", example = "1")
    private Long total = null;

    public List<KnowledgeBaseObsConfigExecuteRecord> getData() {
        return data;
    }

    public KnowledgeBaseObsConfigExecuteRecordsResp setData(List<KnowledgeBaseObsConfigExecuteRecord> data) {
        this.data = data;
        return this;
    }

    public Long getTotal() {
        return total;
    }

    public KnowledgeBaseObsConfigExecuteRecordsResp setTotal(Long total) {
        this.total = total;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class KnowledgeBaseObsConfigExecuteRecordsResp {\n");

        sb.append("    data: ").append(toIndentedString(data)).append("\n");
        sb.append("    total: ").append(toIndentedString(total)).append("\n");
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
        KnowledgeBaseObsConfigExecuteRecordsResp knowledgeBaseObsConfigExecuteRecordsResp
            = (KnowledgeBaseObsConfigExecuteRecordsResp) o;
        return Objects.equals(this.data, knowledgeBaseObsConfigExecuteRecordsResp.data) && Objects.equals(this.total,
            knowledgeBaseObsConfigExecuteRecordsResp.total);
    }

    @Override
    public int hashCode() {
        return Objects.hash(data, total);
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
