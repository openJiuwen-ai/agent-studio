/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 导出结果信息。
 */
@ApiModel(description = "导出结果信息。")

@Validated

public class ExportResourceRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("download_url")
    @Schema(description = "下载URL", example = "https://example.com")
    @Length(max = 2048)
    private String downloadUrl = null;

    @JsonProperty("export_result")
    @Schema(description = "导出结果", example = "{}")
    @Valid
    private Object exportResult = null;

    public String getDownloadUrl() {
        return downloadUrl;
    }

    public ExportResourceRsp setDownloadUrl(String downloadUrl) {
        this.downloadUrl = downloadUrl;
        return this;
    }

    public Object getExportResult() {
        return exportResult;
    }

    public ExportResourceRsp setExportResult(Object exportResult) {
        this.exportResult = exportResult;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ExportResourceRsp {\n");

        sb.append("    downloadUrl: ").append(toIndentedString(downloadUrl)).append("\n");
        sb.append("    exportResult: ").append(toIndentedString(exportResult)).append("\n");
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
        ExportResourceRsp exportResourceRsp = (ExportResourceRsp) o;
        return Objects.equals(this.downloadUrl, exportResourceRsp.downloadUrl) && Objects.equals(this.exportResult,
            exportResourceRsp.exportResult);
    }

    @Override
    public int hashCode() {
        return Objects.hash(downloadUrl, exportResult);
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
