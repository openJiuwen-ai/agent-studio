/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.openjiuwen.studio.agent.common.dto.TriggerConfig;

import lombok.Data;

import java.io.Serializable;
import java.util.List;

/**
 *
 */
@Data
public class WorkflowEntity implements Serializable {
    private static final long serialVersionUID = 1L;

    private String id;

    private String name;

    private String code;

    private String description;

    private String avatar;

    @JsonProperty("icon_name")
    private String iconName;

    @JsonProperty("dsl_path")
    private String dslPath;

    @JsonProperty("ir_path")
    private String irPath;

    private String status;

    private String visibility;

    @JsonProperty("created_at")
    private Long createdAt;

    @JsonProperty("updated_at")
    private Long updatedAt;

    @JsonProperty("published_at")
    private Long publishedAt;

    @JsonProperty("created_by")
    private String createdBy;

    @JsonProperty("creator_id")
    private String creatorId;

    @JsonProperty("updated_by")
    private String updatedBy;

    @JsonProperty("updater_id")
    private String updaterId;

    @JsonProperty("project_id")
    private String projectId;

    @JsonProperty("domain_id")
    private String domainId;

    @JsonProperty("workspace_id")
    private String workspaceId;

    @JsonProperty("deploy_wf_version")
    private Long deployWfVersion;

    private Boolean deleted = false;

    @JsonProperty("workflow_type")
    private String workflowType;

    @JsonProperty("last_version_id")
    private String lastVersionId;

    @JsonProperty("test_status")
    private Integer testStatus;

    /**
     * workflow使用触发器
     */
    @JsonProperty("trigger_list")
    private List<TriggerConfig> triggerList;

    /**
     * 是否是自定义节点，1表示是自定义节点,0或空表示不是
     */
    @JsonProperty("customize_node")
    private Integer customizeNode;

    @JsonProperty("trace_id")
    private String traceId;

    @JsonProperty("share_info")
    private ShareInfo shareInfo;

    @JsonProperty("is_share")
    private Integer isShare;
}
