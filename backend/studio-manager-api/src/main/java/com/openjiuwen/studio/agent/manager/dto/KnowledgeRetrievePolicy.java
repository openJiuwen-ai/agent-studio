/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;

import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 知识检索策略。
 */
@ApiModel(description = "知识检索策略。")

@Validated

public class KnowledgeRetrievePolicy implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("search_mode")
    @Schema(description = "知识库检索模式：doc-语义检索、keyword-关键词检索、mix-混合检索", example = "doc")
    private SearchModeEnum searchMode = SearchModeEnum.DOC;

    @JsonProperty("top_k")
    @Range(min = 1L, max = 50L)
    @Schema(description = "检索返回的 Top-K 数量，取值范围 1~50", example = "5")
    private Integer topK = 5;

    @JsonProperty("recall_threshold")
    @Schema(description = "语义检索召回阈值，取值范围 0~1，低于此阈值的结果将被过滤", example = "0.5")
    private Float recallThreshold = 0.5f;

    @JsonProperty("faq_threshold")
    @Schema(description = "FAQ 检索匹配阈值，取值范围 0~1", example = "0.9")
    private Float faqThreshold = 0.9f;

    @JsonProperty("need_extras_faq_search")
    @Schema(description = "是否在语义检索结果不足时额外执行 FAQ 检索", example = "false")
    private Boolean needExtrasFaqSearch = false;

    @JsonProperty("show_source")
    @Schema(description = "是否在回答中展示知识来源引用", example = "true")
    private Boolean showSource = null;

    @JsonProperty("retrieve_image")
    @Schema(description = "是否检索图片内容", example = "false")
    private Boolean retrieveImage = false;


    public SearchModeEnum getSearchMode() {
        return searchMode;
    }

    public KnowledgeRetrievePolicy setSearchMode(SearchModeEnum searchMode) {
        this.searchMode = searchMode;
        return this;
    }

    public Integer getTopK() {
        return topK;
    }

    public KnowledgeRetrievePolicy setTopK(Integer topK) {
        this.topK = topK;
        return this;
    }

    public Float getRecallThreshold() {
        return recallThreshold;
    }

    public KnowledgeRetrievePolicy setRecallThreshold(Float recallThreshold) {
        this.recallThreshold = recallThreshold;
        return this;
    }

    public Float getFaqThreshold() {
        return faqThreshold;
    }

    public KnowledgeRetrievePolicy setFaqThreshold(Float faqThreshold) {
        this.faqThreshold = faqThreshold;
        return this;
    }

    public KnowledgeRetrievePolicy setNeedExtrasFaqSearch(Boolean needExtrasFaqSearch) {
        this.needExtrasFaqSearch = needExtrasFaqSearch;
        return this;
    }

    public Boolean isNeedExtrasFaqSearch() {
        return needExtrasFaqSearch;
    }

    public KnowledgeRetrievePolicy setShowSource(Boolean showSource) {
        this.showSource = showSource;
        return this;
    }

    public Boolean isShowSource() {
        return showSource;
    }

    public KnowledgeRetrievePolicy setRetrieveImage(Boolean retrieveImage) {
        this.retrieveImage = retrieveImage;
        return this;
    }

    public Boolean isRetrieveImage() {
        return retrieveImage;
    }


    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class KnowledgeRetrievePolicy {\n");

        sb.append("    searchMode: ").append(toIndentedString(searchMode)).append("\n");
        sb.append("    topK: ").append(toIndentedString(topK)).append("\n");
        sb.append("    recallThreshold: ").append(toIndentedString(recallThreshold)).append("\n");
        sb.append("    faqThreshold: ").append(toIndentedString(faqThreshold)).append("\n");
        sb.append("    needExtrasFaqSearch: ").append(toIndentedString(needExtrasFaqSearch)).append("\n");
        sb.append("    showSource: ").append(toIndentedString(showSource)).append("\n");
        sb.append("    retrieveImage: ").append(toIndentedString(retrieveImage)).append("\n");
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
        KnowledgeRetrievePolicy knowledgeRetrievePolicy = (KnowledgeRetrievePolicy) o;
        return Objects.equals(this.searchMode, knowledgeRetrievePolicy.searchMode) && Objects.equals(this.topK,
            knowledgeRetrievePolicy.topK) && Objects.equals(this.recallThreshold,
            knowledgeRetrievePolicy.recallThreshold) && Objects.equals(this.faqThreshold,
            knowledgeRetrievePolicy.faqThreshold) && Objects.equals(this.needExtrasFaqSearch,
            knowledgeRetrievePolicy.needExtrasFaqSearch) && Objects.equals(this.showSource,
            knowledgeRetrievePolicy.showSource) && Objects.equals(this.retrieveImage,
            knowledgeRetrievePolicy.retrieveImage);
    }

    @Override
    public int hashCode() {
        return Objects.hash(searchMode, topK, recallThreshold, faqThreshold, needExtrasFaqSearch, showSource,
            retrieveImage);
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

    /**
     * 知识库检索模式，对应三种取值： - doc：语义检索，使用向量检索技术 - keyword：关键词检索，使用倒排检索技术 - mix：混合检索，使用向量检索和关键词检索混合检索
     */
    public enum SearchModeEnum {
        DOC("doc"),

        KEYWORD("keyword"),

        MIX("mix");

        private String value;

        SearchModeEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static SearchModeEnum fromValue(String text) {
            for (SearchModeEnum b : SearchModeEnum.values()) {
                if (String.valueOf(b.value).equals(text)) {
                    return b;
                }
            }
            return null;
        }

        @Override
        @JsonValue
        public String toString() {
            return String.valueOf(value);
        }
    }
}
