/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.config;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.core.StreamReadConstraints;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.text.SimpleDateFormat;
import java.util.TimeZone;

/**
 * 动态配置jackson最大token限制
 *
 */
@Configuration
public class JacksonConfig {
    @Value("${jackson.max-string-length:50000000}")
    private int maxStringLength;

    @Value("${jackson.max-token-limit:10000000}")
    private long maxTokenLimit;

    @Value("${jackson.time-zone}")
    private String timeZone;

    @Value("${jackson.date-format}")
    private String dateFormat;

    @Value("${jackson.default-property-inclusion}")
    private String defaultPropertyInclusion;

    @Value("${jackson.fail-on-unknown-properties:false}")
    private boolean isFailOnUnknownProperties;

    @Value("${jackson.serialization.write-dates-as-timestamps:true}")
    private boolean writeDatesAsTimestamps;

    @Bean
    public ObjectMapper objectMapper() {
        ObjectMapper mapper = new ObjectMapper();
        // 使用 maxStringLength 和 maxTokenCount 分别配置
        mapper.getFactory()
            .setStreamReadConstraints(StreamReadConstraints.builder()
                .maxStringLength(maxStringLength)
                .maxTokenCount(maxTokenLimit)
                .build());
        mapper.setDateFormat(new SimpleDateFormat(dateFormat));
        mapper.setTimeZone(TimeZone.getTimeZone(timeZone));
        // 配置序列化时将Date转换为时间戳
        if (writeDatesAsTimestamps) {
            mapper.enable(com.fasterxml.jackson.databind.SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
        }

        mapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, isFailOnUnknownProperties);
        if ("non_null".equalsIgnoreCase(defaultPropertyInclusion)) {
            mapper.setSerializationInclusion(JsonInclude.Include.NON_NULL);
        }
        return mapper;
    }
}
