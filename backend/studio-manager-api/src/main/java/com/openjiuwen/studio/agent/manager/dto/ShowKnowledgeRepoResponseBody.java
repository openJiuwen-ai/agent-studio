/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;
import com.openjiuwen.studio.agent.common.dto.knowledge.ParseConf;
import com.openjiuwen.studio.agent.common.dto.knowledge.SplitConf;
import com.openjiuwen.studio.agent.manager.dto.ExternalKnowledgeBaseSource;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 知识库，包含若干文档
 */
@ApiModel(description = "知识库，包含若干文档")

@Validated

public class ShowKnowledgeRepoResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("knowledge_repo_id")
    @Schema(description = "知识库ID", example = "knowledge-repo-001")
    @Length(min = 1, max = 64)
    private String knowledgeRepoId = null;

    @JsonProperty("project_id")
    @Schema(description = "项目ID", example = "project-001")
    @Length(min = 1, max = 64)
    private String projectId = null;

    @JsonProperty("display_name")
    @Schema(description = "知识库显示名称", example = "我的知识库", required = true)
    @NotBlank
    @Length(min = 1, max = 64)
    private String displayName = null;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "workspace-001")
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("description")
    @Schema(description = "知识库描述", example = "用于存储产品文档的知识库")
    @Length(max = 100)
    private String description = null;

    @JsonProperty("type")
    @Schema(description = "知识库类型，external表示外部引用，internal表示平台内部创建", example = "internal", required = true)
    @NotNull
    private TypeEnum type = null;

    @JsonProperty("repo_type")
    @Schema(description = "知识库来源类型", example = "external")
    @Length(min = 1, max = 32)
    private String repoType = null;

    @JsonProperty("size")
    @Schema(description = "知识库当前已用大小（字节）", example = "1024")
    @Range(min = 0L, max = 102400000000L)
    private Long size = null;

    @JsonProperty("max_size")
    @Schema(description = "知识库最大容量（字节）", example = "1073741824")
    @Range(min = 0L, max = 102400000000L)
    private Long maxSize = null;

    @JsonProperty("remain_size")
    @Schema(description = "知识库剩余可用空间（字节）", example = "1073740800")
    @Range(min = 0L, max = 102400000000L)
    private Long remainSize = null;

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "user001")
    @Length(max = 64)
    private String creator = null;

    @JsonProperty("update_user_name")
    @Schema(description = "最近更新者用户名", example = "user002")
    @Length(max = 64)
    private String updateUserName = null;

    @JsonProperty("parse_conf")
    @Schema(description = "文档解析配置", example = "{}")
    @Valid
    private ParseConf parseConf = null;

    @JsonProperty("split_conf")
    @Schema(description = "文档切分配置", example = "{}")
    @Valid
    private SplitConf splitConf = null;

    @JsonProperty("embedding_model")
    @Schema(description = "向量化模型名称", example = "text-embedding-ada-002")
    @Length(max = 32)
    private String embeddingModel = null;

    @JsonProperty("rerank_model")
    @Schema(description = "重排序模型名称", example = "rerank-model-001")
    @Length(max = 32)
    private String rerankModel = null;

    @JsonProperty("icon")
    @Schema(description = "知识库图标数据", example = "data:image/png;base64,iVBORw0KGgo=")
    @Length(max = 1024000)
    private String icon = null;

    @JsonProperty("icon_name")
    @Schema(description = "知识库图标名称", example = "icon.png")
    @Length(max = 64)
    private String iconName = null;

    @JsonProperty("status")
    @Schema(description = "知识库状态", example = "active")
    @Length(max = 16)
    private String status = null;

    @JsonProperty("metadata")
    @Schema(description = "知识库元数据", example = "{\"key\":\"value\"}")
    @Length(max = 4096)
    private String metadata = null;

    @JsonProperty("create_time")
    @Schema(description = "创建时间（毫秒时间戳）", example = "1714521600000")
    @Range(min = 0L, max = 253402214400000L)
    private Long createTime = null;

    @JsonProperty("update_time")
    @Schema(description = "更新时间（毫秒时间戳）", example = "1714608000000")
    @Range(min = 0L, max = 253402214400000L)
    private Long updateTime = null;

    @JsonProperty("rag_chunk_parser_conf")
    @Schema(description = "RAG分块解析配置", example = "{}")
    @Valid
    private RagChunkParserConf ragChunkParserConf = null;

    @JsonProperty("share_scope")
    @Schema(description = "知识库可见范围，可选值：SELF、GLOBAL、ALL", example = "GLOBAL")
    private ShareScopeEnum shareScope = ShareScopeEnum.GLOBAL;

    @JsonProperty("source")
    @Schema(description = "外部知识库来源信息", example = "{}")
    private ExternalKnowledgeBaseSource source = null;

    public String getKnowledgeRepoId() {
        return knowledgeRepoId;
    }

    public ShowKnowledgeRepoResponseBody setKnowledgeRepoId(String knowledgeRepoId) {
        this.knowledgeRepoId = knowledgeRepoId;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public ShowKnowledgeRepoResponseBody setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public String getDisplayName() {
        return displayName;
    }

    public ShowKnowledgeRepoResponseBody setDisplayName(String displayName) {
        this.displayName = displayName;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ShowKnowledgeRepoResponseBody setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ShowKnowledgeRepoResponseBody setDescription(String description) {
        this.description = description;
        return this;
    }

    public TypeEnum getType() {
        return type;
    }

    public ShowKnowledgeRepoResponseBody setType(TypeEnum type) {
        this.type = type;
        return this;
    }

    public String getRepoType() {
        return repoType;
    }

    public ShowKnowledgeRepoResponseBody setRepoType(String repoType) {
        this.repoType = repoType;
        return this;
    }

    public Long getSize() {
        return size;
    }

    public ShowKnowledgeRepoResponseBody setSize(Long size) {
        this.size = size;
        return this;
    }

    public Long getMaxSize() {
        return maxSize;
    }

    public ShowKnowledgeRepoResponseBody setMaxSize(Long maxSize) {
        this.maxSize = maxSize;
        return this;
    }

    public Long getRemainSize() {
        return remainSize;
    }

    public ShowKnowledgeRepoResponseBody setRemainSize(Long remainSize) {
        this.remainSize = remainSize;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public ShowKnowledgeRepoResponseBody setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getUpdateUserName() {
        return updateUserName;
    }

    public ShowKnowledgeRepoResponseBody setUpdateUserName(String updateUserName) {
        this.updateUserName = updateUserName;
        return this;
    }

    public ParseConf getParseConf() {
        return parseConf;
    }

    public ShowKnowledgeRepoResponseBody setParseConf(ParseConf parseConf) {
        this.parseConf = parseConf;
        return this;
    }

    public SplitConf getSplitConf() {
        return splitConf;
    }

    public ShowKnowledgeRepoResponseBody setSplitConf(SplitConf splitConf) {
        this.splitConf = splitConf;
        return this;
    }

    public String getEmbeddingModel() {
        return embeddingModel;
    }

    public ShowKnowledgeRepoResponseBody setEmbeddingModel(String embeddingModel) {
        this.embeddingModel = embeddingModel;
        return this;
    }

    public String getRerankModel() {
        return rerankModel;
    }

    public ShowKnowledgeRepoResponseBody setRerankModel(String rerankModel) {
        this.rerankModel = rerankModel;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public ShowKnowledgeRepoResponseBody setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public String getIconName() {
        return iconName;
    }

    public ShowKnowledgeRepoResponseBody setIconName(String iconName) {
        this.iconName = iconName;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public ShowKnowledgeRepoResponseBody setStatus(String status) {
        this.status = status;
        return this;
    }

    public String getMetadata() {
        return metadata;
    }

    public ShowKnowledgeRepoResponseBody setMetadata(String metadata) {
        this.metadata = metadata;
        return this;
    }

    public Long getCreateTime() {
        return createTime;
    }

    public ShowKnowledgeRepoResponseBody setCreateTime(Long createTime) {
        this.createTime = createTime;
        return this;
    }

    public Long getUpdateTime() {
        return updateTime;
    }

    public ShowKnowledgeRepoResponseBody setUpdateTime(Long updateTime) {
        this.updateTime = updateTime;
        return this;
    }

    public RagChunkParserConf getRagChunkParserConf() {
        return ragChunkParserConf;
    }

    public ShowKnowledgeRepoResponseBody setRagChunkParserConf(RagChunkParserConf ragChunkParserConf) {
        this.ragChunkParserConf = ragChunkParserConf;
        return this;
    }

    public ShareScopeEnum getShareScope() {
        return shareScope;
    }

    public ShowKnowledgeRepoResponseBody setShareScope(ShareScopeEnum shareScope) {
        this.shareScope = shareScope;
        return this;
    }

    public ExternalKnowledgeBaseSource getSource() {
        return source;
    }

    public ShowKnowledgeRepoResponseBody setSource(ExternalKnowledgeBaseSource source) {
        this.source = source;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ShowKnowledgeRepoResponseBody {\n");

        sb.append("    knowledgeRepoId: ").append(toIndentedString(knowledgeRepoId)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    displayName: ").append(toIndentedString(displayName)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    repoType: ").append(toIndentedString(repoType)).append("\n");
        sb.append("    size: ").append(toIndentedString(size)).append("\n");
        sb.append("    maxSize: ").append(toIndentedString(maxSize)).append("\n");
        sb.append("    remainSize: ").append(toIndentedString(remainSize)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    updateUserName: ").append(toIndentedString(updateUserName)).append("\n");
        sb.append("    parseConf: ").append(toIndentedString(parseConf)).append("\n");
        sb.append("    splitConf: ").append(toIndentedString(splitConf)).append("\n");
        sb.append("    embeddingModel: ").append(toIndentedString(embeddingModel)).append("\n");
        sb.append("    rerankModel: ").append(toIndentedString(rerankModel)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    iconName: ").append(toIndentedString(iconName)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    metadata: ").append(toIndentedString(metadata)).append("\n");
        sb.append("    createTime: ").append(toIndentedString(createTime)).append("\n");
        sb.append("    updateTime: ").append(toIndentedString(updateTime)).append("\n");
        sb.append("    ragChunkParserConf: ").append(toIndentedString(ragChunkParserConf)).append("\n");
        sb.append("    shareScope: ").append(toIndentedString(shareScope)).append("\n");
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
        ShowKnowledgeRepoResponseBody showKnowledgeRepoResponseBody = (ShowKnowledgeRepoResponseBody) o;
        return Objects.equals(this.knowledgeRepoId, showKnowledgeRepoResponseBody.knowledgeRepoId) && Objects.equals(
            this.projectId, showKnowledgeRepoResponseBody.projectId) && Objects.equals(this.displayName,
            showKnowledgeRepoResponseBody.displayName) && Objects.equals(this.workspaceId,
            showKnowledgeRepoResponseBody.workspaceId) && Objects.equals(this.description,
            showKnowledgeRepoResponseBody.description) && Objects.equals(this.type, showKnowledgeRepoResponseBody.type)
            && Objects.equals(this.repoType, showKnowledgeRepoResponseBody.repoType) && Objects.equals(this.size,
            showKnowledgeRepoResponseBody.size) && Objects.equals(this.maxSize, showKnowledgeRepoResponseBody.maxSize)
            && Objects.equals(this.remainSize, showKnowledgeRepoResponseBody.remainSize) && Objects.equals(this.creator,
            showKnowledgeRepoResponseBody.creator) && Objects.equals(this.updateUserName,
            showKnowledgeRepoResponseBody.updateUserName) && Objects.equals(this.parseConf,
            showKnowledgeRepoResponseBody.parseConf) && Objects.equals(this.splitConf,
            showKnowledgeRepoResponseBody.splitConf) && Objects.equals(this.embeddingModel,
            showKnowledgeRepoResponseBody.embeddingModel) && Objects.equals(this.rerankModel,
            showKnowledgeRepoResponseBody.rerankModel) && Objects.equals(this.icon, showKnowledgeRepoResponseBody.icon)
            && Objects.equals(this.iconName, showKnowledgeRepoResponseBody.iconName) && Objects.equals(this.status,
            showKnowledgeRepoResponseBody.status) && Objects.equals(this.metadata,
            showKnowledgeRepoResponseBody.metadata) && Objects.equals(this.createTime,
            showKnowledgeRepoResponseBody.createTime) && Objects.equals(this.updateTime,
            showKnowledgeRepoResponseBody.updateTime) && Objects.equals(this.ragChunkParserConf,
            showKnowledgeRepoResponseBody.ragChunkParserConf) && Objects.equals(this.shareScope,
            showKnowledgeRepoResponseBody.shareScope);
    }

    @Override
    public int hashCode() {
        return Objects.hash(knowledgeRepoId, projectId, displayName, workspaceId, description, type, repoType, size,
            maxSize, remainSize, creator, updateUserName, parseConf, splitConf, embeddingModel, rerankModel, icon,
            iconName, status, metadata, createTime, updateTime, ragChunkParserConf, shareScope);
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
     * 知识库类型，枚举，包括两种取值。 external：用户在知识库平台创建的知识库，在Agent平台中进行引用 internal：用户在Agent平台创建的知识库
     */
    public enum TypeEnum {
        EXTERNAL("external"),

        INTERNAL("internal");

        private String value;

        TypeEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static TypeEnum fromValue(String text) {
            for (TypeEnum b : TypeEnum.values()) {
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

    /**
     * 知识库可见范围 - SELF：当前空间下可见。 - GLOBAL：当前租户下共享。 - ALL：包含当前空间下可见与当前租户下共享。
     */
    public enum ShareScopeEnum {
        SELF("SELF"),

        GLOBAL("GLOBAL"),

        ALL("ALL");

        private String value;

        ShareScopeEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static ShareScopeEnum fromValue(String text) {
            for (ShareScopeEnum b : ShareScopeEnum.values()) {
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
