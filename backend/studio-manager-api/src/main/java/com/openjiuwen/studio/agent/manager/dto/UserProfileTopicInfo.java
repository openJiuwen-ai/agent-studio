/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 用户画像记忆主题信息。
 */
@ApiModel(description = "用户画像记忆主题信息。")

@Validated

public class UserProfileTopicInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("topic_name")
    @Schema(description = "主题名称", example = "示例名称", required = true)
    @NotBlank
    @Length(max = 100)
    private String topicName = null;

    @JsonProperty("topic_description")
    @Schema(description = "主题", example = "示例描述")
    @Length(max = 500)
    private String topicDescription = null;

    @JsonProperty("tags")
    @Schema(description = "标签列表", example = "[]")
    @Valid
    @Size(max = 30)
    private List<UserProfileTagInfo> tags = null;

    public String getTopicName() {
        return topicName;
    }

    public UserProfileTopicInfo setTopicName(String topicName) {
        this.topicName = topicName;
        return this;
    }

    public String getTopicDescription() {
        return topicDescription;
    }

    public UserProfileTopicInfo setTopicDescription(String topicDescription) {
        this.topicDescription = topicDescription;
        return this;
    }

    public List<UserProfileTagInfo> getTags() {
        return tags;
    }

    public UserProfileTopicInfo setTags(List<UserProfileTagInfo> tags) {
        this.tags = tags;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class UserProfileTopicInfo {\n");

        sb.append("    topicName: ").append(toIndentedString(topicName)).append("\n");
        sb.append("    topicDescription: ").append(toIndentedString(topicDescription)).append("\n");
        sb.append("    tags: ").append(toIndentedString(tags)).append("\n");
        sb.append("}");
        return sb.toString();
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj) {
            return true;
        }
        if (obj == null || getClass() != obj.getClass()) {
            return false;
        }
        UserProfileTopicInfo userProfileTopicInfo = (UserProfileTopicInfo) obj;
        return Objects.equals(this.topicName, userProfileTopicInfo.topicName) && Objects.equals(this.topicDescription,
            userProfileTopicInfo.topicDescription) && Objects.equals(this.tags, userProfileTopicInfo.tags);
    }

    @Override
    public int hashCode() {
        return Objects.hash(topicName, topicDescription, tags);
    }

    private String toIndentedString(Object obj) {
        if (obj == null) {
            return "null";
        }
        return obj.toString().replace("\n", "\n    ");
    }
}
