/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.workflow.resource.model;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.Data;

import java.util.List;

/**
 * 运行时资产导出清单（manifest.json）。
 * 对应 SDD 4.4.1，描述导出包内全部资产及其 SHA256、状态。
 */
@Data
public class RuntimeAssetManifest {

    @JsonProperty("manifest_version")
    private String manifestVersion = "1.0";

    @JsonProperty("export_id")
    private String exportId;

    @JsonProperty("exported_at")
    private String exportedAt;

    @JsonProperty("exported_by")
    private String exportedBy;

    @JsonProperty("source")
    private ManifestSource source;

    @JsonProperty("resources")
    private List<ManifestResource> resources;

    @JsonProperty("assets")
    private List<ManifestAsset> assets;

    @JsonProperty("summary")
    private ManifestSummary summary;

    @Data
    public static class ManifestSource {
        @JsonProperty("environment")
        private String environment;

        @JsonProperty("storage_type")
        private String storageType;

        @JsonProperty("bucket")
        private String bucket;
    }

    @Data
    public static class ManifestResource {
        @JsonProperty("resource_id")
        private String resourceId;

        @JsonProperty("resource_name")
        private String resourceName;

        @JsonProperty("resource_type")
        private String resourceType;

        @JsonProperty("ir_path")
        private String irPath;

        @JsonProperty("version")
        private String version;

        @JsonProperty("mode")
        private String mode;

        @JsonProperty("domain_id")
        private String domainId;

        @JsonProperty("project_id")
        private String projectId;

        @JsonProperty("workspace_id")
        private String workspaceId;
    }

    @Data
    public static class ManifestAsset {
        /** 资产类型：agent_ir / workflow_ir / model_service / model_auth /
         *  kb_connection / kb_reference / metadata / skill */
        @JsonProperty("type")
        private String type;

        /** OBS object key，同时是 ZIP 内路径 */
        @JsonProperty("key")
        private String key;

        @JsonProperty("size")
        private long size;

        @JsonProperty("sha256")
        private String sha256;

        /** ok / missing —— PRD 可靠性：读取失败的资产记录错误但继续导出 */
        @JsonProperty("status")
        private String status;

        /** status=missing 时的失败原因（如 OBS 404），ok 时为 null */
        @JsonProperty("error_reason")
        private String errorReason;

        /** 备注：如 t_mapping 版本与 IR 内嵌路径不一致时的差异说明 */
        @JsonProperty("note")
        private String note;
    }

    @Data
    public static class ManifestSummary {
        @JsonProperty("total_assets")
        private int totalAssets;

        @JsonProperty("total_size_bytes")
        private long totalSizeBytes;

        @JsonProperty("ir_count")
        private int irCount;

        @JsonProperty("model_count")
        private int modelCount;

        @JsonProperty("kb_count")
        private int kbCount;

        @JsonProperty("skill_count")
        private int skillCount;

        @JsonProperty("metadata_count")
        private int metadataCount;

        @JsonProperty("missing_count")
        private int missingCount;
    }
}
