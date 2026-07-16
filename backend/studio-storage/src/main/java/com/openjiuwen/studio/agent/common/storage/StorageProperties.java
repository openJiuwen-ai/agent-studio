/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.storage;

import lombok.Data;

import org.springframework.boot.context.properties.ConfigurationProperties;

@Data
@ConfigurationProperties(prefix = "storage")
public class StorageProperties {

    private Type type = Type.OBS;

    private int expires = 7;

    private long bucketStorageLimit = 100;

    private String customClass;

    private String customClasspath;

    private Obs obs = new Obs();

    private Local local = new Local();

    public enum Type {
        OBS, LOCAL, CUSTOM
    }

    @Data
    public static class Obs {
        private String url;
        private String ak;
        private String sk;
        private String bucket;
        private String stagingBucket;
        private boolean opensource = true;
        private String pathStyle = "path";
        private boolean autoCreateBucket = true;
    }

    @Data
    public static class Local {
        private String basePath;
        private String bucket;
        private String stagingBucket;
        private String serverUrl;
    }
}
