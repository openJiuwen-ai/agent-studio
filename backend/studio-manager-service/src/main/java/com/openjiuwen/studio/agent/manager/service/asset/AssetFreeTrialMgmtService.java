/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.asset;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.collections4.MapUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.math.NumberUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.YearMonth;
import java.time.temporal.TemporalAdjusters;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * AssetFreeTrialMgmtService
 *
 */
@Slf4j
@Service
@RequiredArgsConstructor(onConstructor_ = {@Autowired})
public class AssetFreeTrialMgmtService {
    private final RedisClient redisClient;

    @Value("${asset.app.free.trial-quota-limit:10}")
    private int maxFreeTrialTimes;

    @Value("${asset.app.free.trial-quota-check-enabled:false}")
    private boolean trialQuotaCheckEnabled;

    private static final String ASSET_FREE_TRIAL_USAGE_QUOTA_RW_LOCK_FORMAT
        = "agent.manager.asset.app.free.trial.usage.quota.rw.lock.asset_%s.month_%s.domain_%s.lock";

    private static final String ASSET_FREE_TRIAL_USAGE_QUOTA_KEY_FORMAT
        = "agent.manager.asset.app.free.trial.usage.quota.asset_%s.month_%s.domain_%s";

    /**
     * queryFreeTrialUsageQuota
     *
     * @param assetId assetId
     * @param domainId domainId
     * @return int
     */
    public int queryFreeTrialUsageQuota(String assetId, String domainId) {
        if (StringUtils.isAnyBlank(assetId, domainId)) {
            log.info("Blank assetId or domainId, return max limit quota as usage quota.");
            return maxFreeTrialTimes;
        }

        try {
            String assetFreeTrialUsageRecords = redisClient.get(getAssetFreeTrialUsageQuotaKey(domainId, assetId));

            if (StringUtils.isBlank(assetFreeTrialUsageRecords)) {
                log.info(
                    "None asset free trial quota record stored, return zero as usage quota. Domain: {}, asset: {}.",
                    domainId, assetId);
                return 0;
            }

            return NumberUtils.toInt(assetFreeTrialUsageRecords, maxFreeTrialTimes);
        } catch (Exception e) {
            log.error("Query free trial usage quota failed.", e);
            return maxFreeTrialTimes;
        }
    }

    /**
     * queryFreeTrialUsageQuota
     *
     * @param assetIds assetIds
     * @param domainId domainId
     * @return Map<String,Integer> key: assetId, value: usageQuota
     */
    public Map<String, Integer> queryFreeTrialUsageQuota(List<String> assetIds, String domainId) {
        if (StringUtils.isBlank(domainId) || CollectionUtils.isEmpty(assetIds)) {
            return Collections.emptyMap();
        }

        List<String> assetFreeTrialUsageQuotaKeys = new ArrayList<>();
        for (String assetId : assetIds) {
            assetFreeTrialUsageQuotaKeys.add(getAssetFreeTrialUsageQuotaKey(domainId, assetId));
        }

        try {
            Map<String, Object> assetFreeTrialUsageQuotaMap = redisClient.getAll(assetFreeTrialUsageQuotaKeys);

            if (MapUtils.isEmpty(assetFreeTrialUsageQuotaMap)) {
                log.info("None asset free trial quota record stored, return zero as usage quota. Domain: {}.",
                    domainId);
                Map<String, Integer> freeTrialUsageQuotaMap = new HashMap<>(assetIds.size());
                for (String assetId : assetIds) {
                    freeTrialUsageQuotaMap.put(assetId, 0);
                }

                return freeTrialUsageQuotaMap;
            }

            Map<String, Integer> freeTrialUsageQuotaMap = new HashMap<>(assetIds.size());
            for (String assetId : assetIds) {
                Object storedUsageQuota = assetFreeTrialUsageQuotaMap.get(
                    getAssetFreeTrialUsageQuotaKey(domainId, assetId));
                if (storedUsageQuota == null) {
                    freeTrialUsageQuotaMap.put(assetId, 0);
                    continue;
                }

                freeTrialUsageQuotaMap.put(assetId, NumberUtils.toInt(storedUsageQuota.toString(), maxFreeTrialTimes));
            }

            return freeTrialUsageQuotaMap;
        } catch (Exception e) {
            log.error("Query free trial usage quotas failed.", e);
            return Collections.emptyMap();
        }
    }

    /**
     * isInFreeTrial
     *
     * @param assetId assetId
     * @param domainId domainId
     * @return boolean
     */
    public boolean isInFreeTrial(String assetId, String domainId) {
        if (!trialQuotaCheckEnabled) {
            return true;
        }

        if (StringUtils.isAnyBlank(assetId, domainId)) {
            log.info("Not in asset free trial: blank assertId or conversationId.");
            return false;
        }

        String assertFreeTrialUsageRecords = redisClient.get(getAssetFreeTrialUsageQuotaKey(domainId, assetId));

        if (StringUtils.isBlank(assertFreeTrialUsageRecords)) {
            log.info("Empty usage records, try to add usage record, domain: {}, asset: {}.", domainId, assetId);
            return incrementAssetFreeTrialUsageQuota(domainId, assetId);
        }

        int usageQuotaCntInFreeTrial = NumberUtils.toInt(assertFreeTrialUsageRecords);
        if (usageQuotaCntInFreeTrial >= maxFreeTrialTimes) {
            log.info("Usage quota cnt {} has reach the max free trial times limit {}.", usageQuotaCntInFreeTrial,
                maxFreeTrialTimes);
            return false;
        } else {
            return incrementAssetFreeTrialUsageQuota(domainId, assetId);
        }
    }

    private boolean incrementAssetFreeTrialUsageQuota(String domainId, String assetId) {
        RedisLock writeAssetUsageLockKey = null;
        try {
            writeAssetUsageLockKey = redisClient.getLock(getAssetFreeTrialUsageQuotaRwLockKey(domainId, assetId));

            if (writeAssetUsageLockKey.tryLock(Duration.ofSeconds(10))) {
                String assertFreeTrialUsageRecordsVal = redisClient.get(
                    getAssetFreeTrialUsageQuotaKey(domainId, assetId));

                if (StringUtils.isBlank(assertFreeTrialUsageRecordsVal)) {
                    log.info("None usage records of assert {} for domain {} in month_{}.", assetId, domainId,
                        LocalDate.now().getMonthValue());
                    redisClient.set(getAssetFreeTrialUsageQuotaKey(domainId, assetId), "1",
                        Duration.ofMillis(getAssetFreeTrialRecordsListKeyTtlMills()));
                    log.info("Add usage record success.");

                    return true;
                }

                int usageQuotaCntInFreeTrial = NumberUtils.toInt(assertFreeTrialUsageRecordsVal);

                if (usageQuotaCntInFreeTrial >= maxFreeTrialTimes) {
                    log.info(
                        "Usage records count has reach the max free trial times limit {}, current usage quota: {}.",
                        maxFreeTrialTimes, usageQuotaCntInFreeTrial);
                    log.info("Don't increment usage quota. Domain: {}, asset: {}", domainId, assetId);
                    return false;
                } else {
                    redisClient.set(getAssetFreeTrialUsageQuotaKey(domainId, assetId),
                        String.valueOf(usageQuotaCntInFreeTrial + 1),
                        Duration.ofMillis(getAssetFreeTrialRecordsListKeyTtlMills()));
                    log.info("Add usage record success. Domain: {}, asset: {}, usageQuotaCnt {}.", domainId, assetId,
                        usageQuotaCntInFreeTrial);
                    return true;
                }
            }
        } catch (Exception e) {
            log.error("Failed to add asset trial usage records.", e);
        } finally {
            if (writeAssetUsageLockKey != null) {
                writeAssetUsageLockKey.unlock();
            }
        }
        return true;
    }

    private long getAssetFreeTrialRecordsListKeyTtlMills() {
        LocalDateTime now = LocalDateTime.now();
        LocalDateTime firstDayOfNextMonth = now.with(TemporalAdjusters.firstDayOfNextMonth()).with(LocalTime.MAX);
        return Duration.between(now, firstDayOfNextMonth).toMillis();
    }

    protected String getAssetFreeTrialUsageQuotaKey(String domainId, String assetId) {
        return String.format(Locale.ROOT, ASSET_FREE_TRIAL_USAGE_QUOTA_KEY_FORMAT, assetId,
            YearMonth.from(LocalDate.now()), domainId);
    }

    protected String getAssetFreeTrialUsageQuotaRwLockKey(String domainId, String assertId) {
        return String.format(Locale.ROOT, ASSET_FREE_TRIAL_USAGE_QUOTA_RW_LOCK_FORMAT, assertId,
            YearMonth.from(LocalDate.now()), domainId);
    }
}
