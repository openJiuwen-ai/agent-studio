/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.error.DownstreamService;
import com.openjiuwen.studio.agent.common.error.ErrorDefinition;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorCatalog;

import java.util.Map;
import java.util.Optional;
import java.util.Set;

/**
 * COM-04 §4.2/§4.3: 下游原码 → Manager 定义映射目录。
 * <p>
 * 不可变、构建期固化，不在生产请求中动态读取 YAML。两类数据：
 * <ol>
 *   <li>已识别下游原码集合（parser 信任门 + 诊断写入依据）——当前为 DEF-06 发布的
 *       八个 Builder canonical 码 {@code openjiuwen.13100006~13100013}；</li>
 *   <li>显式 {@code (service, downstreamCode) -> StudioError} 映射表——Manager-owned
 *       精确业务映射；初始为空（八码默认映射 {@code openjiuwen.02001131/502}）。</li>
 * </ol>
 *
 * <p>增加/删除映射时由测试与 {@code tools/observability/error-codes.yaml} 对账。
 * Manager-owned 映射的 StudioError 必须满足 Manifest、i18n、语义和 HTTP 状态约束。
 */
public final class DownstreamErrorMappingCatalog {

    /**
     * DEF-06 发布的 Builder canonical 码——Manager 当前识别的下游原码。
     * Runtime 下游原码暂未登记（Runtime 错误契约独立，后续按需补）。
     */
    private static final Set<String> RECOGNIZED_BUILDER_CODES = Set.of(
        "openjiuwen.13100006", "openjiuwen.13100007", "openjiuwen.13100008",
        "openjiuwen.13100009", "openjiuwen.13100010", "openjiuwen.13100011",
        "openjiuwen.13100012", "openjiuwen.13100013"
    );

    /**
     * 显式 {@code (service, downstreamCode) -> StudioError} 映射表。
     * <p>
     * 初始为空：DEF-06 八码默认映射 {@code DOWNSTREAM_DEPENDENCY_FAILED/502}。
     * 未来产品要求把 Builder 业务语义转为 Manager 参数错误/任务不存在/状态冲突时，
     * 在此表添加 Manager-owned StudioError 映射，并同步 StudioError/catalog/Manifest/
     * i18n/前端兼容测试/回滚说明。
     */
    private static final Map<DownstreamService, Map<String, StudioError>> EXPLICIT_MAPPINGS =
        Map.of();  // 初始无显式映射

    private final ManagerErrorCatalog managerCatalog;

    public DownstreamErrorMappingCatalog(ManagerErrorCatalog managerCatalog) {
        this.managerCatalog = managerCatalog;
    }

    /**
     * 下游原码是否被识别为可信（parser 信任门 + 诊断写入依据）。
     * <p>
     * 精确匹配，不补前缀、不改大小写、不把数字转 canonical。
     */
    public boolean isRecognizedDownstreamCode(DownstreamService service, String code) {
        if (code == null || code.isBlank()) {
            return false;
        }
        if (service == DownstreamService.BUILDER) {
            return RECOGNIZED_BUILDER_CODES.contains(code);
        }
        // RUNTIME / EXTERNAL 下游原码暂未登记
        return false;
    }

    /**
     * 查询显式 Manager-owned 映射。未命中返回 empty（调用方走默认 02001131）。
     */
    public Optional<ErrorDefinition> lookupExplicitMapping(DownstreamService service, String code) {
        if (code == null || code.isBlank()) {
            return Optional.empty();
        }
        Map<String, StudioError> serviceTable = EXPLICIT_MAPPINGS.get(service);
        if (serviceTable == null) {
            return Optional.empty();
        }
        StudioError managerError = serviceTable.get(code);
        if (managerError == null) {
            return Optional.empty();
        }
        return Optional.of(managerCatalog.resolve(managerError));
    }

    /** 默认 Manager 下游依赖失败定义（02001131/502）。 */
    public ErrorDefinition defaultDownstreamFailure() {
        return managerCatalog.downstreamDependencyFailed();
    }
}
