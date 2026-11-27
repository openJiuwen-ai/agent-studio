/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.contract;

import com.openjiuwen.studio.agent.common.error.ErrorDescriptor;
import com.openjiuwen.studio.agent.common.error.PassthroughText;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerHttpErrorResponseBuilder.I18nResolver;

import java.util.Locale;

/**
 * COM-04 §5.2 修订二期（2026-11-02 用户裁定）：下游失败族统一文案组装。
 * <p>
 * 统一格式（由 mapper 打在 descriptor 上的组件标签触发）：
 * <ul>
 *   <li>{@code error_msg = 族前缀}（"下游依赖访问失败。"，取默认下游失败码 i18n，缺失回退字面量）；</li>
 *   <li>{@code error_reason = "组件{label}：{错误信息}"}——错误信息优先级：
 *       Manager i18n 命中的原码 message → 帧内受管 error_msg →
 *       （兜底码时）i18n reason → 字面量"下游服务调用返回错误或网络不可达"；</li>
 *   <li>{@code error_suggestion}：原码 i18n suggestion → 受管 error_suggestion →
 *       族 suggestion → 字面量"请检查下游服务状态后重试"。</li>
 * </ul>
 * 组装结果恒非空（字面量终兜底），fail-closed 的"不返回空文案"约束按构造满足；
 * 非下游错误不走本类（保持 i18n 三键 + fail-closed 抛出语义）。
 */
public final class DownstreamFamilyFormat {

    /** 族前缀 i18n key（即默认下游依赖失败码的 message key）。 */
    static final String FAMILY_MSG_KEY = "openjiuwen.02001131";

    private static final String FAMILY_MSG_FALLBACK_ZH = "下游依赖访问失败。";
    private static final String FAMILY_MSG_FALLBACK_EN = "Downstream dependency access failed.";
    private static final String GENERIC_DETAIL_ZH = "下游服务调用返回错误或网络不可达";
    private static final String GENERIC_DETAIL_EN =
        "downstream service call returned an error or the network is unreachable";
    private static final String FAMILY_SUGGESTION_FALLBACK_ZH = "请检查下游服务状态后重试";
    private static final String FAMILY_SUGGESTION_FALLBACK_EN =
        "Please check the downstream service status and retry.";

    private DownstreamFamilyFormat() {
    }

    // ---- 纯字面量兜底（公开给渲染失败时的硬编码回退,评审修订 2026-11-03 三轮:
    //      AgentServiceProxyService.renderDownstreamErrorOrSafeFallback 的 catch
    //      分支曾硬编码中文,与族格式的中英分档不一致——英文用户在渲染失败兜底
    //      路径会收到中文错误。此组方法不依赖 resolver/i18n,按语种取字面量) ----

    /** 渲染失败兜底:族前缀字面量。 */
    public static String fallbackMessage(Locale locale) {
        return isChinese(locale) ? FAMILY_MSG_FALLBACK_ZH : FAMILY_MSG_FALLBACK_EN;
    }

    /** 渲染失败兜底:reason 字面量（"组件{label}：…"/"component {label}: …";label 可空）。 */
    public static String fallbackReason(String label, Locale locale) {
        String detail = isChinese(locale) ? GENERIC_DETAIL_ZH : GENERIC_DETAIL_EN;
        if (label == null || label.isBlank()) {
            return detail;
        }
        return isChinese(locale)
            ? "组件" + label + "：" + detail
            : "component " + label + ": " + detail;
    }

    /** 渲染失败兜底:suggestion 字面量。 */
    public static String fallbackSuggestion(Locale locale) {
        return isChinese(locale)
            ? FAMILY_SUGGESTION_FALLBACK_ZH : FAMILY_SUGGESTION_FALLBACK_EN;
    }

    /** error_msg：族前缀。 */
    static String message(I18nResolver resolver, Object[] args, Locale locale) {
        String resolved = resolveOrNull(resolver, FAMILY_MSG_KEY, args, locale);
        if (resolved != null) {
            return resolved;
        }
        return isChinese(locale) ? FAMILY_MSG_FALLBACK_ZH : FAMILY_MSG_FALLBACK_EN;
    }

    /** error_reason："组件{label}：{错误信息}"（中文语种）/"component {label}: {…}"（其他语种）。 */
    static String reason(I18nResolver resolver, ErrorDescriptor descriptor, String label, Object[] args, Locale locale) {
        String phrase = isChinese(locale)
            ? "组件" + label + "：" : "component " + label + ": ";
        return phrase + detail(resolver, descriptor, args, locale);
    }

    /** error_suggestion：三级回退。 */
    static String suggestion(I18nResolver resolver, ErrorDescriptor descriptor, Object[] args, Locale locale) {
        PassthroughText passthrough = descriptor.getPassthroughText();
        String resolved = resolveOrNull(resolver, descriptor.getSuggestionKey(), args, locale);
        if (resolved != null) {
            return resolved;
        }
        if (passthrough != null && passthrough.getSuggestion() != null
            && !passthrough.getSuggestion().isBlank()) {
            return passthrough.getSuggestion();
        }
        String family = resolveOrNull(resolver, FAMILY_MSG_KEY + ".suggestion", args, locale);
        if (family != null) {
            return family;
        }
        return isChinese(locale)
            ? FAMILY_SUGGESTION_FALLBACK_ZH : FAMILY_SUGGESTION_FALLBACK_EN;
    }

    /** 错误信息本体：兜底码（messageKey 即族 key）取其 i18n reason；透传码取 message/受管文案。 */
    private static String detail(I18nResolver resolver, ErrorDescriptor descriptor, Object[] args, Locale locale) {
        if (FAMILY_MSG_KEY.equals(descriptor.getMessageKey())) {
            // 兜底码：无可信原码细节 → 用族 reason 文案做"错误信息"
            String reason = resolveOrNull(resolver, descriptor.getReasonKey(), args, locale);
            if (reason != null) {
                return reason;
            }
            return isChinese(locale) ? GENERIC_DETAIL_ZH : GENERIC_DETAIL_EN;
        }
        PassthroughText passthrough = descriptor.getPassthroughText();
        String resolved = resolveOrNull(resolver, descriptor.getMessageKey(), args, locale);
        if (resolved != null) {
            return resolved;
        }
        if (passthrough != null && passthrough.getMessage() != null
            && !passthrough.getMessage().isBlank()) {
            return passthrough.getMessage();
        }
        String reason = resolveOrNull(resolver, descriptor.getReasonKey(), args, locale);
        if (reason != null) {
            return reason;
        }
        return isChinese(locale) ? GENERIC_DETAIL_ZH : GENERIC_DETAIL_EN;
    }

    /**
     * 宽松解析：blank / 回显 key（I18nUtil 以 key 作默认值）/ resolver 异常 均视为未命中返回 null。
     * 区别于构建器的 fail-closed safeResolve——族格式按构造兜底，不需要抛出。
     */
    static String resolveOrNull(I18nResolver resolver, String key, Object[] args, Locale locale) {
        String result;
        try {
            result = resolver.resolve(key, args, locale);
        } catch (RuntimeException e) {
            return null;
        }
        if (result == null || result.isBlank() || key.equals(result)) {
            return null;
        }
        return result;
    }

    private static boolean isChinese(Locale locale) {
        return locale != null && locale.getLanguage().toLowerCase(Locale.ROOT).startsWith("zh");
    }
}
