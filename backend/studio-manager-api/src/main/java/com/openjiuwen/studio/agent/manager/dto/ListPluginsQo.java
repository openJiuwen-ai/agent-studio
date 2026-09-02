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
 * ListPluginsQo: converted from multi query params
 */
@ApiModel(description = "ListPluginsQo: converted from multi query params")

@Validated

public class ListPluginsQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws-001", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @NotBlank
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("offset")
    @Schema(description = "分页偏移量", example = "0")
    @Range(min = 0L, max = 10000L)
    private Integer offset = 0;

    @JsonProperty("limit")
    @Schema(description = "每页数量限制", example = "1000")
    @Range(min = 1L, max = 1000L)
    private Integer limit = 1000;

    @JsonProperty("id")
    @Schema(description = "插件ID", example = "plugin-001")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("ids")
    @Schema(description = "插件ID列表", example = "[]")
    @Valid
    @Size()
    private List<@Length() String> ids = null;

    @JsonProperty("en_name")
    @Schema(description = "英文名称", example = "my-plugin")
    @Length(max = 64)
    private String enName = null;

    @JsonProperty("cn_name")
    @Schema(description = "中文名称", example = "我的插件")
    @Length(max = 64)
    private String cnName = null;

    @JsonProperty("desc")
    @Schema(description = "描述", example = "插件描述信息")
    @Length(max = 256)
    private String desc = null;

    @JsonProperty("type")
    @Schema(description = "插件类型", example = "tool")
    @Length(max = 32)
    private String type = null;

    @JsonProperty("intf_type")
    @Schema(description = "接口类型", example = "rest")
    @Length(max = 32)
    private String intfType = null;

    @JsonProperty("call_mode")
    @Schema(description = "调用方式", example = "sync")
    @Length(max = 32)
    private String callMode = null;

    @JsonProperty("published")
    @Schema(description = "是否已发布", example = "true")
    private Boolean published = null;

    @JsonProperty("customize_node")
    @Schema(description = "是否为自定义节点", example = "false")
    private Boolean customizeNode = null;

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "admin")
    @Length(max = 64)
    private String creator = null;

    @JsonProperty("creator_id")
    @Schema(description = "创建者ID", example = "user-001")
    @Length(max = 64)
    private String creatorId = null;

    @JsonProperty("entry_point")
    @Schema(description = "入口点", example = "/api/plugin")
    private String entryPoint = null;

    @JsonProperty("label")
    @Schema(description = "标签", example = "utility")
    @Length(max = 32)
    private String label = null;

    @JsonProperty("category")
    @Schema(description = "分类", example = "general")
    private String category = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListPluginsQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public Integer getOffset() {
        return offset;
    }

    public ListPluginsQo setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public ListPluginsQo setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    public String getId() {
        return id;
    }

    public ListPluginsQo setId(String id) {
        this.id = id;
        return this;
    }

    public List<String> getIds() {
        return ids;
    }

    public ListPluginsQo setIds(List<String> ids) {
        this.ids = ids;
        return this;
    }

    public String getEnName() {
        return enName;
    }

    public ListPluginsQo setEnName(String enName) {
        this.enName = enName;
        return this;
    }

    public String getCnName() {
        return cnName;
    }

    public ListPluginsQo setCnName(String cnName) {
        this.cnName = cnName;
        return this;
    }

    public String getDesc() {
        return desc;
    }

    public ListPluginsQo setDesc(String desc) {
        this.desc = desc;
        return this;
    }

    public String getType() {
        return type;
    }

    public ListPluginsQo setType(String type) {
        this.type = type;
        return this;
    }

    public String getIntfType() {
        return intfType;
    }

    public ListPluginsQo setIntfType(String intfType) {
        this.intfType = intfType;
        return this;
    }

    public String getCallMode() {
        return callMode;
    }

    public ListPluginsQo setCallMode(String callMode) {
        this.callMode = callMode;
        return this;
    }

    public ListPluginsQo setPublished(Boolean published) {
        this.published = published;
        return this;
    }

    public Boolean isPublished() {
        return published;
    }

    public ListPluginsQo setCustomizeNode(Boolean customizeNode) {
        this.customizeNode = customizeNode;
        return this;
    }

    public Boolean isCustomizeNode() {
        return customizeNode;
    }

    public String getCreator() {
        return creator;
    }

    public ListPluginsQo setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getCreatorId() {
        return creatorId;
    }

    public ListPluginsQo setCreatorId(String creatorId) {
        this.creatorId = creatorId;
        return this;
    }

    public String getEntryPoint() {
        return entryPoint;
    }

    public ListPluginsQo setEntryPoint(String entryPoint) {
        this.entryPoint = entryPoint;
        return this;
    }

    public String getLabel() {
        return label;
    }

    public ListPluginsQo setLabel(String label) {
        this.label = label;
        return this;
    }

    public String getCategory() {
        return category;
    }

    public ListPluginsQo setCategory(String category) {
        this.category = category;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListPluginsQo {\n");

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
        sb.append("    callMode: ").append(toIndentedString(callMode)).append("\n");
        sb.append("    published: ").append(toIndentedString(published)).append("\n");
        sb.append("    customizeNode: ").append(toIndentedString(customizeNode)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    creatorId: ").append(toIndentedString(creatorId)).append("\n");
        sb.append("    entryPoint: ").append(toIndentedString(entryPoint)).append("\n");
        sb.append("    label: ").append(toIndentedString(label)).append("\n");
        sb.append("    category: ").append(toIndentedString(category)).append("\n");
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
        ListPluginsQo listPluginsQo = (ListPluginsQo) o;
        return Objects.equals(this.workspaceId, listPluginsQo.workspaceId) && Objects.equals(this.offset,
            listPluginsQo.offset) && Objects.equals(this.limit, listPluginsQo.limit) && Objects.equals(this.id,
            listPluginsQo.id) && Objects.equals(this.ids, listPluginsQo.ids) && Objects.equals(this.enName,
            listPluginsQo.enName) && Objects.equals(this.cnName, listPluginsQo.cnName) && Objects.equals(this.desc,
            listPluginsQo.desc) && Objects.equals(this.type, listPluginsQo.type) && Objects.equals(this.intfType,
            listPluginsQo.intfType) && Objects.equals(this.callMode, listPluginsQo.callMode) && Objects.equals(
            this.published, listPluginsQo.published) && Objects.equals(this.customizeNode, listPluginsQo.customizeNode)
            && Objects.equals(this.creator, listPluginsQo.creator) && Objects.equals(this.creatorId,
            listPluginsQo.creatorId) && Objects.equals(this.entryPoint, listPluginsQo.entryPoint) && Objects.equals(
            this.label, listPluginsQo.label) && Objects.equals(this.category, listPluginsQo.category);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, offset, limit, id, ids, enName, cnName, desc, type, intfType, callMode,
            published, customizeNode, creator, creatorId, entryPoint, label, category);
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
