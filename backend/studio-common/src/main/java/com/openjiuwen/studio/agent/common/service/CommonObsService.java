/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.service;

/**
 * OBS公共服务，后续Manager和Runtime的OBSService要归一
 *
 */
public interface CommonObsService {

    /**
     * 上传OBS文件
     *
     * @param objectKey 文件路径
     * @param content 文件内容
     */
    void putObject(String objectKey, String content);

    /**
     * 删除OBS文件
     *
     * @param objectKey 文件路径
     */
    void deleteObject(String objectKey);

    /**
     * 下载OBS文件
     *
     * @param objectKey 文件路径
     * @return 文件内容
     */
    String getObject(String objectKey);

    /**
     * 下载OBS文件，对象不存在时返回 {@code null}（而非抛出）。
     *
     * <p>用于"对象不存在=业务语义"的调用方（如发布元数据读取：未发布资源元数据对象在 OBS 不存在，
     * 404 应语义化为 null 而非 OBS 服务故障）。其余下载场景用 {@link #getObject(String)}，
     * 让对象不存在与 OBS 故障统一抛出，避免调用方解引用 null 导致 NPE。</p>
     *
     * <p>默认实现委托 {@link #getObject(String)}；OBS 实现（MgObsService）覆盖此方法，
     * 对 404 返回 null、对 5xx 等真实故障抛出。</p>
     *
     * @param objectKey 文件路径
     * @return 文件内容；对象不存在时返回 {@code null}（仅 OBS 实现区分）
     */
    default String getObjectOrNull(String objectKey) {
        return getObject(objectKey);
    }
}
