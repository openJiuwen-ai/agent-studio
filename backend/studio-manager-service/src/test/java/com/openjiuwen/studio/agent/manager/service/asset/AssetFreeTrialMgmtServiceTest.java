/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.asset;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;

import lombok.SneakyThrows;

import org.apache.commons.lang3.StringUtils;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.MethodOrderer;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestMethodOrder;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Collections;
import java.util.List;
import java.util.Map;

@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
class AssetFreeTrialMgmtServiceTest {
    @Mock
    private RedisClient redisClient;

    @Mock
    private RedisLock redisLock;

    @InjectMocks
    private AssetFreeTrialMgmtService assetFreeTrialMgmtService;

    private static final String TEST_DOMAIN_ID = "testDomainId";

    private static final String TEST_ASSET_ID = "testAssetId";

    private static final String TEST_CONVERSATION_ID = "testConversationId";

    private static final int TEST_MAX_FREE_TRIAL_QUOTA = 2;

    private static MockedStatic<RequestContextUtils> requestContextUtilsMockedStatic;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(assetFreeTrialMgmtService, "maxFreeTrialTimes", TEST_MAX_FREE_TRIAL_QUOTA);
        ReflectionTestUtils.setField(assetFreeTrialMgmtService, "trialQuotaCheckEnabled", true);

        requestContextUtilsMockedStatic = Mockito.mockStatic(RequestContextUtils.class);
        requestContextUtilsMockedStatic.when(RequestContextUtils::getRequestUserDomainId).thenReturn(TEST_DOMAIN_ID);
    }

    @AfterEach
    void tearDown() {
        // 在所有测试完成后关闭 mock
        if (requestContextUtilsMockedStatic != null) {
            requestContextUtilsMockedStatic.close();
        }
    }

    @Test
    void should_get_max_free_trial_quota_as_usage_when_asset_or_domain_id_is_blank() {
        assertEquals(TEST_MAX_FREE_TRIAL_QUOTA,
            assetFreeTrialMgmtService.queryFreeTrialUsageQuota(TEST_ASSET_ID, null));
        assertEquals(TEST_MAX_FREE_TRIAL_QUOTA,
            assetFreeTrialMgmtService.queryFreeTrialUsageQuota((String) null, TEST_DOMAIN_ID));
    }

    @Test
    void should_get_zero_as_usage_when_none_usage_record_stored() {
        when(redisClient.get(anyString())).thenReturn(null);

        assertEquals(0, assetFreeTrialMgmtService.queryFreeTrialUsageQuota(TEST_ASSET_ID, TEST_DOMAIN_ID));
    }

    @Test
    void should_get_usage_equals_stored_usage_record() {
        when(redisClient.get(anyString())).thenReturn("1");

        assertEquals(1, assetFreeTrialMgmtService.queryFreeTrialUsageQuota(TEST_ASSET_ID, TEST_DOMAIN_ID));
    }

    @Test
    void should_get_max_free_trial_quota_as_usage_when_exception_happened_get_stored_record() {
        when(redisClient.get(anyString())).thenThrow(new RuntimeException());

        assertEquals(TEST_MAX_FREE_TRIAL_QUOTA,
            assetFreeTrialMgmtService.queryFreeTrialUsageQuota(TEST_ASSET_ID, TEST_DOMAIN_ID));
    }

    @Test
    void should_get_max_free_trial_quotas_as_usage_when_asset_or_domain_id_is_blank() {
        assertEquals(Collections.emptyMap(),
            assetFreeTrialMgmtService.queryFreeTrialUsageQuota(Collections.singletonList(TEST_ASSET_ID), null));
        assertEquals(Collections.emptyMap(),
            assetFreeTrialMgmtService.queryFreeTrialUsageQuota((List<String>) null, TEST_DOMAIN_ID));
    }

    @Test
    void should_get_zero_as_usages_when_none_usage_record_stored() {
        when(redisClient.getAll(anyList())).thenReturn(Collections.emptyMap());

        Map<String, Integer> freeTrialUsageQuotas = assetFreeTrialMgmtService.queryFreeTrialUsageQuota(
            Collections.singletonList(TEST_ASSET_ID), TEST_DOMAIN_ID);

        assertEquals(0, freeTrialUsageQuotas.get(TEST_ASSET_ID));
    }

    @Test
    void should_get_usages_equals_stored_usage_record() {
        when(redisClient.getAll(anyList())).thenReturn(Collections.singletonMap(
            assetFreeTrialMgmtService.getAssetFreeTrialUsageQuotaKey(TEST_DOMAIN_ID, TEST_ASSET_ID), "1"));

        Map<String, Integer> freeTrialUsageQuotas = assetFreeTrialMgmtService.queryFreeTrialUsageQuota(
            Collections.singletonList(TEST_ASSET_ID), TEST_DOMAIN_ID);

        assertNotNull(freeTrialUsageQuotas);
        assertEquals(1, freeTrialUsageQuotas.get(TEST_ASSET_ID));
    }

    @Test
    void should_get_empty_free_trial_quotas_map_when_exception_happened_get_stored_record() {
        when(redisClient.getAll(anyList())).thenThrow(new RuntimeException());

        Map<String, Integer> freeTrialUsageQuotas = assetFreeTrialMgmtService.queryFreeTrialUsageQuota(
            Collections.singletonList(TEST_ASSET_ID), TEST_DOMAIN_ID);

        assertNotNull(freeTrialUsageQuotas);
        assertEquals(Collections.emptyMap(), freeTrialUsageQuotas);
    }

    @Test
    void should_get_false_when_check_is_in_free_trial_with_any_empty_domain_or_asset() {
        assertFalse(assetFreeTrialMgmtService.isInFreeTrial(StringUtils.EMPTY, TEST_DOMAIN_ID));
        assertFalse(assetFreeTrialMgmtService.isInFreeTrial(TEST_ASSET_ID, StringUtils.EMPTY));
    }

    @SneakyThrows
    @Test
    void should_get_true_when_check_is_in_free_trial_with_null_usage_quota() {
        when(redisClient.get(anyString())).thenReturn(null);
        when(redisLock.tryLock(any())).thenReturn(true);
        when(redisClient.getLock(anyString())).thenReturn(redisLock);
        doNothing().when(redisClient).set(anyString(), anyString(), any());

        assertTrue(assetFreeTrialMgmtService.isInFreeTrial(TEST_ASSET_ID, TEST_CONVERSATION_ID));
        verify(redisClient, times(1)).set(anyString(), anyString(), any());
    }

    @Test
    void should_get_false_when_check_is_in_free_trial_with_full_usage_quota() {
        when(redisClient.get(anyString())).thenReturn("2");
        assertFalse(assetFreeTrialMgmtService.isInFreeTrial(TEST_ASSET_ID, TEST_CONVERSATION_ID));
        verify(redisClient, times(0)).set(anyString(), anyString(), any());
    }

    @SneakyThrows
    @Test
    void should_get_true_when_check_is_in_free_trial_with_not_full_usage() {
        when(redisClient.get(anyString())).thenReturn("1");
        when(redisLock.tryLock(any())).thenReturn(true);
        when(redisClient.getLock(anyString())).thenReturn(redisLock);
        doNothing().when(redisClient).set(anyString(), anyString(), any());

        assertTrue(assetFreeTrialMgmtService.isInFreeTrial(TEST_ASSET_ID, TEST_CONVERSATION_ID));
        verify(redisClient, times(1)).set(anyString(), anyString(), any());
    }

    @SneakyThrows
    @Test
    void should_get_true_when_check_is_in_free_trial_with_not_full_usage_while_add_by_others() {
        when(redisClient.get(anyString())).thenReturn("1").thenReturn("2");
        when(redisLock.tryLock(any())).thenReturn(true);
        when(redisClient.getLock(anyString())).thenReturn(redisLock);
        doNothing().when(redisClient).set(anyString(), anyString(), any());

        assertFalse(assetFreeTrialMgmtService.isInFreeTrial(TEST_ASSET_ID, TEST_CONVERSATION_ID));
        verify(redisClient, times(0)).set(anyString(), anyString(), any());
    }

    @Test
    void should_get_true_when_quota_check_disabled() {
        ReflectionTestUtils.setField(assetFreeTrialMgmtService, "trialQuotaCheckEnabled", false);

        assertTrue(assetFreeTrialMgmtService.isInFreeTrial(TEST_ASSET_ID, TEST_CONVERSATION_ID));
        verify(redisClient, times(0)).get(anyString());
    }
}
