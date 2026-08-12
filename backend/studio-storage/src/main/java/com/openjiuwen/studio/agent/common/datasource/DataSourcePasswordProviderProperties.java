/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.datasource;

import lombok.Data;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * 数据库密码获取配置属性。
 */
@Data
@ConfigurationProperties(prefix = "spring.datasource.password-provider")
public class DataSourcePasswordProviderProperties {

    /**
     * 密码获取方式：DEFAULT-本地解密，CUSTOM-外部自定义
     */
    private Type type = Type.DEFAULT;

    /**
     * 自定义实现类全限定名，type=CUSTOM 时必填
     */
    private String customClass;

    /**
     * 自定义实现 classpath（外部 JAR 路径），多个用路径分隔符分隔
     */
    private String customClasspath;

    public enum Type {
        DEFAULT, CUSTOM
    }
}
