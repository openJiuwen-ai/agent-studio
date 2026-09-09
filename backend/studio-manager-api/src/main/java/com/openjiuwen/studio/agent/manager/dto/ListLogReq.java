/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ListLogReq
 */

@Validated

public class ListLogReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("startTime")
    @Schema(description = "查询开始时间", example = "2026-01-01T00:00:00Z")
    private String startTime = null;

    @JsonProperty("endTime")
    @Schema(description = "查询结束时间", example = "2026-01-01T23:59:59Z")
    private String endTime = null;

    @JsonProperty("keywords")
    @Schema(description = "搜索关键词", example = "error")
    @Length(max = 128)
    private String keywords = null;

    @JsonProperty("limit")
    @Schema(description = "返回条数限制", example = "100")
    @Length(max = 3)
    private String limit = null;

    @JsonProperty("lineNum")
    @Schema(description = "起始行号", example = "0")
    @Length(max = 32)
    private String lineNum = null;

    @JsonProperty("searchType")
    @Schema(description = "搜索类型", example = "forward")
    private String searchType = null;

    public String getStartTime() {
        return startTime;
    }

    public ListLogReq setStartTime(String startTime) {
        this.startTime = startTime;
        return this;
    }

    public String getEndTime() {
        return endTime;
    }

    public ListLogReq setEndTime(String endTime) {
        this.endTime = endTime;
        return this;
    }

    public String getKeywords() {
        return keywords;
    }

    public ListLogReq setKeywords(String keywords) {
        this.keywords = keywords;
        return this;
    }

    public String getLimit() {
        return limit;
    }

    public ListLogReq setLimit(String limit) {
        this.limit = limit;
        return this;
    }

    public String getLineNum() {
        return lineNum;
    }

    public ListLogReq setLineNum(String lineNum) {
        this.lineNum = lineNum;
        return this;
    }

    public String getSearchType() {
        return searchType;
    }

    public ListLogReq setSearchType(String searchType) {
        this.searchType = searchType;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListLogReq {\n");

        sb.append("    startTime: ").append(toIndentedString(startTime)).append("\n");
        sb.append("    endTime: ").append(toIndentedString(endTime)).append("\n");
        sb.append("    keywords: ").append(toIndentedString(keywords)).append("\n");
        sb.append("    limit: ").append(toIndentedString(limit)).append("\n");
        sb.append("    lineNum: ").append(toIndentedString(lineNum)).append("\n");
        sb.append("    searchType: ").append(toIndentedString(searchType)).append("\n");
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
        ListLogReq listLogReq = (ListLogReq) o;
        return Objects.equals(this.startTime, listLogReq.startTime) && Objects.equals(this.endTime, listLogReq.endTime)
            && Objects.equals(this.keywords, listLogReq.keywords) && Objects.equals(this.limit, listLogReq.limit)
            && Objects.equals(this.lineNum, listLogReq.lineNum) && Objects.equals(this.searchType,
            listLogReq.searchType);
    }

    @Override
    public int hashCode() {
        return Objects.hash(startTime, endTime, keywords, limit, lineNum, searchType);
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
