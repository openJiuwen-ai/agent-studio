/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.config;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * SSRF 总开关关闭时的启动告警回归用例。
 *
 * <p>这里断言告警文案常量而不是捕获 log event：单测里 log4j-to-slf4j 桥会把
 * {@code LogManager.getLogger} 换成 SLF4JLogger，core appender 挂不上（参见
 * {@code SensitiveLogSentinelTest} 的 @Disabled 说明），因此用「文案必须包含正确的环境变量名、
 * 且不得断言协议白名单仍生效」这一静态约束来防回归。
 */
class SSRFStaticConfigTest {

    /** application-manager.yml:462 为该键声明的是 {@code ${SSRF_VALIDATION_ENABLED:false}} 占位符。 */
    private static final String ENV_NAME_FROM_YML = "SSRF_VALIDATION_ENABLED";

    /** Spring 宽松绑定对 {@code knowledge.ssrf.validation.enabled} 推导出的环境变量名。 */
    private static final String ENV_NAME_FROM_RELAXED_BINDING = "KNOWLEDGE_SSRF_VALIDATION_ENABLED";

    @AfterEach
    void restoreDefault() {
        // 恢复默认开启，避免静态字段污染同 JVM 的其他用例
        new SSRFStaticConfig().setSsrfValidationEnabled(true);
    }

    @Test
    void testSetSsrfValidationEnabled_writesStaticField() {
        SSRFStaticConfig config = new SSRFStaticConfig();

        config.setSsrfValidationEnabled(false);
        assertFalse(SSRFStaticConfig.isSsrfValidationEnabled());

        config.setSsrfValidationEnabled(true);
        assertTrue(SSRFStaticConfig.isSsrfValidationEnabled());
    }

    @Test
    void testDisabledWarning_namesEnvVarFormsThatActuallyResolve() {
        String warning = SSRFStaticConfig.SSRF_VALIDATION_DISABLED_WARNING;

        assertTrue(warning.contains("knowledge.ssrf.validation.enabled=false"), warning);
        // yml 占位符写法必须原样给出，否则运维按 KNOWLEDGE_ 前缀找不到对应配置项
        assertTrue(warning.contains("(env " + ENV_NAME_FROM_YML + ")"), warning);
        // 宽松绑定写法也一并给出，避免再被指出「提示的变量名不是实际生效的那个」
        assertTrue(warning.contains(ENV_NAME_FROM_RELAXED_BINDING), warning);
    }

    @Test
    void testDisabledWarning_doesNotClaimProtocolWhitelistStillApplies() {
        String warning = SSRFStaticConfig.SSRF_VALIDATION_DISABLED_WARNING;

        // 协议白名单是否生效取决于 SSRFValidator 的实现（见 !2790），本告警在任一合并顺序下都不能断言它仍生效
        assertFalse(warning.contains("whitelist still applies"), warning);
        assertFalse(warning.contains("allowed-protocols"), warning);
        assertTrue(warning.contains("no longer blocked"), warning);
    }
}
