/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis;

import java.time.Duration;

/**
 * Redis锁
 *
 */
public interface RedisLock {
    /**
     * 获取锁
     *
     * @param maxWait 等待获取锁的最长时间
     * @return 如果成功获取返回<code>true</code>，如果在等待时间达到后仍未获取返回<code>false</code>
     */
    boolean tryLock(Duration maxWait) throws Exception;

    /**
     * 释放锁
     */
    void unlock();
}
