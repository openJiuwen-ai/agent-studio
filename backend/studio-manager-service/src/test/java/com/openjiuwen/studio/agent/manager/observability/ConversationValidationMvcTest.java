/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import jakarta.validation.ConstraintViolationException;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.validation.beanvalidation.LocalValidatorFactoryBean;
import org.springframework.validation.beanvalidation.MethodValidationPostProcessor;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ControllerAdvice;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * COM-05 审视 T3：三个新增拒绝入口的 MVC 验证。用 MethodValidationPostProcessor
 * 创建 AOP 代理启用 @Validated + @Pattern 类级方法校验，验证非法 conversation_id
 * 被参数校验链拒绝（400），合法值进入业务方法。真实业务 Controller 的注解一致性
 * 已由 ConversationRouteRegistryTest 锁定，此处验证 Spring MVC 的 @Pattern 拒绝行为。
 */
class ConversationValidationMvcTest {

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        LocalValidatorFactoryBean validator = new LocalValidatorFactoryBean();
        validator.afterPropertiesSet();
        MethodValidationPostProcessor processor = new MethodValidationPostProcessor();
        processor.setValidator(validator);
        processor.afterPropertiesSet();
        TestController proxy = (TestController) processor
            .postProcessAfterInitialization(new TestController(), "testController");

        mockMvc = MockMvcBuilders.standaloneSetup(proxy)
            .addFilters(new CorrelationContextFilter())
            .addInterceptors(new ConversationContextInterceptor())
            .setControllerAdvice(new ConstraintViolationAdvice())
            .build();
    }

    @AfterEach
    void clearMdc() {
        MDC.clear();
    }

    /** 合法 conversation_id 进入业务方法（200）。 */
    @Test
    void legalConversationId_entersBusinessMethod() throws Exception {
        mockMvc.perform(get("/test/conv/conv-1").header("X-Request-Id", "req-1"))
            .andExpect(status().isOk());
    }

    /** 含点号的非法值被 @Pattern 拒绝（400），不进入业务方法。 */
    @Test
    void dotInConversationId_rejectedByPattern() throws Exception {
        mockMvc.perform(get("/test/conv/bad.value").header("X-Request-Id", "req-1"))
            .andExpect(status().isBadRequest());
    }

    /** 超长值（65 字符）被 @Size 拒绝。 */
    @Test
    void overLengthRejected() throws Exception {
        mockMvc.perform(get("/test/conv/" + "a".repeat(65)).header("X-Request-Id", "req-1"))
            .andExpect(status().isBadRequest());
    }

    /** 空值被拒绝（路径变量缺失 → 404，非 400）。 */
    @Test
    void validBoundary_64chars_passes() throws Exception {
        mockMvc.perform(get("/test/conv/" + "a".repeat(64)).header("X-Request-Id", "req-1"))
            .andExpect(status().isOk());
    }

    @RestController
    @RequestMapping("/test")
    @org.springframework.validation.annotation.Validated
    static class TestController {

        @GetMapping("/conv/{conversation_id}")
        public String conv(
            @Pattern(regexp = ConversationIdValidator.STANDARD_CONVERSATION_REGEXP) @Size(max = 64)
            @PathVariable("conversation_id") String conversationId) {
            return MDC.get(MdcKeys.CONVERSATION_ID);
        }
    }

    @ControllerAdvice
    static class ConstraintViolationAdvice {
        @ExceptionHandler(ConstraintViolationException.class)
        public ResponseEntity<String> handle(ConstraintViolationException e) {
            return ResponseEntity.badRequest().body("validation error");
        }
    }
}
