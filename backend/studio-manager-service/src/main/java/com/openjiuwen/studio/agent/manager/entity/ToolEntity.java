/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.manager.dto.RequestInfo;
import com.openjiuwen.studio.agent.manager.dto.ToolCredential;

import lombok.Data;

import java.util.Date;
import java.util.List;

/**
 * 工具实体类
 *
 */
@Data
public class ToolEntity {
    @JsonProperty("tool_id")
    private String toolId;

    @JsonProperty("project_id")
    private String projectId;

    @JsonProperty("workspace_id")
    private String workspaceId;

    @JsonProperty("tool_display_name")
    private String toolDisplayName;

    @JsonProperty("tool_chinese_name")
    private String toolChineseName;

    @JsonProperty("tool_desc")
    private String toolDesc;

    @JsonProperty("tool_desc_en")
    private String toolDescEn;

    @JsonProperty("icon")
    private String icon;

    @JsonProperty("icon_name")
    private String iconName;

    @JsonProperty("request_info")
    private RequestInfo requestInfo;

    @JsonProperty("auth_info")
    private AuthInfo authInfo;

    @JsonProperty("visibility")
    private String visibility;

    @JsonProperty("input_schema")
    private String inputSchema;

    @JsonProperty("output_schema")
    private String outputSchema;

    @JsonProperty("is_input_list")
    private Boolean isInputList;

    @JsonProperty("is_output_list")
    private Boolean isOutputList;

    @JsonProperty("type")
    private String type;

    @JsonProperty("intf_type")
    private String intfType;

    @JsonProperty("metadata")
    private String metadata;

    @JsonProperty("call_mode")
    private String callMode;

    @JsonProperty("creator")
    private String creator;

    @JsonProperty("creator_id")
    private String creatorId;

    @JsonProperty("created_on")
    private Date createdOn;

    @JsonProperty("updated_on")
    private Date updatedOn;

    /**
     * 工具测试状态，0：失败；1：成功；2：未知
     */
    @JsonProperty("test_status")
    private Integer testStatus;

    /**
     * 插件最新版本号
     */
    @JsonProperty("last_version_id")
    private String lastVersionId;

    /**
     * 插件凭证
     */
    @JsonProperty("credential")
    private ToolCredential credentials;

    /**
     * 插件凭证开通状态
     */
    @JsonProperty("credential_status")
    private String credentialStatus;

    /**
     * 插件版本号
     */
    @JsonProperty("version_id")
    private String versionId;

    /**
     * 是否是自定义节点，1表示是自定义节点,0或空表示不是
     */
    @JsonProperty("customize_node")
    private Integer customizeNode;

    /**
     * 插件是否需要鉴权
     */
    @JsonProperty("auth_required")
    private Boolean authRequired;

    @JsonProperty("trace_id")
    private String traceId;

    @JsonProperty("published")
    private Integer published;

    @JsonProperty("share_info")
    private ShareInfo shareInfo;

    @JsonProperty("share_reference")
    private List<MappingEntity> shareResourceReferenceList;

    /**
     *  是否是免费插件，0:未知，1:免费，2:付费
     */
    @JsonProperty("is_free")
    private Integer isFree;

    @JsonProperty("domain_id")
    private String domainId;

    @JsonProperty("category")
    private String category;
}
