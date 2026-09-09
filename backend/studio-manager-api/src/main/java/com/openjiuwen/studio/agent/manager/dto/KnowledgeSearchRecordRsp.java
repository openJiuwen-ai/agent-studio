/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * 知识库命中测试记录
 */
@ApiModel(description = "知识库命中测试记录")

@Validated

public class KnowledgeSearchRecordRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("count")
    @Schema(description = "数量", example = "1", required = true)
    @NotNull
    private Long count = null;

    @JsonProperty("KnowledgeSearchRecord")
    @Schema(description = "知识搜索记录", example = "[]", required = true)
    @Valid
    @NotNull
    @Size()
    private List<KnowledgeSearchRecord> knowledgeSearchRecord = new ArrayList<KnowledgeSearchRecord>();

    public Long getCount() {
        return count;
    }

    public KnowledgeSearchRecordRsp setCount(Long count) {
        this.count = count;
        return this;
    }

    public List<KnowledgeSearchRecord> getKnowledgeSearchRecord() {
        return knowledgeSearchRecord;
    }

    public KnowledgeSearchRecordRsp setKnowledgeSearchRecord(List<KnowledgeSearchRecord> knowledgeSearchRecord) {
        this.knowledgeSearchRecord = knowledgeSearchRecord;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class KnowledgeSearchRecordRsp {\n");

        sb.append("    count: ").append(toIndentedString(count)).append("\n");
        sb.append("    knowledgeSearchRecord: ").append(toIndentedString(knowledgeSearchRecord)).append("\n");
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
        KnowledgeSearchRecordRsp knowledgeSearchRecordRsp = (KnowledgeSearchRecordRsp) o;
        return Objects.equals(this.count, knowledgeSearchRecordRsp.count) && Objects.equals(this.knowledgeSearchRecord,
            knowledgeSearchRecordRsp.knowledgeSearchRecord);
    }

    @Override
    public int hashCode() {
        return Objects.hash(count, knowledgeSearchRecord);
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
