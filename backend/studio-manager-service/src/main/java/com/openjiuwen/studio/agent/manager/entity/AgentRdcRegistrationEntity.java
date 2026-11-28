/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity;

import com.openjiuwen.studio.agent.common.a2a.enums.RegistrationStatus;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Date;

/**
 * Agent RDC 注册实体
 *
 * <p>FEAT-131: 记录应用发布后的 A2A 注册状态</p>
 * <p>对应表 t_agent_rdc_registration</p>
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class AgentRdcRegistrationEntity {

    /**
     * 主键（UUID）
     */
    private String id;

    /**
     * 应用 ID（agentId / workflowId）
     */
    private String agentId;

    /**
     * 服务 ID（应用类型 + 版本标识）
     */
    private String serviceId;

    /**
     * RDC 返回的实例 ID（A1 注册成功后返回，A3 注销时使用）
     */
    private String instanceId;

    /**
     * 注册状态
     */
    private RegistrationStatus status;

    /**
     * Agent Card JSON（完整，与注册到 RDC 和 /.well-known/agent-card.json 同源）
     */
    private String agentCardJson;

    /**
     * 注册模式（A1=注册 / A3=注销）
     */
    private String registrationMode;

    /**
     * 创建时间
     */
    private Date createdOn;

    /**
     * 更新时间
     */
    private Date updatedOn;
}
