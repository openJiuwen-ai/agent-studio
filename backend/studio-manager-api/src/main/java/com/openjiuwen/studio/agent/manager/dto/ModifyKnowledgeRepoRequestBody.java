/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.openjiuwen.studio.agent.common.annotation.ValidKnowledgeBaseName;
import com.openjiuwen.studio.agent.common.dto.knowledge.ParseConf;
import com.openjiuwen.studio.agent.common.dto.knowledge.SplitConf;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 修改知识库的请求体
 */
@ApiModel(description = "修改知识库的请求体")

@Validated

public class ModifyKnowledgeRepoRequestBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("display_name")
    @Schema(description = "显示名称", example = "我的知识库", required = true)
    @ValidKnowledgeBaseName
    @NotBlank
    @Length(min = 1, max = 50)
    private String displayName = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "知识库描述", required = true)
    @NotBlank
    @Length(max = 100)
    private String description = null;

    @JsonProperty("icon")
    @Schema(description = "图标", example = "base64encodedimage")
    @Length(max = 1024000)
    private String icon = null;

    @JsonProperty("rerank_model")
    @Schema(description = "重排序模型配置", example = "{}")
    @Valid
    private ModelConf rerankModel = null;

    @JsonProperty("parse_conf")
    @Schema(description = "解析配置", example = "{}")
    @Valid
    private ParseConf parseConf = null;

    @JsonProperty("split_conf")
    @Schema(description = "分割配置", example = "{}")
    @Valid
    private SplitConf splitConf = null;

    @JsonProperty("metadata")
    @Schema(description = "元数据", example = "{}")
    @Length(max = 4096)
    private String metadata = null;

    @JsonProperty("rag_chunk_parser_conf")
    @Schema(description = "RAG分块解析配置", example = "{}")
    @Valid
    private RagChunkParserConf ragChunkParserConf = null;

    public String getDisplayName() {
        return displayName;
    }

    public ModifyKnowledgeRepoRequestBody setDisplayName(String displayName) {
        this.displayName = displayName;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ModifyKnowledgeRepoRequestBody setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public ModifyKnowledgeRepoRequestBody setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public ModelConf getRerankModel() {
        return rerankModel;
    }

    public ModifyKnowledgeRepoRequestBody setRerankModel(ModelConf rerankModel) {
        this.rerankModel = rerankModel;
        return this;
    }

    public ParseConf getParseConf() {
        return parseConf;
    }

    public ModifyKnowledgeRepoRequestBody setParseConf(ParseConf parseConf) {
        this.parseConf = parseConf;
        return this;
    }

    public SplitConf getSplitConf() {
        return splitConf;
    }

    public ModifyKnowledgeRepoRequestBody setSplitConf(SplitConf splitConf) {
        this.splitConf = splitConf;
        return this;
    }

    public String getMetadata() {
        return metadata;
    }

    public ModifyKnowledgeRepoRequestBody setMetadata(String metadata) {
        this.metadata = metadata;
        return this;
    }

    public RagChunkParserConf getRagChunkParserConf() {
        return ragChunkParserConf;
    }

    public ModifyKnowledgeRepoRequestBody setRagChunkParserConf(RagChunkParserConf ragChunkParserConf) {
        this.ragChunkParserConf = ragChunkParserConf;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ModifyKnowledgeRepoRequestBody {\n");

        sb.append("    displayName: ").append(toIndentedString(displayName)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    rerankModel: ").append(toIndentedString(rerankModel)).append("\n");
        sb.append("    parseConf: ").append(toIndentedString(parseConf)).append("\n");
        sb.append("    splitConf: ").append(toIndentedString(splitConf)).append("\n");
        sb.append("    metadata: ").append(toIndentedString(metadata)).append("\n");
        sb.append("    ragChunkParserConf: ").append(toIndentedString(ragChunkParserConf)).append("\n");
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
        ModifyKnowledgeRepoRequestBody modifyKnowledgeRepoRequestBody = (ModifyKnowledgeRepoRequestBody) o;
        return Objects.equals(this.displayName, modifyKnowledgeRepoRequestBody.displayName) && Objects.equals(
            this.description, modifyKnowledgeRepoRequestBody.description) && Objects.equals(this.icon,
            modifyKnowledgeRepoRequestBody.icon) && Objects.equals(this.rerankModel,
            modifyKnowledgeRepoRequestBody.rerankModel) && Objects.equals(this.parseConf,
            modifyKnowledgeRepoRequestBody.parseConf) && Objects.equals(this.splitConf,
            modifyKnowledgeRepoRequestBody.splitConf) && Objects.equals(this.metadata,
            modifyKnowledgeRepoRequestBody.metadata) && Objects.equals(this.ragChunkParserConf,
            modifyKnowledgeRepoRequestBody.ragChunkParserConf);
    }

    @Override
    public int hashCode() {
        return Objects.hash(displayName, description, icon, rerankModel, parseConf, splitConf, metadata,
            ragChunkParserConf);
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
