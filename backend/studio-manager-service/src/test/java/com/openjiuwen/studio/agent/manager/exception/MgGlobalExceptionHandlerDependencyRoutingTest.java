/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.RequestHeaderHolderUtils;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.context.support.StaticMessageSource;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.data.redis.RedisConnectionFailureException;
import org.springframework.http.ResponseEntity;

import java.util.Locale;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 统一族格式（COM-04 §5.2 修订二期，2026-11-02）：DataAccessException 内
 * Redis 分流 + Redisson 异常族的组件标签路由。
 * <p>
 * 背景：Spring Data Redis 异常（RedisConnectionFailureException 等）与 SQL
 * 异常同属 {@code DataAccessException} 体系，须按包名分流；Redisson 自身
 * 异常族（{@code org.redisson.client.RedisException}，本地 RedisClient 的
 * SPI 实现）不继承 DataAccessException，须单独接住——否则 Redis 失败会被
 * 误标 mysql 或漏到 02001002 兜底。
 */
class MgGlobalExceptionHandlerDependencyRoutingTest {

    /**
     * 语种固定（评审修订 2026-11-03）：断言的族文案按语种分档，而
     * LanguageUtils 读的是 {@link RequestHeaderHolderUtils} 的 ThreadLocal
     * （生产由 X-Language Filter 写入，Spring 的 LocaleContextHolder 不参与），
     * 测试显式置 zh-CN 避免依赖 ThreadLocal 缺省形态。
     */
    @BeforeEach
    void pinRequestLanguage() {
        RequestHeaderHolderUtils.setRequestLanguage("zh-CN");
    }

    @AfterEach
    void clearRequestLanguage() {
        RequestHeaderHolderUtils.clear();
    }

    private MgGlobalExceptionHandler handler() {
        StaticMessageSource ms = new StaticMessageSource();
        ms.addMessage("openjiuwen.02001051", Locale.CHINA, "Redis访问失败。");
        ms.addMessage("openjiuwen.02001051.reason", Locale.CHINA, "Redis连接或读写失败。");
        ms.addMessage("openjiuwen.02001051.suggestion", Locale.CHINA, "请检查Redis服务状态。");
        ms.addMessage("openjiuwen.02001042", Locale.CHINA, "SQL执行失败。");
        ms.addMessage("openjiuwen.02001042.reason", Locale.CHINA, "数据库访问失败。");
        ms.addMessage("openjiuwen.02001042.suggestion", Locale.CHINA, "请检查数据库。");
        return new MgGlobalExceptionHandler(new I18nUtil(ms));
    }

    @Test
    void dataAccessException_redisFamily_routes_to_redis_code_and_label() {
        // Spring Data Redis 异常继承 DataAccessException——须分流，否则误标 mysql
        RedisConnectionFailureException ex = new RedisConnectionFailureException("connection refused");
        ResponseEntity<ErrorRsp> resp = handler().handleDataAccessException(ex);
        ErrorRsp body = resp.getBody();
        assertEquals("openjiuwen.02001051", body.getErrorCode());
        assertEquals("下游依赖访问失败。", body.getErrorMsg());
        assertTrue(body.getErrorReason().startsWith("组件redis："),
            "error_reason must carry redis component label, got: " + body.getErrorReason());
    }

    @Test
    void dataAccessException_nonRedis_routes_to_sql_code_and_mysql_label() {
        DataAccessResourceFailureException ex = new DataAccessResourceFailureException("db down");
        ResponseEntity<ErrorRsp> resp = handler().handleDataAccessException(ex);
        ErrorRsp body = resp.getBody();
        assertEquals("openjiuwen.02001042", body.getErrorCode());
        assertEquals("下游依赖访问失败。", body.getErrorMsg());
        assertTrue(body.getErrorReason().startsWith("组件mysql："),
            "error_reason must carry mysql component label, got: " + body.getErrorReason());
    }

    @Test
    void redissonException_routes_to_redis_code_and_label() {
        // Redisson 自身异常族不继承 DataAccessException——走专用 handler（handleException）
        org.redisson.client.RedisException ex =
            new org.redisson.client.RedisException("node disconnected");
        ResponseEntity<ErrorRsp> resp = handler().handleException(ex);
        ErrorRsp body = resp.getBody();
        assertEquals("openjiuwen.02001051", body.getErrorCode());
        assertEquals("下游依赖访问失败。", body.getErrorMsg());
        assertTrue(body.getErrorReason().startsWith("组件redis："),
            "error_reason must carry redis component label, got: " + body.getErrorReason());
    }
}
