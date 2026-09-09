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
import java.util.Objects;

/**
 * 更新插件鉴权信息响应体
 */
@ApiModel(description = "更新插件鉴权信息响应体")

@Validated

public class PluginAuthUpdateRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("pluginId")
    @Schema(description = "插件ID", example = "plugin_001")
    @Length(max = 64)
    private String pluginId = null;

    @JsonProperty("isNewlyPublished")
    @Schema(description = "是否为新发布", example = "true")
    private Boolean isNewlyPublished = false;

    @JsonProperty("versionId")
    @Schema(description = "版本ID", example = "v1.0.0")
    @Length(max = 64)
    private String versionId = null;

    @JsonProperty("message")
    @Schema(description = "响应消息", example = "操作成功")
    @Length(max = 256)
    private String message = null;

    public String getPluginId() {
        return pluginId;
    }

    public PluginAuthUpdateRsp setPluginId(String pluginId) {
        this.pluginId = pluginId;
        return this;
    }

    public PluginAuthUpdateRsp setIsNewlyPublished(Boolean isNewlyPublished) {
        this.isNewlyPublished = isNewlyPublished;
        return this;
    }

    public Boolean isIsNewlyPublished() {
        return isNewlyPublished;
    }

    public String getVersionId() {
        return versionId;
    }

    public PluginAuthUpdateRsp setVersionId(String versionId) {
        this.versionId = versionId;
        return this;
    }

    public String getMessage() {
        return message;
    }

    public PluginAuthUpdateRsp setMessage(String message) {
        this.message = message;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PluginAuthUpdateRsp {\n");

        sb.append("    pluginId: ").append(toIndentedString(pluginId)).append("\n");
        sb.append("    isNewlyPublished: ").append(toIndentedString(isNewlyPublished)).append("\n");
        sb.append("    versionId: ").append(toIndentedString(versionId)).append("\n");
        sb.append("    message: ").append(toIndentedString(message)).append("\n");
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
        PluginAuthUpdateRsp pluginAuthUpdateRsp = (PluginAuthUpdateRsp) o;
        return Objects.equals(this.pluginId, pluginAuthUpdateRsp.pluginId) && Objects.equals(this.isNewlyPublished,
            pluginAuthUpdateRsp.isNewlyPublished) && Objects.equals(this.versionId, pluginAuthUpdateRsp.versionId)
            && Objects.equals(this.message, pluginAuthUpdateRsp.message);
    }

    @Override
    public int hashCode() {
        return Objects.hash(pluginId, isNewlyPublished, versionId, message);
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
