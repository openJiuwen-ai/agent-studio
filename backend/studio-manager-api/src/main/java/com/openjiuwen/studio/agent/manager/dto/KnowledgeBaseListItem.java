/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Pattern;
import lombok.Data;
import lombok.experimental.Accessors;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;

/**
 * 知识库列表中的信息
 */
@ApiModel(description = "知识库列表中的信息")

@Validated
@Data
@Accessors(chain = true)
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class KnowledgeBaseListItem implements Serializable {
    private static final long serialVersionUID = 1L;

    @Schema(description = "知识库ID", example = "kb-001")
    @Length(max = 64)
    private String knowledgeBaseId = null;

    @Schema(description = "知识库图标", example = "data:image/png;base64,...")
    @Length(max = 1024000)
    private String icon = null;

    @Schema(description = "知识库类型，share-共享，exclusive-专享", example = "share")
    private RepoTypeEnum repoType = null;

    @Schema(description = "知识库来源类型，internal-默认，external-第三方知识库", example = "internal")
    private TypeEnum type = null;

    @Schema(description = "工作空间ID", example = "ws-001")
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @Length(max = 64)
    private String workspaceId = null;

    @Schema(description = "知识库可见范围，SELF/GLOBAL/ALL/PARTIAL", example = "SELF")
    private ShareScopeEnum shareScope = null;

    @Schema(description = "外部知识库来源信息", example = "{}")
    @Valid
    private ExternalKnowledgeBaseSource source = null;

    @Schema(description = "知识库名称", example = "产品知识库")
    @Length(max = 64)
    private String name = null;

    @Schema(description = "知识库描述", example = "存储产品相关文档和FAQ")
    @Length(max = 100)
    private String description = null;

    @Schema(description = "知识库状态，OPEN-启用，CLOSE-停用", example = "OPEN")
    private StatusEnum status = null;

    @Schema(description = "创建者用户ID", example = "user-001")
    @Length(max = 100)
    private String createdUserId = null;

    @Schema(description = "创建者用户名", example = "张三")
    @Length(max = 100)
    private String createdUserName = null;

    @Schema(description = "创建时间（毫秒时间戳）", example = "1717200000000")
    @Range(min = 0L, max = 253402214400000L)
    private Long createTime = null;

    @Schema(description = "最后更新者用户ID", example = "user-002")
    @Length(max = 100)
    private String lastUpdateUserId = null;

    @Schema(description = "最后更新者用户名", example = "李四")
    @Length(max = 100)
    private String lastUpdateUserName = null;

    @Schema(description = "更新时间（毫秒时间戳）", example = "1717286400000")
    @Range(min = 0L, max = 253402214400000L)
    private Long updateTime = null;

    @Schema(description = "知识库连接ID", example = "conn-001")
    @Length(max = 64)
    private String knowledgeBaseConnectionId = null;

    /**
     * 知识库类型 - share：共享 - exclusive：专享
     */
    public enum RepoTypeEnum {
        SHARE("share"),

        EXCLUSIVE("exclusive");

        private String value;

        RepoTypeEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static RepoTypeEnum fromValue(String text) {
            for (RepoTypeEnum b : RepoTypeEnum.values()) {
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
     * 知识库类型，internal-默认，external-第三方知识库
     */
    public enum TypeEnum {
        INTERNAL("internal"),

        EXTERNAL("external");

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

        ALL("ALL"),

        PARTIAL("PARTIAL");

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

    /**
     * 知识库状态，OPEN-启用，CLOSE-停用
     */
    public enum StatusEnum {
        OPEN("OPEN"),

        CLOSE("CLOSE");

        private String value;

        StatusEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static StatusEnum fromValue(String text) {
            for (StatusEnum b : StatusEnum.values()) {
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
