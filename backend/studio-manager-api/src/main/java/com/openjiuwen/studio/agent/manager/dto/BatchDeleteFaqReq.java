/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * 批量删除FAQ问答对请求体
 */
@ApiModel(description = "批量删除FAQ问答对请求体")

@Validated

public class BatchDeleteFaqReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("faq_ids")
    @Schema(description = "FAQ", example = "[]", required = true)
    @Valid
    @NotNull
    @Size(min = 1, max = 1000)
    private List<@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Length(min = 1, max = 64) String> faqIds
        = new ArrayList<String>();

    public List<@Size(min = 1, max = 1000) String> getFaqIds() {
        return faqIds;
    }

    public BatchDeleteFaqReq setFaqIds(List<@Size(min = 1, max = 1000) String> faqIds) {
        this.faqIds = faqIds;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class BatchDeleteFaqReq {\n");

        sb.append("    faqIds: ").append(toIndentedString(faqIds)).append("\n");
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
        BatchDeleteFaqReq batchDeleteFaqReq = (BatchDeleteFaqReq) o;
        return Objects.equals(this.faqIds, batchDeleteFaqReq.faqIds);
    }

    @Override
    public int hashCode() {
        return Objects.hash(faqIds);
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
