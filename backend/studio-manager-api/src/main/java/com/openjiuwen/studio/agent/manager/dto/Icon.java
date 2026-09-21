/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 智能生成智能体图标。
 */
@ApiModel(description = "智能生成智能体图标。")

@Validated

public class Icon implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("icon")
    @Schema(description = "图标", example = "https://example.com/icon.png")
    private String icon = null;

    @JsonProperty("icon_detail")
    @Schema(description = "图标", example = "https://example.com/icon.png")
    private String iconDetail = null;

    public String getIcon() {
        return icon;
    }

    public Icon setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public String getIconDetail() {
        return iconDetail;
    }

    public Icon setIconDetail(String iconDetail) {
        this.iconDetail = iconDetail;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class Icon {\n");

        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    iconDetail: ").append(toIndentedString(iconDetail)).append("\n");
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
        Icon icon = (Icon) o;
        return Objects.equals(this.icon, icon.icon) && Objects.equals(this.iconDetail, icon.iconDetail);
    }

    @Override
    public int hashCode() {
        return Objects.hash(icon, iconDetail);
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
