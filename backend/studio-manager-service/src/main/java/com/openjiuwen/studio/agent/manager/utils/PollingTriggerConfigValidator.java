/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.utils;

import com.openjiuwen.studio.agent.common.dto.TriggerConfig;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * Validates Polling trigger configuration and applies server defaults.
 */
@Component
public class PollingTriggerConfigValidator {
    private final int defaultPollIntervalSeconds;

    private final int minPollIntervalSeconds;

    private final int maxPollIntervalSeconds;

    private final int maxPollUrlLength;

    public PollingTriggerConfigValidator(
        @Value("${trigger.polling.default-interval-seconds}") int defaultPollIntervalSeconds,
        @Value("${trigger.polling.min-interval-seconds}") int minPollIntervalSeconds,
        @Value("${trigger.polling.max-interval-seconds}") int maxPollIntervalSeconds,
        @Value("${trigger.polling.max-url-length}") int maxPollUrlLength) {
        this.defaultPollIntervalSeconds = defaultPollIntervalSeconds;
        this.minPollIntervalSeconds = minPollIntervalSeconds;
        this.maxPollIntervalSeconds = maxPollIntervalSeconds;
        this.maxPollUrlLength = maxPollUrlLength;
    }

    /**
     * Validates Polling-specific fields and applies their defaults.
     *
     * @param config trigger configuration
     */
    public void validateAndApplyDefaults(TriggerConfig config) {
        String pollUrl = config.getPollUrl();
        if (StringUtils.isBlank(pollUrl) || pollUrl.length() > maxPollUrlLength) {
            throw new AgentStudioException(StudioError.INVALID_URL);
        }

        Integer interval = config.getPollIntervalSeconds();
        if (interval == null) {
            config.setPollIntervalSeconds(defaultPollIntervalSeconds);
            return;
        }
        if (interval < minPollIntervalSeconds || interval > maxPollIntervalSeconds) {
            throw new AgentStudioException(StudioError.INVALID_PARAMETER_ERROR, "poll_interval_seconds");
        }
    }
}
