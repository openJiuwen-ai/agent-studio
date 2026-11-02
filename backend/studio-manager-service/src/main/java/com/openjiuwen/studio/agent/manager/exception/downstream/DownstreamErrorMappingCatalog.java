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
     * RUNTIME 可信码形（COM-04 §5.2 修订，2026-11-02）。
     * <p>
     * 与 Runtime 实际码宇宙对齐，且与 Builder canonical 码族（{@code 13xxxxxx}）正交：
     * <ul>
     *   <li>{@code 1[0-2]\d{4}}——引擎/组件 6 位码族（100000~129999，
     *       {@code openjiuwen/core/common/exception/codes.py} 与
     *       {@code jiuwen/common/exception/status_code.py} 全集，如 101003）；</li>
     *   <li>{@code 999999}——Runtime 错误帧未知码兜底（其自身 i18n 有三段文案）；</li>
     *   <li>{@code 12\d{5,6}}——Runtime error_contract 自有目录（121007/12100001~06）；</li>
     *   <li>{@code 0\d{7}}——应用层 8 位码族（02001003/02201021 等，与 Manager i18n 共库）。</li>
     * </ul>
     * 刻意不信任：8 位 {@code 13} 头（Builder canonical 族——跨服务不信任，
     * 修复 2026-10-27 格式门放行 {@code 13100006} 误入 RUNTIME 的回归）、
     * 任意 7 位、任意其他前缀。
     */
    static final String RUNTIME_CANONICAL_SHAPE = "1[0-2]\\d{4}|999999|12\\d{5,6}|0\\d{7}";

    /**
     * DEF-06 发布的 Builder canonical 码——Manager 当前识别的下游原码。
     * <p>
     * 2026-10-27 备注（已被 2026-11-02 修订取代）：此前对 RUNTIME 按
     * "openjiuwen. + 任意 7~8 位数字"做格式信任，导致 ①引擎 6 位码族全灭、
     * ②Builder canonical 码被 RUNTIME 身份误信、③正则随业务演进失配。
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
     * <p>
     * RUNTIME（2026-11-02 修订）：按 {@link #RUNTIME_CANONICAL_SHAPE} 码形信任
     * （引擎 6 位族/兜底 999999/error_contract 12 族/应用层 0 头 8 位族），
     * 与 Builder canonical 码族正交——Builder 码到 RUNTIME 身份不跨服务误信。
     * 信任后 Parser 提取的原码可透传到 ErrorDescriptor，构建器对 Manager i18n
     * 缺失的码回退使用帧内受管三段文案，前端不再只见兜底 02001131。
     */
    public boolean isRecognizedDownstreamCode(DownstreamService service, String code) {
        if (code == null || code.isBlank()) {
            return false;
        }
        if (service == DownstreamService.BUILDER) {
            return RECOGNIZED_BUILDER_CODES.contains(code);
        }
        if (service == DownstreamService.RUNTIME) {
            return isRuntimeCanonicalShape(code);
        }
        return false;
    }

    /**
     * Runtime canonical 码形判定（openjiuwen. 前缀 + RUNTIME_CANONICAL_SHAPE）。
     * <p>
     * 供 parser 信任门与 mapper 1b 分支共用（纵深防御：mapper 侧再次校验，
     * 直接构造的 DownstreamFailure 也不能把非 Runtime 码形推入透传路径）。
     */
    public boolean isRuntimeCanonicalShape(String code) {
        if (code == null || code.isBlank()) {
            return false;
        }
        String digits = code.startsWith("openjiuwen.")
            ? code.substring("openjiuwen.".length()) : "";
        return !digits.isEmpty() && digits.matches(RUNTIME_CANONICAL_SHAPE);
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

    /**
     * RUNTIME 透传解析(2026-10-27 修复, 2026-11-02 修订):按 runtime 原码构造 ErrorDefinition。
     * <p>
     * Runtime 与 Manager 共用 openjiuwen.* 错误码体系——原码即 i18n_key,
     * message/reason/suggestion 由 i18n 按 "{code}" / "{code}.reason" /
     * "{code}.suggestion" 三键查找(与 Manager 自身错误码同一解析路径)。
     * Manager 侧 i18n 已含 runtime 应用层常见码(02001003/02001004/02001005 等);
     * i18n 缺失的码(引擎 6 位族/999999/error_contract 12 族)由构建器回退到
     * mapper 附带的帧内受管三段文案(PassthroughText)——前端仍能看到 Runtime
     * 自身 i18n 的可读文案,而非兜底 02001131"下游依赖访问失败"。
     *
     * @param code runtime 原码(已过 isRecognizedDownstreamCode 信任门或码形纵深校验)
     * @param httpStatus runtime 实际返回的 HTTP 状态码(403/400 等,不强制 502;
     *                   SSE 阶段无状态时由 mapper 传入 500)
     * @return 透传 ErrorDefinition;永不为 empty(调用方在信任后才调本方法)
     */
    public Optional<ErrorDefinition> resolveByCode(String code, int httpStatus) {
        if (code == null || code.isBlank()) {
            return Optional.empty();
        }
        return Optional.of(new ErrorDefinition(code, httpStatus, code));
    }
}
