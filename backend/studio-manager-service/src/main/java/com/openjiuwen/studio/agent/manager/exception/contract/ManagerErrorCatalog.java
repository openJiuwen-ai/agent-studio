/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.contract;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.error.ErrorDefinition;

/**
 * COM-03 §4.2: Manager 错误目录适配器。
 * <p>
 * 以 StudioError 枚举为目录源，以 full_code 为 i18n 治理根键，
 * 派生 message_key/reason_key/suggestion_key。
 */
public class ManagerErrorCatalog {

    /**
     * 从 StudioError 枚举构建 ErrorDefinition。
     */
    public ErrorDefinition resolve(StudioError error) {
        String fullCode = error.getFullCode();
        return new ErrorDefinition(fullCode, error.getHttpStatus().value(), fullCode);
    }

    /** COM-03 框架码：下游依赖失败（502）。 */
    public ErrorDefinition downstreamDependencyFailed() {
        return resolve(StudioError.DOWNSTREAM_DEPENDENCY_FAILED);
    }

    /** 兜底码：服务内部错误（500）。 */
    public ErrorDefinition unexpectedError() {
        return resolve(StudioError.UNEXPECTED_ERROR);
    }

    /** 参数校验失败（400）。 */
    public ErrorDefinition validationFailed() {
        return resolve(StudioError.METHOD_ARGUMENT_NOT_VALID);
    }
}
