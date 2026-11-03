/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.utils;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;

import org.springframework.context.MessageSource;
import org.springframework.stereotype.Component;

import java.util.Locale;

/**
 * 国际化Util类
 *
 */
@Component
public class I18nUtil {
    private final MessageSource messageSource;

    public I18nUtil(MessageSource messageSource) {
        this.messageSource = messageSource;
    }

    /**
     * 按错误码获取错误信息
     *
     * @param code 错误码
     * @return 异常信息
     */
    public String getMessage(String code, Object... args) {
        // 防御性兜底：i18n 资源缺失时返回 code 本身，避免 MessageSource 抛 NoSuchMessageException
        // 导致全局异常处理器自己崩掉、客户端收不到可读错误（表现为"空响应/语法错误"）。
        try {
            return messageSource.getMessage(code, args, code, LanguageUtils.getLanguageLocale());
        } catch (Exception e) {
            return code;
        }
    }

    /**
     * 按错误码 + 显式 locale 获取错误信息。
     * <p>COM-03 builder 传 locale 解析文案，不可把 locale 当作 varargs 的 args[0] 填占位符
     * （否则 {0} 占位被填成 locale.toString()）。显式重载避免落入 getMessage(String, Object...) 的 varargs。
     *
     * @param code   错误码 i18n key
     * @param args   i18n 占位符填充值（资源未发布时为资源类型等业务参数）
     * @param locale 显式 locale，不被当作占位符参数
     * @return 异常信息；资源缺失时返回 code 本身
     */
    public String getMessage(String code, Object[] args, Locale locale) {
        try {
            // 空 args 归一为 null：MessageFormat 对 null/空数组 + {0} 占位符不抛异常（已实证），
            // 但留 {0} 原文。归一为 null 统一"空 args"契约，便于上层判断；defaultMessage=code 兜底防崩。
            Object[] effective = (args != null && args.length == 0) ? null : args;
            return messageSource.getMessage(code, effective, code, locale);
        } catch (Exception e) {
            return code;
        }
    }

    /**
     * 按错误码获取错误信息
     *
     * @param studioError errorCode
     * @return 异常信息
     */
    public String getMessage(StudioError studioError, Object... args) {
        String code = "openjiuwen." + studioError.getModule().getSubCode() + studioError.getCode();
        try {
            return messageSource.getMessage(code, args, code, LanguageUtils.getLanguageLocale());
        } catch (Exception e) {
            return code;
        }
    }

    /**
     * 按错误码获取建议
     *
     * @param studioError errorCode
     * @return 建议信息
     */
    public String getSuggestion(StudioError studioError, Object... args) {
        String code = "openjiuwen." + studioError.getModule().getSubCode() + studioError.getCode() + ".suggestion";
        try {
            return messageSource.getMessage(code, args, LanguageUtils.getLanguageLocale());
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * 解析全量错误信息并返回结构体
     *
     * @param exception 异常对象
     * @return 包含全量错误信息的结构体
     */
    public ErrorInfo getMessage(AgentStudioException exception) {
        String code = "openjiuwen." + exception.getErrorCode().getModule().getSubCode() + exception.getErrorCode()
            .getCode();
        String message = getMessage(code, exception.getArgs());
        String reason = safeGetMessage(code + ".reason", exception.getArgs());
        String suggestion = safeGetMessage(code + ".suggestion", exception.getArgs());
        return new ErrorInfo(message, reason, suggestion);
    }

    private String safeGetMessage(String key, Object[] args) {
        try {
            return getMessage(key, args);
        } catch (Exception e) {
            return null;
        }
    }
}
