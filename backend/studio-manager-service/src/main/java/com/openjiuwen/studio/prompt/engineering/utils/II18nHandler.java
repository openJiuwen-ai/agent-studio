/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.utils;

/**
 * Excel 列名国际化解析接口(瘦身修订 2026-11-04 1C)。
 *
 * <p>背景:原为 easypoi 的 {@code cn.afterturn.easypoi.handler.inter.II18nHandler}
 * (导出时由 easypoi 渲染链回调)。三套 Excel 栈归一到 easyexcel 后,列名在
 * 导出前由调用方预解析(动态表头),本接口保留同签名供既有转换器链
 * (FormConvert/实体转换器)继续使用,行为不变。
 */
public interface II18nHandler {

    /**
     * 按当前请求语种解析 i18n key 对应的列名文案。
     *
     * @param name i18n key(如 excel.export.variable.key)
     * @return 解析后的文案;解析失败时由实现方决定回退形态
     */
    String getLocaleName(String name);
}
