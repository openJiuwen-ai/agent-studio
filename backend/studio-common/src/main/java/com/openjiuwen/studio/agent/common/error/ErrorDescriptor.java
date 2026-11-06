/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.error;

import com.openjiuwen.studio.agent.common.dto.ErrorDetail;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/**
 * COM-03 §4.1: 服务内不可变错误 descriptor。
 * <p>
 * 是内部模型，不是对外 DTO。HTTP/SSE 构建器只提取安全字段（errorCode/httpStatus/
 * messageKey/reasonKey/suggestionKey/requestId/safeDetails/passthroughText/
 * downstreamComponentLabel）做序列化；
 * {@code cause}、{@code downstreamService}、{@code downstreamErrorCode} 不参与
 * 序列化、{@link #equals}、{@link #hashCode} 和 {@link #toString}。
 * {@code passthroughText}（COM-04 §5.2 修订，2026-11-02）是可信 RUNTIME 原码的
 * 受管三段文案，仅在 i18n 无法解析时由构建器回退使用，不参与 equals/hashCode。
 *
 * <p>构造时立即校验不变量：
 * <ul>
 *   <li>六个必填字段非空非 blank；</li>
 *   <li>httpStatus 为 4xx/5xx；</li>
 *   <li>downstreamService 与 downstreamErrorCode 成对出现（都有或都无）；</li>
 *   <li>safeDetails 非空时逐项校验子错误码和子消息非空。</li>
 * </ul>
 */
public final class ErrorDescriptor {

    private final String errorCode;
    private final int httpStatus;
    private final String messageKey;
    private final String reasonKey;
    private final String suggestionKey;
    private final String requestId;
    private final List<ErrorDetail> safeDetails;
    private final DownstreamService downstreamService;
    private final String downstreamErrorCode;
    private final Throwable cause;
    private final PassthroughText passthroughText;
    private final String downstreamComponentLabel;

    public ErrorDescriptor(String errorCode, int httpStatus, String messageKey,
                           String reasonKey, String suggestionKey, String requestId,
                           List<ErrorDetail> safeDetails, DownstreamService downstreamService,
                           String downstreamErrorCode, Throwable cause) {
        this(errorCode, httpStatus, messageKey, reasonKey, suggestionKey, requestId,
            safeDetails, downstreamService, downstreamErrorCode, cause, null, null);
    }

    /**
     * COM-04 §5.2 修订（2026-11-02）：带可信 RUNTIME 受管文案的构造入口。
     *
     * @param passthroughText 可空；仅可信 Runtime 原码且 Manager i18n 缺失时由构建器回退使用
     */
    public ErrorDescriptor(String errorCode, int httpStatus, String messageKey,
                           String reasonKey, String suggestionKey, String requestId,
                           List<ErrorDetail> safeDetails, DownstreamService downstreamService,
                           String downstreamErrorCode, Throwable cause,
                           PassthroughText passthroughText) {
        this(errorCode, httpStatus, messageKey, reasonKey, suggestionKey, requestId,
            safeDetails, downstreamService, downstreamErrorCode, cause, passthroughText, null);
    }

    /**
     * COM-04 §5.2 修订二期（2026-11-02，用户裁定统一族格式）：
     * 下游失败族对外文案统一为
     * {@code error_msg = 族前缀("下游依赖访问失败。")}、
     * {@code error_reason = "组件{label}：{错误信息}"}。
     *
     * @param passthroughText 可空；受管三段文案，i18n 缺失时回退
     * @param downstreamComponentLabel 可空；下游失败组件标签（runtime/builder/obs/…），
     *        非空时构建器启用统一族格式；由 mapper 判定（含 OBS 码族识别），
     *        属安全序列化字段（不含内部服务枚举与诊断语义）
     */
    public ErrorDescriptor(String errorCode, int httpStatus, String messageKey,
                           String reasonKey, String suggestionKey, String requestId,
                           List<ErrorDetail> safeDetails, DownstreamService downstreamService,
                           String downstreamErrorCode, Throwable cause,
                           PassthroughText passthroughText, String downstreamComponentLabel) {
        requireNonBlank(errorCode, "errorCode");
        requireHttpStatus(httpStatus);
        requireNonBlank(messageKey, "messageKey");
        requireNonBlank(reasonKey, "reasonKey");
        requireNonBlank(suggestionKey, "suggestionKey");
        requireNonBlank(requestId, "requestId");
        validateDownstreamPairing(downstreamService, downstreamErrorCode);
        if (downstreamComponentLabel != null && downstreamComponentLabel.isBlank()) {
            throw new IllegalArgumentException(
                "ErrorDescriptor downstreamComponentLabel must not be blank");
        }
        List<ErrorDetail> validatedDetails = validateSafeDetails(safeDetails);

        this.errorCode = errorCode;
        this.httpStatus = httpStatus;
        this.messageKey = messageKey;
        this.reasonKey = reasonKey;
        this.suggestionKey = suggestionKey;
        this.requestId = requestId;
        this.safeDetails = validatedDetails;
        this.downstreamService = downstreamService;
        this.downstreamErrorCode = downstreamErrorCode;
        this.cause = cause;
        this.passthroughText = passthroughText;
        this.downstreamComponentLabel = downstreamComponentLabel;
    }

    public String getErrorCode() {
        return errorCode;
    }

    public int getHttpStatus() {
        return httpStatus;
    }

    public String getMessageKey() {
        return messageKey;
    }

    public String getReasonKey() {
        return reasonKey;
    }

    public String getSuggestionKey() {
        return suggestionKey;
    }

    public String getRequestId() {
        return requestId;
    }

    /**
     * 安全子错误列表。{@code null} 表示省略 details，空列表表示 {@code []}，
     * 非空列表的每个元素已通过校验。
     *
     * <p>COM-03 §5.4/§7: 返回防御性副本——每个 ErrorDetail 复制为不可变值,
     * 防止调用方通过 getter 修改内部状态。
     */
    public List<ErrorDetail> getSafeDetails() {
        if (safeDetails == null) {
            return null;
        }
        List<ErrorDetail> defensive = new ArrayList<>(safeDetails.size());
        for (ErrorDetail d : safeDetails) {
            defensive.add(new ErrorDetail().setErrorCode(d.getErrorCode()).setErrorMsg(d.getErrorMsg()));
        }
        return Collections.unmodifiableList(defensive);
    }

    /**
     * 仅内部使用——直接下游类别。HTTP/SSE 构建器不得读取此字段。
     */
    DownstreamService getDownstreamServiceInternal() {
        return downstreamService;
    }

    /**
     * 仅内部使用——直接下游原码。HTTP/SSE 构建器不得读取此字段。
     */
    String getDownstreamErrorCodeInternal() {
        return downstreamErrorCode;
    }

    /**
     * 仅供最终责任边界记录异常栈。不参与序列化、equals 和 toString。
     */
    public Throwable getCause() {
        return cause;
    }

    /**
     * COM-04 §5.2 修订（2026-11-02）：可信 RUNTIME 原码的受管三段文案；可空。
     * 构建器仅在 i18n 无法解析时回退使用。
     */
    public PassthroughText getPassthroughText() {
        return passthroughText;
    }

    /**
     * 统一族格式的组件标签（runtime/builder/obs/…）；可空。
     * 非空时构建器把 error_reason 组装为 "组件{label}：{错误信息}"。
     */
    public String getDownstreamComponentLabel() {
        return downstreamComponentLabel;
    }

    private static void requireNonBlank(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("ErrorDescriptor " + name + " must not be blank");
        }
    }

    private static void requireHttpStatus(int status) {
        if (status < 400 || status > 599) {
            throw new IllegalArgumentException("httpStatus must be 4xx/5xx, got " + status);
        }
    }

    private static void validateDownstreamPairing(DownstreamService service, String code) {
        // 基础契约 §3/§5：单向约束——downstreamErrorCode 出现时必须同时有
        // downstreamService；传输失败等无原码场景允许只记录 downstreamService。
        if (service == null && code != null && !code.isBlank()) {
            throw new IllegalArgumentException(
                "downstreamErrorCode set but downstreamService is null");
        }
    }

    private static List<ErrorDetail> validateSafeDetails(List<ErrorDetail> details) {
        if (details == null) {
            return null;
        }
        // COM-03 §5.4: 深度不可变——复制 list 和每个 ErrorDetail,
        // 防止外部原 list/原 ErrorDetail 对象修改影响 descriptor。
        List<ErrorDetail> copies = new ArrayList<>(details.size());
        for (int i = 0; i < details.size(); i++) {
            ErrorDetail d = details.get(i);
            if (d == null) {
                throw new IllegalArgumentException("safeDetails[" + i + "] is null");
            }
            if (d.getErrorCode() == null || d.getErrorCode().isBlank()) {
                throw new IllegalArgumentException("safeDetails[" + i + "].errorCode is blank");
            }
            if (d.getErrorMsg() == null || d.getErrorMsg().isBlank()) {
                throw new IllegalArgumentException("safeDetails[" + i + "].errorMsg is blank");
            }
            copies.add(new ErrorDetail().setErrorCode(d.getErrorCode()).setErrorMsg(d.getErrorMsg()));
        }
        return Collections.unmodifiableList(copies);
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (!(o instanceof ErrorDescriptor that)) {
            return false;
        }
        return httpStatus == that.httpStatus
            && Objects.equals(errorCode, that.errorCode)
            && Objects.equals(messageKey, that.messageKey)
            && Objects.equals(reasonKey, that.reasonKey)
            && Objects.equals(suggestionKey, that.suggestionKey)
            && Objects.equals(requestId, that.requestId)
            && Objects.equals(safeDetails, that.safeDetails);
        // cause, downstreamService, downstreamErrorCode intentionally excluded
    }

    @Override
    public int hashCode() {
        return Objects.hash(errorCode, httpStatus, messageKey, reasonKey,
            suggestionKey, requestId, safeDetails);
        // cause, downstreamService, downstreamErrorCode intentionally excluded
    }

    @Override
    public String toString() {
        return "ErrorDescriptor{errorCode='" + errorCode + "', httpStatus=" + httpStatus
            + ", requestId='" + requestId + "'}";
        // cause, downstreamService, downstreamErrorCode, messageKey/reasonKey/suggestionKey
        // intentionally omitted from repr for safety
    }
}
