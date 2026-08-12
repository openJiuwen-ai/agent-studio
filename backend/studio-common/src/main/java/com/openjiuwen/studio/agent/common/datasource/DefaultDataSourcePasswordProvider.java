/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.datasource;

import com.openjiuwen.studio.agent.common.utils.CryptoUtils;

import lombok.extern.slf4j.Slf4j;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * 默认数据库密码获取实现，使用 CryptoUtils 解密。
 *
 * <p>当 {@code datasource.password-provider.type} 为 {@code DEFAULT} 或未配置时激活。</p>
 */
@Slf4j
@Configuration
@EnableConfigurationProperties(DataSourcePasswordProviderProperties.class)
@ConditionalOnProperty(name = "spring.datasource.password-provider.type",
    havingValue = "DEFAULT", matchIfMissing = true)
public class DefaultDataSourcePasswordProvider implements DataSourcePasswordProvider {

    private final CryptoUtils cryptoUtils;

    public DefaultDataSourcePasswordProvider(CryptoUtils cryptoUtils) {
        this.cryptoUtils = cryptoUtils;
    }

    @Override
    public String getPassword(String rawPassword) {
        if (rawPassword == null || rawPassword.isEmpty()) {
            return rawPassword;
        }
        String decryptedPassword = cryptoUtils.decrypt(rawPassword);
        log.info("DataSource password decrypted successfully");
        return decryptedPassword;
    }
}
