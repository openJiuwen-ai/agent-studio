/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.utils;

import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.CN_LANGUAGE;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.COUNTRY_CN;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.COUNTRY_US;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.LANGUAGE_EN;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.LANGUAGE_ZH;

import com.openjiuwen.studio.prompt.engineering.utils.II18nHandler;

import org.apache.commons.lang3.StringUtils;
import org.springframework.context.MessageSource;

import java.util.Locale;


/**
 * ExcelI18nHandler
 *
 */
public class ExcelI18nHandler implements II18nHandler {

    private final MessageSource messageSource;

    public ExcelI18nHandler(MessageSource messageSource) {
        this.messageSource = messageSource;
    }

    @Override
    public String getLocaleName(String name) {
        if (StringUtils.isBlank(name)) {
            return name;
        }
        Locale locale = CN_LANGUAGE.equals(HttpUtil.getLanguage()) ? new Locale(LANGUAGE_ZH, COUNTRY_CN,
            StringUtils.EMPTY) : new Locale(LANGUAGE_EN, COUNTRY_US, StringUtils.EMPTY);
        return messageSource.getMessage(name, null, locale);
    }
}
