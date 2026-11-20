/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2022-2023. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

import java.sql.Timestamp;
import java.util.List;

@NoArgsConstructor
@AllArgsConstructor
@Data
@EqualsAndHashCode(callSuper = true)
public class McpServiceEntity extends BaseProperties {

    /**
     * MCP service 主键ID UUID
     */
    private String id;

    /**
     * MCP server 名称
     */
    private String name;

    /**
     * MCP server 英文名称
     */
    private String nameEn;

    /**
     * MCP server 描述
     */
    private String description;

    /**
     * MCP server 英文描述
     */
    private String descriptionEn;

    /**
     * markdown文档
     */
    private String readme;

    /**
     * 拉包类型 NPX|UVX|SSE
     */
    private String orgType;

    /**
     * 安装方式 sse|stdio|streamable_http
     */
    private String deployType;

    /**
     * server配置
     */
    private String serverConfig;

    /**
     * 工具列表
     */
    private String tools;

    /**
     * 托管的MPC服务函数实例的URL
     */
    private String fcInstanceUrl;

    /**
     * 托管的MPC服务函数实例在FG侧的id
     */
    private String fcInstanceId;

    /**
     * 托管的MPC服务函数实例在FG侧的状态
     */
    private String fcInstanceStatus;

    /**
     * 托管的MPC服务函数所在的Region，暂时可能用不到
     */
    private String fcRegion;

    /**
     * 托管的MPC服务函数APIG类型的触发器所在组ID
     */
    private String apigGroupId;

    /**
     * 托管的MPC服务函数APIG类型的触发器所在实例ID
     */
    private String apigInstanceId;

    /**
     * 函数名称
     */
    private String functionName;

    /**
     * mcp服务模版id
     */
    private String serverId;

    /**
     * mcp服务模版id
     */
    private String functionUrn;

    private String functionApplicationName;

    /**
     * 域名编号
     */
    private String domainId;

    private Timestamp createdDate;

    private Timestamp lastUpdatedDate;

    /**
     * 唯一编码，用于项目导入重复性判断
     */
    private String uniqueCode ;

    private String projectId;

    /**
     * 工作空间id
     */
    private String workspaceId;

    /**
     * 图标
     */
    private String icon;

    private AuthInfo auth;

    /**
     * 溯源ID，用于导入导出，复制
     */
    private String traceId;

    private String visibility;

    /**
     * 节点类型，用于区分Mcp服务节点与数据获取、加工节点
     */
    private String nodeType;

    /**
     * 鉴权类型，用于数据获取、加工节点透传鉴权token的标志
     */
    private String authType;

    /**
     * 跨线程临时存储iamtoken
     */
    private String tempToken;

    /**
     * FEAT-134：快照与配置相关写入的并发修订号（新实例默认 0）
     */
    private Long snapshotRevision;

    /**
     * FEAT-134：同服务活动操作声明（与 ws_mcp_operation.id 对应；NULL=无活动操作）
     */
    private String activeMcpOperationId;

    /**
     * FEAT-134：导入后待补配提示标记（不改变鉴权 scope）
     */
    private Boolean importConfigPending;

    /**
     * FEAT-134：待补配的 JSON Pointer 路径清单（仅路径不含值）
     */
    private String importConfigPaths;

    /**
     * 服务来源
     */
    private String thirdResource;

    /**
     * 三方服务id
     */
    private String thirdId;

    /**
     * 三方服务版本id
     */
    private String thirdVersionId;

    /**
     * 部署失败具体原因/错误信息
     */
    private String failReason;

    /**
     * MCP拓展自定义鉴权信息
     */
    private AuthInfo authInfo;

    /**
     * 是否被共享（0=否，1=是)
     */
    private int isShare;

    /**
     * 来源（0=本身，1 = 共享）
     */
    private int origin;

    @JsonProperty("share_info")
    private ShareInfo shareInfo;

    @JsonProperty("share_reference")
    private List<MappingEntity> shareResourceReferenceList;
}

