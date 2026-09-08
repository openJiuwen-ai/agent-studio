/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.examples;

import com.openjiuwen.studio.agent.common.datasource.DataSourcePasswordProvider;

/**
 * 自定义数据库密码获取实现示例：从环境变量获取密码。
 *
 * <p>适用场景：数据库密码通过 K8s Secret 以环境变量注入，
 * 配置文件中无需存储明文密码。</p>
 *
 * <p>使用方式：
 * <pre>
 * # application.yml
 * spring:
 *   datasource:
 *     password-provider:
 *       type: CUSTOM
 *       custom-class: com.openjiuwen.studio.examples.EnvPasswordProvider
 *       custom-classpath: /opt/plugins/custom-password-provider.jar
 * </pre>
 *
 * <p>设置环境变量 {@code DB_REAL_PASSWORD} 后启动服务即可。</p>
 *
 * <p>与 Python 侧 {@code EnvPasswordProvider} 对齐，行为一致。</p>
 */
public class EnvPasswordProvider implements DataSourcePasswordProvider {

    private static final String ENV_KEY = "DB_REAL_PASSWORD";

    @Override
    public String getPassword(String rawPassword) {
        String password = System.getenv(ENV_KEY);
        if (password == null || password.isEmpty()) {
            throw new IllegalStateException(
                "Environment variable '" + ENV_KEY + "' is not set, cannot obtain database password");
        }
        return password;
    }
}
