/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.datasource;

/**
 * 数据库密码获取接口，支持外部自定义实现。
 *
 * <p>默认实现使用 CryptoUtils 解密；
 * 自定义实现通过外部 JAR 加载，可对接 KMS、Vault 等外部凭据管理服务。</p>
 */
public interface DataSourcePasswordProvider {

    /**
     * 获取数据库密码（明文）。
     *
     * @param rawPassword 配置文件中的原始密码（可能为加密密文，也可能为明文）
     * @return 解密后的明文密码
     */
    String getPassword(String rawPassword);
}
