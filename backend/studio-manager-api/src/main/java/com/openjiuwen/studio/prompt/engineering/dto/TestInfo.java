/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 测试用例相关信息
 */
@ApiModel(description = "测试用例相关信息")

@Validated
public class TestInfo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    @Pattern(regexp = "(^$)|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    private String id = null;

    @JsonProperty("question")
    @Schema(description = "问题", example = "示例问题", required = true)
    @NotBlank
    @Length(max = 512)
    private String question = null;

    @JsonProperty("standard_answer")
    @Schema(description = "标准答案", example = "示例文本", required = true)
    @NotBlank
    @Length(max = 512)
    private String standardAnswer = null;

    @JsonProperty("set_id")
    @Schema(description = "集合标识", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    @Pattern(regexp = "(^$)|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    private String setId = null;

    public String getId() {
        return id;
    }

    public TestInfo setId(String id) {
        this.id = id;
        return this;
    }

    public String getQuestion() {
        return question;
    }

    public TestInfo setQuestion(String question) {
        this.question = question;
        return this;
    }

    public String getStandardAnswer() {
        return standardAnswer;
    }

    public TestInfo setStandardAnswer(String standardAnswer) {
        this.standardAnswer = standardAnswer;
        return this;
    }

    public String getSetId() {
        return setId;
    }

    public TestInfo setSetId(String setId) {
        this.setId = setId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class TestInfo {\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    question: ").append(toIndentedString(question)).append("\n");
        sb.append("    standardAnswer: ").append(toIndentedString(standardAnswer)).append("\n");
        sb.append("    setId: ").append(toIndentedString(setId)).append("\n");
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
        TestInfo testInfo = (TestInfo) o;
        return Objects.equals(this.id, testInfo.id) && Objects.equals(this.question, testInfo.question)
            && Objects.equals(this.standardAnswer, testInfo.standardAnswer) && Objects.equals(this.setId,
            testInfo.setId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, question, standardAnswer, setId);
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
