/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.mapper;

import com.openjiuwen.studio.agent.manager.entity.PollingTriggerStateEntity;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.Date;

/**
 * Polling trigger state mapper.
 */
@Mapper
public interface PollingTriggerStateMapper {
    int initialize(@Param("triggerId") String triggerId);

    PollingTriggerStateEntity selectByTriggerId(@Param("triggerId") String triggerId);

    PollingTriggerStateEntity selectForUpdate(@Param("triggerId") String triggerId);

    int compareAndSetLastSeenHash(@Param("triggerId") String triggerId,
        @Param("expectedHash") String expectedHash, @Param("newHash") String newHash);

    int updateLastCheckedAt(@Param("triggerId") String triggerId,
        @Param("lastCheckedAt") Date lastCheckedAt);

    int deleteByTriggerId(@Param("triggerId") String triggerId);
}
