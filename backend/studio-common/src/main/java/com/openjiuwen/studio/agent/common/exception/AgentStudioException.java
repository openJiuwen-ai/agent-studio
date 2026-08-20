/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.exception;

import com.openjiuwen.studio.agent.common.enums.StudioError;

import lombok.Getter;
import lombok.Setter;

import java.io.Serial;
import java.util.List;
import java.util.Locale;

/**
 * AgentStudio运行时异常
 *
 */
@Getter
@Setter
public class AgentStudioException extends RuntimeException {
    @Serial
    private static final long serialVersionUID = 2319282483595953441L;

    /**
     * 错误编码中的i18n定义如果包含占位符，传入填充的字符串
     * @see org.springframework.context.MessageSource#getMessage(String, Object[], Locale)
     */
    private final transient Object[] args;

    private StudioError errorCode;

    private List<String> details;

    /**
     * 标准构造函数 (用于 i18n 参数替换)
     * 注意：此方法不会设置 exception message，getMessage() 可能为空
     */
    public AgentStudioException(StudioError errorCode, Object... args) {
        super();
        this.errorCode = errorCode;
        this.args = args;
    }

    /**
     * 带具体错误信息的构造函数
     * 作用：确保 new AgentStudioException(Error, "HTTP 404") 时，
     * 错误信息能被 getMessage() 获取到，从而被 collectAllExceptionInfo 挖掘并在前端展示。
     *
     * @param errorCode 错误枚举
     * @param message   具体的调试信息/错误描述
     */
    public AgentStudioException(StudioError errorCode, String message) {
        super(message); // 关键：传给父类，这样 e.getMessage() 才有值！
        this.errorCode = errorCode;
        // 兼容策略：同时将 message 作为 args[0] 存入，防止 i18n 模板里有 {0} 占位符
        this.args = new Object[]{message};
    }

    /**
     * 带详情列表的构造函数
     */
    public AgentStudioException(StudioError errorCode, List<String> details, Object... args) {
        super();
        this.errorCode = errorCode;
        this.args = args;
        this.details = details;
    }

    /**
     * 包装原始异常的构造函数
     * 作用：保留原始堆栈 (Cause)
     */
    public AgentStudioException(StudioError errorCode, Exception e, Object... args) {
        super(e); // 传入 cause
        this.errorCode = errorCode;
        this.args = args;
    }

    /**
     * AgentStudioException handling constructor
     * @param message message
     */
    public AgentStudioException(String message) {
        this(StudioError.UNEXPECTED_ERROR, message);
    }
}
