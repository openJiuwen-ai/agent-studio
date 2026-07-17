/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.storage;

import java.io.InputStream;
import java.util.List;

/**
 * 统一文件存储接口，屏蔽底层存储差异（OBS / 本地文件系统 / 自定义实现）。
 *
 * <h3>路径约定</h3>
 * <p>所有方法的 {@code path} 参数格式为 {@code namespace/objectKey}，
 * 其中 {@code namespace} 由 {@link #getDefaultNamespace()} 或 {@link #getStagingNamespace()} 获取，
 * {@code objectKey} 为业务相对路径（如 {@code ir/agentId/config.json}）。</p>
 *
 * <h3>实现类</h3>
 * <ul>
 *   <li>{@code ObsFileStoreImpl} — OBS，通过 {@code storage.type=OBS} 激活</li>
 *   <li>{@code LocalFileStoreImpl} — 本地文件系统，通过 {@code storage.type=LOCAL} 激活</li>
 *   <li>自定义实现 — 通过 {@code storage.type=CUSTOM} + 外部 JAR 加载</li>
 * </ul>
 *
 * @see LocalFileStoreImpl
 * @see StorageProperties
 */
public interface FileStore {

    /**
     * 写入文本内容到指定路径。
     *
     * @param path    存储路径，格式为 {@code namespace/objectKey}
     * @param content 文本内容（UTF-8）
     * @return 写入后的存储路径
     * @throws RuntimeException 写入失败时抛出
     */
    String write(String path, String content);

    /**
     * 写入二进制流到指定路径。
     *
     * @param path        存储路径，格式为 {@code namespace/objectKey}
     * @param inputStream 输入流
     * @return 写入后的存储路径
     * @throws RuntimeException 写入失败时抛出
     */
    String write(String path, InputStream inputStream);

    /**
     * 写入二进制流到指定路径，并设置过期时间。
     *
     * @param path        存储路径，格式为 {@code namespace/objectKey}
     * @param inputStream 输入流
     * @param expires     过期天数，{@code -1} 表示永不过期
     * @return 写入后的存储路径
     * @throws RuntimeException 写入失败时抛出
     */
    String write(String path, InputStream inputStream, int expires);

    /**
     * 读取指定路径的文本内容。
     *
     * @param path 存储路径，格式为 {@code namespace/objectKey}
     * @return 文本内容（UTF-8）
     * @throws RuntimeException 读取失败时抛出
     */
    String read(String path);

    /**
     * 读取指定路径的二进制流。
     *
     * @param path 存储路径，格式为 {@code namespace/objectKey}
     * @return 输入流，调用方负责关闭
     * @throws RuntimeException 读取失败时抛出
     */
    InputStream readStream(String path);

    /**
     * 删除指定路径的对象。
     *
     * @param path 存储路径，格式为 {@code namespace/objectKey}
     * @return {@code true} 删除成功，{@code false} 删除失败
     */
    boolean delete(String path);

    /**
     * 检查指定路径的对象是否存在。
     *
     * @param path 存储路径，格式为 {@code namespace/objectKey}
     * @return {@code true} 存在，{@code false} 不存在
     */
    boolean exists(String path);

    /**
     * 复制对象。
     *
     * @param sourcePath 源路径，格式为 {@code namespace/objectKey}
     * @param targetPath 目标路径，格式为 {@code namespace/objectKey}
     * @return {@code true} 复制成功，{@code false} 复制失败
     * @throws RuntimeException 复制失败时抛出
     */
    boolean copy(String sourcePath, String targetPath);

    /**
     * 列出指定前缀下的所有对象 key。
     *
     * <p>返回的 key 不含 namespace 前缀，格式为 {@code prefix/xxx}，
     * 与 OBS {@code listObjects} 返回的 {@code objectKey} 格式一致。</p>
     *
     * @param prefix 查询前缀，格式为 {@code namespace/keyPrefix}
     * @return 对象 key 列表，不含 namespace；前缀不存在时返回空列表
     */
    List<String> list(String prefix);

    /**
     * 按前缀批量删除对象。
     *
     * <p>默认实现基于 {@link #list(String)} 逐个调用 {@link #delete(String)}，
     * 子类可覆写为更高效的批量删除。</p>
     *
     * @param prefix 查询前缀，格式为 {@code namespace/keyPrefix}
     * @return {@code true} 全部删除成功，{@code false} 存在删除失败的对象
     */
    default boolean deleteByPrefix(String prefix) {
        List<String> keys = list(prefix);
        if (keys == null || keys.isEmpty()) {
            return true;
        }
        boolean allDeleted = true;
        for (String key : keys) {
            String fullPath = prefix;
            if (!prefix.endsWith("/")) {
                fullPath = prefix + "/";
            }
            if (!delete(fullPath + key)) {
                allDeleted = false;
            }
        }
        return allDeleted;
    }

    /**
     * 获取对象的临时下载 URL。
     *
     * <p>OBS 实现返回带签名的预签名 URL；LOCAL 实现返回
     * {@code {serverUrl}/api/storage/download?path=xxx} 格式的 HTTP 地址。</p>
     *
     * @param path           存储路径，格式为 {@code namespace/objectKey}
     * @param expiresSeconds URL 有效时长（秒）
     * @return 可访问的 URL
     * @throws RuntimeException 生成 URL 失败时抛出
     */
    String getUrl(String path, long expiresSeconds);

    /**
     * 获取对象的元信息。
     *
     * @param path 存储路径，格式为 {@code namespace/objectKey}
     * @return 元信息对象，对象不存在时返回 {@code null}
     */
    FileMeta getMeta(String path);

    /**
     * 列出指定前缀下所有对象和目录的元信息。
     *
     * <p>使用 delimiter 分隔，{@link FileMeta#isDirectory()} 为 {@code true} 表示目录项，
     * 为 {@code false} 表示文件项。目录项的 {@code size} 为 0，{@code lastModified} 为 -1。</p>
     *
     * @param prefix 查询前缀，格式为 {@code namespace/keyPrefix}
     * @return 元信息列表，含文件和目录；前缀不存在时返回空列表
     */
    List<FileMeta> listMetas(String prefix);

    /**
     * 获取默认命名空间（业务数据桶）。
     *
     * <p>OBS 实现返回桶名；LOCAL 实现返回配置的 bucket 名称。</p>
     *
     * @return 默认命名空间名称
     */
    String getDefaultNamespace();

    /**
     * 获取暂存命名空间（临时数据桶）。
     *
     * <p>OBS 实现返回暂存桶名；LOCAL 实现返回配置的 staging-bucket 名称。</p>
     *
     * @return 暂存命名空间名称
     */
    String getStagingNamespace();
}
