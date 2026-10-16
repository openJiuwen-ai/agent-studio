/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.utils;

/**
 * Manager 会话 ID 校验 profile 的共享编译期常量（COM-05 §12.2）。
 *
 * <p>放在 api 模块以保证依赖方向可用：api 接口方法的 {@code @Pattern} 注解与
 * service 模块 {@code ConversationIdValidator} 的拦截器校验共用同一份正则，
 * 防止两份规则漂移。拦截器接受范围不得宽于对应 Controller 注解。
 */
public final class ConversationIdPatterns {

    /** 普通会话约束：{@code [A-Za-z0-9_-]}，1～64。 */
    public static final String STANDARD_CONVERSATION_REGEXP = "^[a-zA-Z0-9_-]{1,64}$";

    /** Workflow 执行/资产/网页 chat 会话约束（允许括号）：{@code [A-Za-z0-9_()-]}，1～64。 */
    public static final String WORKFLOW_CONVERSATION_REGEXP = "^[a-zA-Z0-9_()-]{1,64}$";

    /** N2L {cid}（冻结契约 1～128）：{@code [A-Za-z0-9._:-]}。 */
    public static final String N2L_CONVERSATION_REGEXP = "^[a-zA-Z0-9._:-]{1,128}$";

    private ConversationIdPatterns() {
    }
}
