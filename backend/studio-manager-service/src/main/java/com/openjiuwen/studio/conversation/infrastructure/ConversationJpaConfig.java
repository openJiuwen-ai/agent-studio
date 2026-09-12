/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.conversation.infrastructure;

import org.springframework.context.annotation.Configuration;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.boot.autoconfigure.domain.EntityScan;

/**
 * 对话工作台领域 JPA 扫描配置。
 *
 * <p>宿主应用（studio-manager Application，包 com.openjiuwen.studio.agent.manager）的 JPA 自动扫描
 * 仅覆盖主包层级，本领域包（com.openjiuwen.studio.conversation）的实体与仓库需在此显式声明，
 * 避免侵入 agent/manager 包。</p>
 */
@Configuration
@EntityScan(basePackages = {
    "com.openjiuwen.studio.conversation.infrastructure.entity",
    "com.openjiuwen.studio.agent.manager"
})
@EnableJpaRepositories(basePackages = {
    "com.openjiuwen.studio.conversation.infrastructure.repository",
    "com.openjiuwen.studio.agent.manager"
})
public class ConversationJpaConfig {
}
