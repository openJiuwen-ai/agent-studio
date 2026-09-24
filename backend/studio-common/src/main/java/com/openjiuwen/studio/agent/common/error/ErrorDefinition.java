/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.error;

import java.util.Objects;

/**
 * COM-03 §4.2: 错误目录定义的不可变元数据。
 * <p>
 * 由 Manifest {@code i18n_key} 单一治理根键派生三段查找坐标：
 * {@code message_key = i18n_key}、{@code reason_key = i18n_key + ".reason"}、
 * {@code suggestion_key = i18n_key + ".suggestion"}。
 * {@code error_code} 是独立稳定字段，不属于 i18n 文案。
 */
public final class ErrorDefinition {

    private final String errorCode;
    private final int httpStatus;
    private final String i18nKey;

    public ErrorDefinition(String errorCode, int httpStatus, String i18nKey) {
        requireNonBlank(errorCode, "errorCode");
        requireHttpStatus(httpStatus);
        requireNonBlank(i18nKey, "i18nKey");
        this.errorCode = errorCode;
        this.httpStatus = httpStatus;
        this.i18nKey = i18nKey;
    }

    public String getErrorCode() {
        return errorCode;
    }

    public int getHttpStatus() {
        return httpStatus;
    }

    public String getI18nKey() {
        return i18nKey;
    }

    /** 派生的 message 查找坐标 = i18n_key。 */
    public String getMessageKey() {
        return i18nKey;
    }

    /** 派生的 reason 查找坐标 = i18n_key + ".reason"。 */
    public String getReasonKey() {
        return i18nKey + ".reason";
    }

    /** 派生的 suggestion 查找坐标 = i18n_key + ".suggestion"。 */
    public String getSuggestionKey() {
        return i18nKey + ".suggestion";
    }

    private static void requireNonBlank(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("ErrorDefinition " + name + " must not be blank");
        }
    }

    private static void requireHttpStatus(int status) {
        if (status < 400 || status > 599) {
            throw new IllegalArgumentException("httpStatus must be 4xx/5xx, got " + status);
        }
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (!(o instanceof ErrorDefinition that)) {
            return false;
        }
        return httpStatus == that.httpStatus
            && Objects.equals(errorCode, that.errorCode)
            && Objects.equals(i18nKey, that.i18nKey);
    }

    @Override
    public int hashCode() {
        return Objects.hash(errorCode, httpStatus, i18nKey);
    }

    @Override
    public String toString() {
        return "ErrorDefinition{errorCode='" + errorCode + "', httpStatus=" + httpStatus
            + ", i18nKey='" + i18nKey + "'}";
    }
}
