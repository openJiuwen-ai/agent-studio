/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 创建FAQ问答对响应体
 */
@ApiModel(description = "创建FAQ问答对响应体")

@Validated

public class CreateFaqResp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("faq_id")
    @Schema(description = "FAQ ID", example = "example-id-123", required = true)
    @NotBlank
    @Length(min = 1, max = 64)
    private String faqId = null;

    public String getFaqId() {
        return faqId;
    }

    public CreateFaqResp setFaqId(String faqId) {
        this.faqId = faqId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreateFaqResp {\n");

        sb.append("    faqId: ").append(toIndentedString(faqId)).append("\n");
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
        CreateFaqResp createFaqResp = (CreateFaqResp) o;
        return Objects.equals(this.faqId, createFaqResp.faqId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(faqId);
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
