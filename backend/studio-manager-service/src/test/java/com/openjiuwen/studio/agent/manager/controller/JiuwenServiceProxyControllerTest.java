/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.controller;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anySet;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mockConstruction;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.service.JiuwenRuntimeI18nService;

import reactor.core.publisher.Flux;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.MockedConstruction;
import org.mockito.Mockito;
import org.mockito.MockitoAnnotations;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.web.servlet.mvc.method.annotation.ResponseBodyEmitter;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

/**
 * JiuwenServiceProxyController 单元测试，重点覆盖 wrapToSse 的 SSE 错误事件处理逻辑：
 * 上游 Flux 错误时先发送 error 事件帧再 completeWithError，以及 send 抛 IOException 的兜底分支。
 */
@MockitoSettings(strictness = Strictness.LENIENT)
class JiuwenServiceProxyControllerTest {

    @Mock
    private JiuwenRuntimeI18nService jiuwenRuntimeI18nService;

    private JiuwenServiceProxyController controller;

    private AutoCloseable mockitoCloseable;

    @BeforeEach
    void setUp() {
        mockitoCloseable = MockitoAnnotations.openMocks(this);
        // wrapToSse 仅依赖 jiuwenRuntimeI18nService（error 事件 i18n 处理），其余构造参数传 null
        controller = new JiuwenServiceProxyController(null, null, null, null, null, null, jiuwenRuntimeI18nService);
        when(jiuwenRuntimeI18nService.createRuntimeErrorEvent(any()))
            .thenAnswer(invocation -> invocation.getArgument(0));
    }

    @AfterEach
    void tearDown() throws Exception {
        mockitoCloseable.close();
    }

    /**
     * 通过反射调用私有方法 wrapToSse，返回其内部构造的 SseEmitter。
     *
     * @param flux 上游数据流
     * @return wrapToSse 构造并返回的 SseEmitter
     */
    private SseEmitter invokeWrapToSse(Flux<Object> flux) throws Exception {
        Method method = JiuwenServiceProxyController.class.getDeclaredMethod("wrapToSse", Flux.class);
        method.setAccessible(true);
        return (SseEmitter) method.invoke(controller, flux);
    }

    /**
     * 从 SseEmitter.send 收到的参数中查找 Map 类型的事件数据。
     * Spring 6.2 中 SseEmitter.event().data(x).build() 返回 Set<DataWithMediaType>，
     * 非 String 数据（如 error 帧的 Map）以原对象作为 DataWithMediaType 的数据。
     *
     * @param sendArg send 收到的参数
     * @return 事件承载的 Map 数据
     */
    private static Map<String, Object> findMapEvent(Object sendArg) {
        assertTrue(sendArg instanceof Set, "send 参数应为 Set<DataWithMediaType>");
        for (Object item : (Set<?>) sendArg) {
            ResponseBodyEmitter.DataWithMediaType event =
                (ResponseBodyEmitter.DataWithMediaType) item;
            if (event.getData() instanceof Map) {
                @SuppressWarnings("unchecked")
                Map<String, Object> map = (Map<String, Object>) event.getData();
                return map;
            }
        }
        throw new AssertionError("Set 中未找到 Map 类型的事件数据");
    }

    /**
     * 判断 send 参数（Set<DataWithMediaType>）中是否存在包含指定文本的事件数据。
     *
     * @param sendArg  send 收到的参数
     * @param expected 期望出现的事件文本
     * @return 存在包含该文本的事件数据时返回 true
     */
    private static boolean containsEventText(Object sendArg, String expected) {
        if (!(sendArg instanceof Set)) {
            return false;
        }
        for (Object item : (Set<?>) sendArg) {
            ResponseBodyEmitter.DataWithMediaType event =
                (ResponseBodyEmitter.DataWithMediaType) item;
            Object data = event.getData();
            if (data != null && String.valueOf(data).contains(expected)) {
                return true;
            }
        }
        return false;
    }

    /**
     * 用例描述：上游 Flux 正常发射数据时，wrapToSse 应将数据作为事件发送给客户端并正常完成，不发送任何 error 事件
     * 预制条件：mock SseEmitter 构造，jiuwenRuntimeI18nService.createRuntimeErrorEvent 返回原参数
     * 输入参数：Flux.just("hello")，发射单个字符串事件
     * 预期结果：send 收到 data="hello"；complete() 被调用；completeWithError 从未调用；createRuntimeErrorEvent 从未调用
     *
     * @throws Exception 反射调用可能抛出的异常
     */
    @Test
    void testWrapToSseShouldSendDataAndCompleteOnNormalFlux() throws Exception {
        try (MockedConstruction<SseEmitter> mocked = mockConstruction(SseEmitter.class)) {
            invokeWrapToSse(Flux.just("hello"));
            SseEmitter emitterMock = mocked.constructed().get(0);

            ArgumentCaptor<Set> sendCaptor = ArgumentCaptor.forClass(Set.class);
            verify(emitterMock).send(sendCaptor.capture());
            assertTrue(containsEventText(sendCaptor.getValue(), "hello"), "发送事件应包含正常数据 hello");

            verify(emitterMock).complete();
            verify(emitterMock, never()).completeWithError(any());
            verify(jiuwenRuntimeI18nService, never()).createRuntimeErrorEvent(any());
        }
    }

    /**
     * 用例描述：上游 Flux 出错时，wrapToSse 应先发送 error 事件帧（event=error，data.code=JIU_WEN_SERVICE_EXCEPTION，
     * data.message=""（不携带上游异常，i18n 友好文案由 createRuntimeErrorEvent 按 code 生成 error_msg）），
     * 再以 AgentStudioException 调用 completeWithError 结束流
     * 预制条件：mock SseEmitter 构造，jiuwenRuntimeI18nService.createRuntimeErrorEvent 返回原参数
     * 输入参数：Flux.error(new RuntimeException("boom"))，上游异常信息为 "boom"
     * 预期结果：send 收到 error 帧且 code="1058"、message=""；completeWithError 参数 errorCode=JIU_WEN_SERVICE_EXCEPTION；
     *          complete() 从未调用；createRuntimeErrorEvent 收到 error 帧的 code（用于生成 i18n error_msg）与空 message
     *
     * @throws Exception 反射调用可能抛出的异常
     */
    @Test
    void testWrapToSseShouldSendErrorFrameAndCompleteWithErrorOnFluxError() throws Exception {
        try (MockedConstruction<SseEmitter> mocked = mockConstruction(SseEmitter.class)) {
            invokeWrapToSse(Flux.error(new RuntimeException("boom")));
            SseEmitter emitterMock = mocked.constructed().get(0);

            ArgumentCaptor<Set> sendCaptor = ArgumentCaptor.forClass(Set.class);
            verify(emitterMock).send(sendCaptor.capture());
            Map<String, Object> errorEvent = findMapEvent(sendCaptor.getValue());
            assertEquals("error", errorEvent.get("event"), "事件类型应为 error");
            assertTrue(errorEvent.get("data") instanceof Map, "error 帧的 data 应为 Map");
            Map<String, Object> errorData = (Map<String, Object>) errorEvent.get("data");
            assertEquals(StudioError.JIU_WEN_SERVICE_EXCEPTION.getCode(), errorData.get("code"),
                "error 帧的 code 应为 JIU_WEN_SERVICE_EXCEPTION 错误码");
            assertEquals("", errorData.get("message"), "error 帧的 message 应为空字符串，不暴露上游异常信息");

            ArgumentCaptor<Map> i18nCaptor = ArgumentCaptor.forClass(Map.class);
            verify(jiuwenRuntimeI18nService).createRuntimeErrorEvent(i18nCaptor.capture());
            assertEquals(StudioError.JIU_WEN_SERVICE_EXCEPTION.getCode(), i18nCaptor.getValue().get("code"));
            assertEquals("", i18nCaptor.getValue().get("message"),
                "createRuntimeErrorEvent 收到的 message 应为空字符串，error_msg 由 code 生成");

            ArgumentCaptor<Throwable> completeCaptor = ArgumentCaptor.forClass(Throwable.class);
            verify(emitterMock).completeWithError(completeCaptor.capture());
            assertTrue(completeCaptor.getValue() instanceof AgentStudioException);
            assertEquals(StudioError.JIU_WEN_SERVICE_EXCEPTION,
                ((AgentStudioException) completeCaptor.getValue()).getErrorCode());

            verify(emitterMock, never()).complete();
        }
    }

    /**
     * 用例描述：正常数据 send 抛 IOException 时，data 回调捕获异常并抛出 AgentStudioException，
     * 该异常由 Reactor 转为 onError，最终仍发送 error 帧并 completeWithError
     * 预制条件：mock SseEmitter 且 send(Set) 抛 IOException
     * 输入参数：Flux.just("hello")，send 正常事件时抛 IOException
     * 预期结果：completeWithError 被调用（参数 errorCode=JIU_WEN_SERVICE_EXCEPTION）；complete() 从未调用；
     *          send 被调用两次（正常事件一次 + error 帧一次，均抛 IOException 被处理）
     *
     * @throws Exception 反射调用可能抛出的异常
     */
    @Test
    void testWrapToSseShouldThrowAgentStudioExceptionWhenNormalEventSendFails() throws Exception {
        try (MockedConstruction<SseEmitter> mocked = mockConstruction(SseEmitter.class,
            (emitterMock, context) -> {
                try {
                    doThrow(new IOException("send failed")).when(emitterMock).send(anySet());
                } catch (IOException e) {
                    throw new IllegalStateException(e);
                }
            })) {
            invokeWrapToSse(Flux.just("hello"));
            SseEmitter emitterMock = mocked.constructed().get(0);

            verify(emitterMock, Mockito.times(2)).send(anySet());
            ArgumentCaptor<Throwable> completeCaptor = ArgumentCaptor.forClass(Throwable.class);
            verify(emitterMock).completeWithError(completeCaptor.capture());
            assertTrue(completeCaptor.getValue() instanceof AgentStudioException);
            assertEquals(StudioError.JIU_WEN_SERVICE_EXCEPTION,
                ((AgentStudioException) completeCaptor.getValue()).getErrorCode());
            verify(emitterMock, never()).complete();
        }
    }

    /**
     * 用例描述：error 回调中发送 error 事件帧本身抛 IOException 时，该异常被内层 catch 吞掉，
     * 但仍需继续调用 completeWithError 结束流，避免连接悬挂
     * 预制条件：mock SseEmitter 且 send(Set) 抛 IOException
     * 输入参数：Flux.error(new RuntimeException("boom"))，发送 error 帧时抛 IOException
     * 预期结果：completeWithError 仍被调用（参数 errorCode=JIU_WEN_SERVICE_EXCEPTION）；complete() 从未调用
     *
     * @throws Exception 反射调用可能抛出的异常
     */
    @Test
    void testWrapToSseShouldStillCompleteWithErrorWhenErrorEventSendFails() throws Exception {
        try (MockedConstruction<SseEmitter> mocked = mockConstruction(SseEmitter.class,
            (emitterMock, context) -> {
                try {
                    doThrow(new IOException("send failed")).when(emitterMock).send(anySet());
                } catch (IOException e) {
                    throw new IllegalStateException(e);
                }
            })) {
            invokeWrapToSse(Flux.error(new RuntimeException("boom")));
            SseEmitter emitterMock = mocked.constructed().get(0);

            verify(emitterMock).send(anySet());
            ArgumentCaptor<Throwable> completeCaptor = ArgumentCaptor.forClass(Throwable.class);
            verify(emitterMock).completeWithError(completeCaptor.capture());
            assertTrue(completeCaptor.getValue() instanceof AgentStudioException);
            assertEquals(StudioError.JIU_WEN_SERVICE_EXCEPTION,
                ((AgentStudioException) completeCaptor.getValue()).getErrorCode());
            verify(emitterMock, never()).complete();
        }
    }

    /**
     * 用例描述：上游发射 Map 数据但事件类型不是 error 时，parseEventMsg 不应走 i18n 处理分支，
     * 数据应原样透传发送
     * 预制条件：mock SseEmitter 构造，jiuwenRuntimeI18nService.createRuntimeErrorEvent 返回原参数
     * 输入参数：Flux.just(Map{event=message, data=hi})，非 error 的 Map 事件
     * 预期结果：send 收到原 Map（event=message、data=hi）；createRuntimeErrorEvent 从未调用；complete() 被调用
     *
     * @throws Exception 反射调用可能抛出的异常
     */
    @Test
    void testWrapToSseShouldSendMapDataAsIsWhenNotErrorEvent() throws Exception {
        try (MockedConstruction<SseEmitter> mocked = mockConstruction(SseEmitter.class)) {
            Map<String, Object> normalEvent = new HashMap<>();
            normalEvent.put("event", "message");
            normalEvent.put("data", "hi");
            invokeWrapToSse(Flux.just(normalEvent));
            SseEmitter emitterMock = mocked.constructed().get(0);

            ArgumentCaptor<Set> sendCaptor = ArgumentCaptor.forClass(Set.class);
            verify(emitterMock).send(sendCaptor.capture());
            Map<String, Object> sent = findMapEvent(sendCaptor.getValue());
            assertEquals("message", sent.get("event"), "非 error 事件应按原样透传");
            assertEquals("hi", sent.get("data"), "非 error 事件 data 应按原样透传");

            verify(jiuwenRuntimeI18nService, never()).createRuntimeErrorEvent(any());
            verify(emitterMock).complete();
            verify(emitterMock, never()).completeWithError(any());
        }
    }

    /**
     * 用例描述：parseEventMsg 处理 error 帧时 i18n 处理抛异常，应被 catch 兜底并返回原始事件，
     * completeWithError 仍正常执行，保证流正确终止
     * 预制条件：mock SseEmitter 构造，createRuntimeErrorEvent 抛 RuntimeException
     * 输入参数：Flux.error(new RuntimeException("boom"))，上游异常信息为 "boom"
     * 预期结果：send 收到未 i18n 处理的原始 error 帧（code 保留、message 为空字符串）；completeWithError 仍被调用；complete() 从未调用
     *
     * @throws Exception 反射调用可能抛出的异常
     */
    @Test
    void testWrapToSseShouldStillCompleteWithErrorWhenParseEventMsgFails() throws Exception {
        when(jiuwenRuntimeI18nService.createRuntimeErrorEvent(any()))
            .thenThrow(new RuntimeException("i18n fail"));
        try (MockedConstruction<SseEmitter> mocked = mockConstruction(SseEmitter.class)) {
            invokeWrapToSse(Flux.error(new RuntimeException("boom")));
            SseEmitter emitterMock = mocked.constructed().get(0);

            ArgumentCaptor<Set> sendCaptor = ArgumentCaptor.forClass(Set.class);
            verify(emitterMock).send(sendCaptor.capture());
            Map<String, Object> errorEvent = findMapEvent(sendCaptor.getValue());
            assertEquals("error", errorEvent.get("event"), "事件类型应为 error");
            Map<String, Object> errorData = (Map<String, Object>) errorEvent.get("data");
            assertEquals(StudioError.JIU_WEN_SERVICE_EXCEPTION.getCode(), errorData.get("code"),
                "原始 error 帧应保留 JIU_WEN_SERVICE_EXCEPTION 错误码");
            assertEquals("", errorData.get("message"), "原始 error 帧的 message 应为空字符串，不暴露上游异常信息");

            ArgumentCaptor<Throwable> completeCaptor = ArgumentCaptor.forClass(Throwable.class);
            verify(emitterMock).completeWithError(completeCaptor.capture());
            assertTrue(completeCaptor.getValue() instanceof AgentStudioException);
            assertEquals(StudioError.JIU_WEN_SERVICE_EXCEPTION,
                ((AgentStudioException) completeCaptor.getValue()).getErrorCode());
            verify(emitterMock, never()).complete();
        }
    }
}
