/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity.plugin;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.manager.dto.ToolCredential;

import lombok.Data;

import java.util.Date;

/**
 * 插件实体类
 *
 */
@Data
public class PluginEntity {
    @JsonProperty("plugin_id")
    private String pluginId;

    @JsonProperty("project_id")
    private String projectId;

    @JsonProperty("workspace_id")
    private String workspaceId;

    @JsonProperty("plugin_display_name")
    private String pluginDisplayName;

    @JsonProperty("plugin_chinese_name")
    private String pluginChineseName;

    @JsonProperty("plugin_desc")
    private String pluginDesc;

    @JsonProperty("plugin_desc_en")
    private String pluginDescEn;

    @JsonProperty("icon")
    private String icon;

    @JsonProperty("icon_name")
    private String iconName;

    @JsonProperty("request_info")
    private String requestInfo;

    @JsonProperty("auth_info")
    private AuthInfo authInfo;

    @JsonProperty("visibility")
    private String visibility;

    @JsonProperty("input_schema")
    private String inputSchema;

    @JsonProperty("output_schema")
    private String outputSchema;

    @JsonProperty("is_input_list")
    private String isInputList;

    @JsonProperty("is_output_list")
    private String isOutputList;

    @JsonProperty("type")
    private String type;

    @JsonProperty("call_mode")
    private String callMode;

    @JsonProperty("intf_type")
    private String intfType;

    @JsonProperty("metadata")
    private String metadata;

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
    private String testStatus;

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

    /**
     *  是否是免费插件，0:未知，1:免费，2:付费
     */
    @JsonProperty("is_free")
    private Integer isFree;

    @JsonProperty("domain_id")
    private String domainId;

    @JsonProperty("is_share")
    private Integer isShare;

    @JsonProperty("category")
    private String category;

    /**
     * 用户插件上架到资产广场标记（1=是，0=否）
     */
    @JsonProperty("platform_published")
    private Integer platformPublished;

    /**
     * 上架锚定的发布版本ID（t_release_version.version_id）
     */
    @JsonProperty("plaza_version_id")
    private String plazaVersionId;
}
