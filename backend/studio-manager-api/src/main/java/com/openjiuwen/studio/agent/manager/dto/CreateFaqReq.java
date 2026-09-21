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
 * 创建FAQ问答对请求体
 */
@ApiModel(description = "创建FAQ问答对请求体")

@Validated

public class CreateFaqReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("question")
    @Schema(description = "问题", example = "如何重置密码？", required = true)
    @NotBlank
    @Length(min = 1, max = 1000)
    private String question = null;

    @JsonProperty("answer")
    @Schema(description = "答案", example = "请点击设置中的重置密码按钮。", required = true)
    @NotBlank
    @Length(min = 1, max = 10000)
    private String answer = null;

    @JsonProperty("question1")
    @Schema(description = "相似问题1", example = "密码怎么重置？")
    @Length(max = 1000)
    private String question1 = null;

    @JsonProperty("question2")
    @Schema(description = "相似问题2", example = "忘记密码怎么办？")
    @Length(max = 1000)
    private String question2 = null;

    @JsonProperty("question3")
    @Schema(description = "相似问题3", example = "如何修改密码？")
    @Length(max = 1000)
    private String question3 = null;

    @JsonProperty("question4")
    @Schema(description = "相似问题4", example = "密码如何找回？")
    @Length(max = 1000)
    private String question4 = null;

    @JsonProperty("category")
    @Schema(description = "分类", example = "账号管理")
    @Length(max = 255)
    private String category = null;

    @JsonProperty("tags")
    @Schema(description = "标签", example = "密码,账号")
    @Length(max = 4096)
    private String tags = null;

    public String getQuestion() {
        return question;
    }

    public CreateFaqReq setQuestion(String question) {
        this.question = question;
        return this;
    }

    public String getAnswer() {
        return answer;
    }

    public CreateFaqReq setAnswer(String answer) {
        this.answer = answer;
        return this;
    }

    public String getQuestion1() {
        return question1;
    }

    public CreateFaqReq setQuestion1(String question1) {
        this.question1 = question1;
        return this;
    }

    public String getQuestion2() {
        return question2;
    }

    public CreateFaqReq setQuestion2(String question2) {
        this.question2 = question2;
        return this;
    }

    public String getQuestion3() {
        return question3;
    }

    public CreateFaqReq setQuestion3(String question3) {
        this.question3 = question3;
        return this;
    }

    public String getQuestion4() {
        return question4;
    }

    public CreateFaqReq setQuestion4(String question4) {
        this.question4 = question4;
        return this;
    }

    public String getCategory() {
        return category;
    }

    public CreateFaqReq setCategory(String category) {
        this.category = category;
        return this;
    }

    public String getTags() {
        return tags;
    }

    public CreateFaqReq setTags(String tags) {
        this.tags = tags;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreateFaqReq {\n");

        sb.append("    question: ").append(toIndentedString(question)).append("\n");
        sb.append("    answer: ").append(toIndentedString(answer)).append("\n");
        sb.append("    question1: ").append(toIndentedString(question1)).append("\n");
        sb.append("    question2: ").append(toIndentedString(question2)).append("\n");
        sb.append("    question3: ").append(toIndentedString(question3)).append("\n");
        sb.append("    question4: ").append(toIndentedString(question4)).append("\n");
        sb.append("    category: ").append(toIndentedString(category)).append("\n");
        sb.append("    tags: ").append(toIndentedString(tags)).append("\n");
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
        CreateFaqReq createFaqReq = (CreateFaqReq) o;
        return Objects.equals(this.question, createFaqReq.question) && Objects.equals(this.answer, createFaqReq.answer)
            && Objects.equals(this.question1, createFaqReq.question1) && Objects.equals(this.question2,
            createFaqReq.question2) && Objects.equals(this.question3, createFaqReq.question3) && Objects.equals(
            this.question4, createFaqReq.question4) && Objects.equals(this.category, createFaqReq.category)
            && Objects.equals(this.tags, createFaqReq.tags);
    }

    @Override
    public int hashCode() {
        return Objects.hash(question, answer, question1, question2, question3, question4, category, tags);
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
