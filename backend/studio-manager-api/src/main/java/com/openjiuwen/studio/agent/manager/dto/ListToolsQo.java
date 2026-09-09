/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * ListToolsQo: converted from multi query params
 */
@ApiModel(description = "ListToolsQo: converted from multi query params")

@Validated

public class ListToolsQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws_001", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @NotBlank
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("offset")
    @Schema(description = "偏移量", example = "0")
    @Range(min = 0L, max = 10000L)
    private Integer offset = 0;

    @JsonProperty("limit")
    @Schema(description = "限制数量", example = "20")
    @Range(min = 1L, max = 1000L)
    private Integer limit = 1000;

    @JsonProperty("id")
    @Schema(description = "ID", example = "tool_001")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("ids")
    @Schema(description = "ID列表", example = "[]")
    @Valid
    @Size()
    private List<@Length() String> ids = null;

    @JsonProperty("en_name")
    @Schema(description = "英文名称", example = "my_tool")
    @Length(max = 64)
    private String enName = null;

    @JsonProperty("cn_name")
    @Schema(description = "中文名称", example = "我的工具")
    @Length(max = 64)
    private String cnName = null;

    @JsonProperty("desc")
    @Schema(description = "描述", example = "工具描述")
    @Length(max = 256)
    private String desc = null;

    @JsonProperty("type")
    @Schema(description = "类型", example = "plugin")
    @Length(max = 32)
    private String type = null;

    @JsonProperty("intf_type")
    @Schema(description = "接口类型", example = "rest")
    private String intfType = null;

    @JsonProperty("published")
    @Schema(description = "是否已发布", example = "true")
    private Boolean published = null;

    @JsonProperty("customize_node")
    @Schema(description = "是否自定义节点", example = "false")
    private Boolean customizeNode = null;

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "user_001")
    @Length(max = 64)
    private String creator = null;

    @JsonProperty("creator_id")
    @Schema(description = "创建者ID", example = "user_001")
    @Length(max = 64)
    private String creatorId = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListToolsQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public Integer getOffset() {
        return offset;
    }

    public ListToolsQo setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public ListToolsQo setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    public String getId() {
        return id;
    }

    public ListToolsQo setId(String id) {
        this.id = id;
        return this;
    }

    public List<String> getIds() {
        return ids;
    }

    public ListToolsQo setIds(List<String> ids) {
        this.ids = ids;
        return this;
    }

    public String getEnName() {
        return enName;
    }

    public ListToolsQo setEnName(String enName) {
        this.enName = enName;
        return this;
    }

    public String getCnName() {
        return cnName;
    }

    public ListToolsQo setCnName(String cnName) {
        this.cnName = cnName;
        return this;
    }

    public String getDesc() {
        return desc;
    }

    public ListToolsQo setDesc(String desc) {
        this.desc = desc;
        return this;
    }

    public String getType() {
        return type;
    }

    public ListToolsQo setType(String type) {
        this.type = type;
        return this;
    }

    public String getIntfType() {
        return intfType;
    }

    public ListToolsQo setIntfType(String intfType) {
        this.intfType = intfType;
        return this;
    }

    public ListToolsQo setPublished(Boolean published) {
        this.published = published;
        return this;
    }

    public Boolean isPublished() {
        return published;
    }

    public ListToolsQo setCustomizeNode(Boolean customizeNode) {
        this.customizeNode = customizeNode;
        return this;
    }

    public Boolean isCustomizeNode() {
        return customizeNode;
    }

    public String getCreator() {
        return creator;
    }

    public ListToolsQo setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getCreatorId() {
        return creatorId;
    }

    public ListToolsQo setCreatorId(String creatorId) {
        this.creatorId = creatorId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListToolsQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    offset: ").append(toIndentedString(offset)).append("\n");
        sb.append("    limit: ").append(toIndentedString(limit)).append("\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    ids: ").append(toIndentedString(ids)).append("\n");
        sb.append("    enName: ").append(toIndentedString(enName)).append("\n");
        sb.append("    cnName: ").append(toIndentedString(cnName)).append("\n");
        sb.append("    desc: ").append(toIndentedString(desc)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    intfType: ").append(toIndentedString(intfType)).append("\n");
        sb.append("    published: ").append(toIndentedString(published)).append("\n");
        sb.append("    customizeNode: ").append(toIndentedString(customizeNode)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    creatorId: ").append(toIndentedString(creatorId)).append("\n");
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
        ListToolsQo listToolsQo = (ListToolsQo) o;
        return Objects.equals(this.workspaceId, listToolsQo.workspaceId) && Objects.equals(this.offset,
            listToolsQo.offset) && Objects.equals(this.limit, listToolsQo.limit) && Objects.equals(this.id,
            listToolsQo.id) && Objects.equals(this.ids, listToolsQo.ids) && Objects.equals(this.enName,
            listToolsQo.enName) && Objects.equals(this.cnName, listToolsQo.cnName) && Objects.equals(this.desc,
            listToolsQo.desc) && Objects.equals(this.type, listToolsQo.type) && Objects.equals(this.intfType,
            listToolsQo.intfType) && Objects.equals(this.published, listToolsQo.published) && Objects.equals(
            this.customizeNode, listToolsQo.customizeNode) && Objects.equals(this.creator, listToolsQo.creator)
            && Objects.equals(this.creatorId, listToolsQo.creatorId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, offset, limit, id, ids, enName, cnName, desc, type, intfType, published,
            customizeNode, creator, creatorId);
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
