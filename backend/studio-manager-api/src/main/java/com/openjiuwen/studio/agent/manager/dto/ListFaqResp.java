/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.openjiuwen.studio.agent.common.dto.knowledge.KnowledgeFaq;

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
 * 查询FAQ问答对列表响应体
 */
@ApiModel(description = "查询FAQ问答对列表响应体")

@Validated

public class ListFaqResp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("count")
    @Schema(description = "数量", example = "10", required = true)
    @NotNull
    private Integer count = null;

    @JsonProperty("faq_list")
    @Schema(description = "FAQ", example = "[]", required = true)
    @Valid
    @NotNull
    @Size(max = 1000)
    private List<KnowledgeFaq> faqList = new ArrayList<KnowledgeFaq>();

    public Integer getCount() {
        return count;
    }

    public ListFaqResp setCount(Integer count) {
        this.count = count;
        return this;
    }

    public List<KnowledgeFaq> getFaqList() {
        return faqList;
    }

    public ListFaqResp setFaqList(List<KnowledgeFaq> faqList) {
        this.faqList = faqList;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListFaqResp {\n");

        sb.append("    count: ").append(toIndentedString(count)).append("\n");
        sb.append("    faqList: ").append(toIndentedString(faqList)).append("\n");
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
        ListFaqResp listFaqResp = (ListFaqResp) o;
        return Objects.equals(this.count, listFaqResp.count) && Objects.equals(this.faqList, listFaqResp.faqList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(count, faqList);
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
