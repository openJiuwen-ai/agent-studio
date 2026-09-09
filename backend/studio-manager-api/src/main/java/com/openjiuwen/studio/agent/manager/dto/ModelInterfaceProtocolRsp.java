/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ModelInterfaceProtocolRsp
 */

@Validated

public class ModelInterfaceProtocolRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "协议ID", example = "protocol-001")
    private String id = null;

    @JsonProperty("protocol")
    @Schema(description = "协议名称", example = "OpenAI")
    private String protocol = null;

    @JsonProperty("en_name")
    @Schema(description = "英文名称", example = "OpenAI Compatible")
    private String enName = null;

    @JsonProperty("zh_name")
    @Schema(description = "中文名称", example = "OpenAI兼容协议")
    private String zhName = null;

    @JsonProperty("model_types")
    @Schema(description = "支持的模型类型", example = "chat,embedding")
    private String modelTypes = null;

    @JsonProperty("visible")
    @Schema(description = "是否可见", example = "true")
    private String visible = null;

    public String getId() {
        return id;
    }

    public ModelInterfaceProtocolRsp setId(String id) {
        this.id = id;
        return this;
    }

    public String getProtocol() {
        return protocol;
    }

    public ModelInterfaceProtocolRsp setProtocol(String protocol) {
        this.protocol = protocol;
        return this;
    }

    public String getEnName() {
        return enName;
    }

    public ModelInterfaceProtocolRsp setEnName(String enName) {
        this.enName = enName;
        return this;
    }

    public String getZhName() {
        return zhName;
    }

    public ModelInterfaceProtocolRsp setZhName(String zhName) {
        this.zhName = zhName;
        return this;
    }

    public String getModelTypes() {
        return modelTypes;
    }

    public ModelInterfaceProtocolRsp setModelTypes(String modelTypes) {
        this.modelTypes = modelTypes;
        return this;
    }

    public String getVisible() {
        return visible;
    }

    public ModelInterfaceProtocolRsp setVisible(String visible) {
        this.visible = visible;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ModelInterfaceProtocolRsp {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    protocol: ").append(toIndentedString(protocol)).append("\n");
        sb.append("    enName: ").append(toIndentedString(enName)).append("\n");
        sb.append("    zhName: ").append(toIndentedString(zhName)).append("\n");
        sb.append("    modelTypes: ").append(toIndentedString(modelTypes)).append("\n");
        sb.append("    visible: ").append(toIndentedString(visible)).append("\n");
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
        ModelInterfaceProtocolRsp modelInterfaceProtocolRsp = (ModelInterfaceProtocolRsp) o;
        return Objects.equals(this.id, modelInterfaceProtocolRsp.id) && Objects.equals(this.protocol,
            modelInterfaceProtocolRsp.protocol) && Objects.equals(this.enName, modelInterfaceProtocolRsp.enName)
            && Objects.equals(this.zhName, modelInterfaceProtocolRsp.zhName) && Objects.equals(this.modelTypes,
            modelInterfaceProtocolRsp.modelTypes) && Objects.equals(this.visible, modelInterfaceProtocolRsp.visible);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, protocol, enName, zhName, modelTypes, visible);
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
