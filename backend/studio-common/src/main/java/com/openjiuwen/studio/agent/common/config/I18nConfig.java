/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.config;

import org.springframework.context.MessageSource;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.context.support.ResourceBundleMessageSource;

/**
 * 国际化相关
 *
 */

@Configuration
public class I18nConfig {
    @Bean
    @Primary
    public MessageSource messageSource() {
        ResourceBundleMessageSource messageSource = new ResourceBundleMessageSource();
        messageSource.setBasenames("i18n/studio-messages", "messages", "agent-base-i18n/messages");
        messageSource.setDefaultEncoding("UTF-8");
        // 设置缓存时间 1h
        messageSource.setCacheSeconds(3600);
        return messageSource;
    }
}
