/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Date;
import java.util.Objects;

/**
 * ActionOrTriggerBaseInfo
 */

@Validated

public class ActionOrTriggerBaseInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识ID", example = "action_001")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "发送邮件")
    @Length(max = 128)
    private String name = null;

    @JsonProperty("created_time")
    @Schema(description = "创建时间", example = "2026-01-01T10:00:00Z")
    private Date createdTime = null;

    @JsonProperty("updated_time")
    @Schema(description = "更新时间", example = "2026-01-01T12:00:00Z")
    private Date updatedTime = null;

    public String getId() {
        return id;
    }

    public ActionOrTriggerBaseInfo setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public ActionOrTriggerBaseInfo setName(String name) {
        this.name = name;
        return this;
    }

    public Date getCreatedTime() {
        return createdTime;
    }

    public ActionOrTriggerBaseInfo setCreatedTime(Date createdTime) {
        this.createdTime = createdTime;
        return this;
    }

    public Date getUpdatedTime() {
        return updatedTime;
    }

    public ActionOrTriggerBaseInfo setUpdatedTime(Date updatedTime) {
        this.updatedTime = updatedTime;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ActionOrTriggerBaseInfo {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    createdTime: ").append(toIndentedString(createdTime)).append("\n");
        sb.append("    updatedTime: ").append(toIndentedString(updatedTime)).append("\n");
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
        ActionOrTriggerBaseInfo actionOrTriggerBaseInfo = (ActionOrTriggerBaseInfo) o;
        return Objects.equals(this.id, actionOrTriggerBaseInfo.id) && Objects.equals(this.name,
            actionOrTriggerBaseInfo.name) && Objects.equals(this.createdTime, actionOrTriggerBaseInfo.createdTime)
            && Objects.equals(this.updatedTime, actionOrTriggerBaseInfo.updatedTime);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, createdTime, updatedTime);
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
