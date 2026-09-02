/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Date;
import java.util.Objects;

/**
 * 自定义对象信息结果
 */
@ApiModel(description = "自定义对象信息结果")

@Validated

public class ObjectRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "对象ID", example = "obj_001")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("project_id")
    @Schema(description = "项目ID", example = "proj_001")
    @Length(max = 64)
    private String projectId = null;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws_001")
    @Length(max = 64)
    private String workspaceId = null;

    @JsonProperty("name")
    @Schema(description = "对象名称", example = "my_object")
    @Length(max = 64)
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "对象描述", example = "自定义对象")
    @Length(max = 1024)
    private String description = null;

    @JsonProperty("schemas")
    @Schema(description = "对象Schema定义", example = "{}")
    private String schemas = null;

    @JsonProperty("creator_id")
    @Schema(description = "创建者ID", example = "user_001")
    @Length(max = 1024)
    private String creatorId = null;

    @JsonProperty("update_time")
    @Schema(description = "更新时间", example = "2026-01-01T00:00:00Z")
    private Date updateTime = null;

    public String getId() {
        return id;
    }

    public ObjectRsp setId(String id) {
        this.id = id;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public ObjectRsp setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ObjectRsp setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getName() {
        return name;
    }

    public ObjectRsp setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ObjectRsp setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getSchemas() {
        return schemas;
    }

    public ObjectRsp setSchemas(String schemas) {
        this.schemas = schemas;
        return this;
    }

    public String getCreatorId() {
        return creatorId;
    }

    public ObjectRsp setCreatorId(String creatorId) {
        this.creatorId = creatorId;
        return this;
    }

    public Date getUpdateTime() {
        return updateTime;
    }

    public ObjectRsp setUpdateTime(Date updateTime) {
        this.updateTime = updateTime;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ObjectRsp {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    schemas: ").append(toIndentedString(schemas)).append("\n");
        sb.append("    creatorId: ").append(toIndentedString(creatorId)).append("\n");
        sb.append("    updateTime: ").append(toIndentedString(updateTime)).append("\n");
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
        ObjectRsp objectRsp = (ObjectRsp) o;
        return Objects.equals(this.id, objectRsp.id) && Objects.equals(this.projectId, objectRsp.projectId)
            && Objects.equals(this.workspaceId, objectRsp.workspaceId) && Objects.equals(this.name, objectRsp.name)
            && Objects.equals(this.description, objectRsp.description) && Objects.equals(this.schemas,
            objectRsp.schemas) && Objects.equals(this.creatorId, objectRsp.creatorId) && Objects.equals(this.updateTime,
            objectRsp.updateTime);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, projectId, workspaceId, name, description, schemas, creatorId, updateTime);
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
