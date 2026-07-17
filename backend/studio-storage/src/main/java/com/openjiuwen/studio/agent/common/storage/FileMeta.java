/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.storage;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 文件元信息，用于 {@link FileStore#listMetas(String)} 和 {@link FileStore#getMeta(String)} 返回结果。
 *
 * @see FileStore#listMetas(String)
 * @see FileStore#getMeta(String)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class FileMeta {

    /**
     * 对象名称。
     *
     * <p>文件项为完整 objectKey（如 {@code ir/agentId/config.json}）；
     * 目录项为 commonPrefix（如 {@code ir/agentId/}，以 {@code /} 结尾）。</p>
     */
    private String name;

    /**
     * 对象大小（字节）。
     *
     * <p>文件项为实际大小；目录项为 0；元信息不可用时为 -1。</p>
     */
    private long size;

    /**
     * 最后修改时间（毫秒时间戳）。
     *
     * <p>文件项为实际修改时间；目录项为 -1；元信息不可用时为 -1。</p>
     */
    private long lastModified;

    /**
     * 是否为目录。
     *
     * <p>{@code true} 表示目录项（对应 OBS 的 commonPrefix）；
     * {@code false} 表示文件项。</p>
     */
    private boolean directory;
}
