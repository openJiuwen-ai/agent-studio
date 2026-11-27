/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.contract;

import java.util.Map;
import java.util.Set;

/**
 * COM-04 §5.2 修订二期（2026-11-02 用户裁定）：Manager 自有错误码的
 * 依赖组件标签分类——manager 自身直接访问的下游依赖（OBS / SQL 数据库）
 * 失败时，统一族格式标注"是哪个组件"。
 * <p>
 * 仅按码族精确匹配（不按文案猜测）：OBS 访问链（MgObsService 等包装的
 * 02001004/14/23/24、02001113/14、02401043、02701004）→ {@code obs}；
 * SQL 执行链（SQL_EXECUTE_FAILED 02001042）→ {@code mysql}；Redis 访问链
 * （02001040/02001051）→ {@code redis}。调测链路 builder 掉线不走本表
 * ——与 runtime 掉线同构，经 DownstreamErrorMapper 兜底 02001131+标签
 * （2026-11-02 用户裁定一致性）。
 * Runtime/Builder 下游身份的标签由 {@code DownstreamErrorMapper} 判定（含
 * Runtime 引擎 OBS 码段 1005xx），与本类互补，不重复登记。
 * 未命中返回 null（非依赖类错误保持 i18n 三键原格式）。
 */
final class DependencyComponentLabels {

    private static final Map<String, String> LABELS = buildLabels();

    private DependencyComponentLabels() {
    }

    private static Map<String, String> buildLabels() {
        Map<String, String> labels = new java.util.HashMap<>();
        // Manager 侧 OBS 依赖码族（直接访问 OBS 的失败包装）
        Set.of("openjiuwen.02001004", "openjiuwen.02001014", "openjiuwen.02001023",
               "openjiuwen.02001024", "openjiuwen.02001113", "openjiuwen.02001114",
               "openjiuwen.02401043", "openjiuwen.02701004")
            .forEach(code -> labels.put(code, "obs"));
        // Manager 侧 SQL/数据库依赖码族
        labels.put("openjiuwen.02001042", "mysql");
        // Manager 侧 Redis 依赖码族（访问失败 + Redisson bucket）
        labels.put("openjiuwen.02001051", "redis");
        labels.put("openjiuwen.02001040", "redis");
        return java.util.Collections.unmodifiableMap(labels);
    }

    /** Manager 自有错误码 → 依赖组件标签；未命中返回 null。 */
    static String forManagerErrorCode(String errorCode) {
        if (errorCode == null || errorCode.isBlank()) {
            return null;
        }
        return LABELS.get(errorCode);
    }
}
