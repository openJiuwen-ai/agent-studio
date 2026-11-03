/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.rce.client;

/**
 * 关联 Header Feign 配置标记接口（COM-04 §10.4）。
 *
 * <p>实现该接口的 Feign configuration 类表示会注入三个平台关联 Header。
 * 治理测试据此标记识别关联配置（而非硬编码类集合），新增关联配置类只要实现本接口即可被治理覆盖。
 * 只有 {@link FeignClientRegistry} 允许的客户端才可挂载实现本接口的配置。
 */
public interface CorrelationFeignConfig {
}
