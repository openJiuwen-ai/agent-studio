/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2020-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity;

import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.TypeReference;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.openjiuwen.studio.agent.manager.dto.ResourceVersionInfo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.experimental.Accessors;

import java.util.Arrays;
import java.util.Date;
import java.util.List;

/**
 * 跨空间共享对象
 *
 */
@NoArgsConstructor
@AllArgsConstructor
@Data
@Accessors(chain = true)
public class ShareResourceEntity {
    /**
     * 被共享的源元素ID，主键。
     */
    @JsonProperty("resource_id")
    private String resourceId;

    @JsonProperty("resource_name")
    private String resourceName;

    /**
     * 被共享的资源类型，如agent、workflow、tool、mcp等。
     */
    @JsonProperty("resource_type")
    private String resourceType;

    /**
     * 源元素归属的空间ID。
     */
    @JsonProperty("workspace_id")
    private String workspaceId;

    /**
     * 源元素归属的空间名称。
     */
    @JsonProperty("workspace_name")
    private String workspaceName;

    /**
     * 被共享的源元素的溯源ID。
     */
    @JsonProperty("trace_id")
    private String traceId;

    /**
     * 被共享的版本号。当前写入为JSON数组串（元素含版本号/版本名），
     * 历史数据可能为逗号分隔的版本号串。
     */
    @JsonProperty("version_list")
    private String versionList;

    /**
     * 当前企业项目ID。
     */
    @JsonProperty("project_id")
    private String projectId;

    /**
     * 租户ID。
     */
    @JsonProperty("tenant_id")
    private String tenantId;

    /**
     * 创建用户ID。
     */
    @JsonProperty("creator_id")
    private String creatorId;

    @JsonProperty("creator")
    private String creator;

    /**
     * 创建时间，默认为当前时间戳。
     */
    @JsonProperty("create_time")
    private Date createTime;

    /**
     * 更新用户ID。
     */
    @JsonProperty("updater_id")
    private String updaterId;

    @JsonProperty("updater")
    private String updater;

    /**
     * 更新时间，默认为当前时间戳。
     */
    @JsonProperty("update_time")
    private Date updateTime;

    /**
     * 判断指定版本号是否在共享版本列表中（按版本号逐项精确匹配）。
     * <p>
     * versionList为JSON数组串（元素含版本号/版本名），历史数据可能为逗号分隔的版本号串，
     * 两种格式均需解析/拆分后精确比对。严禁对原始串直接做String.contains子串匹配：
     * 不存在的版本号（如"178"）会因是已共享版本号（如"1789548359671"）的子串而被误判为已共享。
     * <p>
     * 边界行为说明：versionId仅作equals比较参数，不做任何解析/拆分/正则，
     * 含引号、逗号、括号、中文、emoji或超长的版本号均安全；JSON分支下这些字符经
     * toJSONString转义写入、parseObject还原后仍可精确匹配。若versionList以"["开头但
     * 不是合法JSON（脏数据，正常写入路径不会产生），与既有解析代码保持一致地抛出
     * JSONException快速失败，避免误放行删除可能已共享的版本。
     *
     * @param versionId 版本ID
     * @return 版本号在共享列表中时返回true
     */
    public boolean containsVersion(String versionId) {
        if (versionList == null || versionList.isEmpty() || versionId == null || versionId.isEmpty()) {
            return false;
        }
        String trimmedVersionList = versionList.trim();
        if (trimmedVersionList.startsWith("[")) {
            List<ResourceVersionInfo> versionInfos = JSONObject.parseObject(trimmedVersionList,
                new TypeReference<>() { });
            return versionInfos != null && !versionInfos.isEmpty() && versionInfos.stream()
                .anyMatch(info -> info != null && versionId.equals(info.getVersionId()));
        }

        // 兼容历史格式：逗号分隔的版本号串，逐项精确匹配
        return Arrays.stream(trimmedVersionList.split(","))
            .map(String::trim)
            .anyMatch(versionId::equals);
    }
}
