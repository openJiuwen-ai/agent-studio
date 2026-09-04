/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.conversation.domain.model.valueobject;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 文件引用值对象
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class FileRef {
    /**
     * OBS key/url
     */
    private String key;

    /**
     * 上传时的原始文件名
     */
    private String fileName;

    public FileRef(String key) {
        this(key, null);
    }

}
