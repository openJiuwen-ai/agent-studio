/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.datasource;

import com.openjiuwen.studio.agent.common.common.ExternalJarLoader;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 自定义数据库密码获取实现自动配置。
 *
 * <p>当 {@code datasource.password-provider.type} 为 {@code CUSTOM} 时激活。
 * 通过 {@code custom-classpath} 加载外部 JAR 构建 URLClassLoader，
 * 通过反射实例化 {@code custom-class} 指定的实现类。</p>
 */
@Configuration
@ConditionalOnProperty(name = "spring.datasource.password-provider.type", havingValue = "CUSTOM")
@EnableConfigurationProperties(DataSourcePasswordProviderProperties.class)
public class CustomDataSourcePasswordProviderAutoConfiguration {

    @Bean
    public DataSourcePasswordProvider dataSourcePasswordProvider(DataSourcePasswordProviderProperties properties,
        ConfigurableApplicationContext context) {
        String className = properties.getCustomClass();
        if (className == null || className.isEmpty()) {
            throw new IllegalArgumentException(
                "datasource.password-provider.custom-class must be specified when datasource.password-provider.type=CUSTOM");
        }

        ClassLoader classLoader = ExternalJarLoader.buildClassLoaderFromClasspath(properties.getCustomClasspath());

        return ExternalJarLoader.loadAndInject(className, DataSourcePasswordProvider.class, classLoader, context);
    }
}
