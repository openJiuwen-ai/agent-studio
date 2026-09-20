/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 保存评估结果
 */
@ApiModel(description = "保存评估结果")

@Validated
public class PeEvalResult implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("score")
    @Schema(description = "评分", example = "85")
    private Integer score = null;

    @JsonProperty("time")
    @Schema(description = "时间", example = "1.5")
    private Double time = null;

    @JsonProperty("token")
    @Schema(description = "Token数量", example = "1024")
    private Integer token = null;

    public Integer getScore() {
        return score;
    }

    public PeEvalResult setScore(Integer score) {
        this.score = score;
        return this;
    }

    public Double getTime() {
        return time;
    }

    public PeEvalResult setTime(Double time) {
        this.time = time;
        return this;
    }

    public Integer getToken() {
        return token;
    }

    public PeEvalResult setToken(Integer token) {
        this.token = token;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PeEvalResult {\n");
        sb.append("    score: ").append(toIndentedString(score)).append("\n");
        sb.append("    time: ").append(toIndentedString(time)).append("\n");
        sb.append("    token: ").append(toIndentedString(token)).append("\n");
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
        PeEvalResult peEvalResult = (PeEvalResult) o;
        return Objects.equals(this.score, peEvalResult.score) && Objects.equals(this.time, peEvalResult.time)
            && Objects.equals(this.token, peEvalResult.token);
    }

    @Override
    public int hashCode() {
        return Objects.hash(score, time, token);
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
