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
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 自研RAG知识库解析切片配置
 */
@ApiModel(description = "自研RAG知识库解析切片配置")

@Validated

public class RagChunkParserConf implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("chunk_method")
    @Schema(description = "切片方法", example = "naive")
    private ChunkMethodEnum chunkMethod = ChunkMethodEnum.NAIVE;

    @JsonProperty("auto_keywords")
    @Schema(description = "自动提取关键词数量", example = "3")
    @Range(min = 0L, max = 32L)
    private Integer autoKeywords = 0;

    @JsonProperty("auto_questions")
    @Schema(description = "自动提取问题数量", example = "2")
    @Range(min = 0L, max = 10L)
    private Integer autoQuestions = 0;

    @JsonProperty("chunk_token_num")
    @Schema(description = "切片Token数量", example = "512")
    @Range(min = 1L, max = 2048L)
    private Integer chunkTokenNum = 512;

    @JsonProperty("delimiter")
    @Schema(description = "分隔符列表", example = "[\"\\n\\n\"]")
    @Valid
    @Size(min = 1, max = 100)
    private List<@Length(min = 1, max = 128) String> delimiter = null;

    public ChunkMethodEnum getChunkMethod() {
        return chunkMethod;
    }

    public RagChunkParserConf setChunkMethod(ChunkMethodEnum chunkMethod) {
        this.chunkMethod = chunkMethod;
        return this;
    }

    public Integer getAutoKeywords() {
        return autoKeywords;
    }

    public RagChunkParserConf setAutoKeywords(Integer autoKeywords) {
        this.autoKeywords = autoKeywords;
        return this;
    }

    public Integer getAutoQuestions() {
        return autoQuestions;
    }

    public RagChunkParserConf setAutoQuestions(Integer autoQuestions) {
        this.autoQuestions = autoQuestions;
        return this;
    }

    public Integer getChunkTokenNum() {
        return chunkTokenNum;
    }

    public RagChunkParserConf setChunkTokenNum(Integer chunkTokenNum) {
        this.chunkTokenNum = chunkTokenNum;
        return this;
    }

    public List<String> getDelimiter() {
        return delimiter;
    }

    public RagChunkParserConf setDelimiter(List<String> delimiter) {
        this.delimiter = delimiter;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class RagChunkParserConf {\n");

        sb.append("    chunkMethod: ").append(toIndentedString(chunkMethod)).append("\n");
        sb.append("    autoKeywords: ").append(toIndentedString(autoKeywords)).append("\n");
        sb.append("    autoQuestions: ").append(toIndentedString(autoQuestions)).append("\n");
        sb.append("    chunkTokenNum: ").append(toIndentedString(chunkTokenNum)).append("\n");
        sb.append("    delimiter: ").append(toIndentedString(delimiter)).append("\n");
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
        RagChunkParserConf ragChunkParserConf = (RagChunkParserConf) o;
        return Objects.equals(this.chunkMethod, ragChunkParserConf.chunkMethod) && Objects.equals(this.autoKeywords,
            ragChunkParserConf.autoKeywords) && Objects.equals(this.autoQuestions, ragChunkParserConf.autoQuestions)
            && Objects.equals(this.chunkTokenNum, ragChunkParserConf.chunkTokenNum) && Objects.equals(this.delimiter,
            ragChunkParserConf.delimiter);
    }

    @Override
    public int hashCode() {
        return Objects.hash(chunkMethod, autoKeywords, autoQuestions, chunkTokenNum, delimiter);
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
     * 切片类型 - naive：通用 - qa：问答 - table：表格 - book：书籍 - laws：法律条文 - one：直接作为一个切片
     */
    public enum ChunkMethodEnum {
        NAIVE("naive"),

        QA("qa"),

        TABLE("table"),

        BOOK("book"),

        LAWS("laws"),

        ONE("one");

        private String value;

        ChunkMethodEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static ChunkMethodEnum fromValue(String text) {
            for (ChunkMethodEnum b : ChunkMethodEnum.values()) {
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
