/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.LanguageUtils;

import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.context.MessageSource;
import org.springframework.stereotype.Service;

import java.util.Locale;
import java.util.Map;

@Slf4j
@Service
public class JiuwenRuntimeI18nService {
    private static final String TOKEN_USE_UP_ERROR_CODE = "openjiuwen.02501051";

    private static final String SYSTEM_ERROR_CODE = "999999";

    @Autowired
    @Qualifier("jiuwenErrorMessageResource")
    private MessageSource messageSource;
    @Autowired
    private I18nUtil i18nUtil;

    /**
     * 异常事件封装
     *
     * @param eventData 九问error事件
     * @return 封装后error事件
     */
    public Map<String, Object> createRuntimeErrorEvent(Map<String, Object> eventData) {
        String message = eventData.get("message") == null ? "" : eventData.get("message").toString();
        if (message.contains(TOKEN_USE_UP_ERROR_CODE)) {
            eventData.put("error_code", TOKEN_USE_UP_ERROR_CODE);
            eventData.put("error_msg", i18nUtil.getMessage(TOKEN_USE_UP_ERROR_CODE));
            eventData.put("error_suggestion", i18nUtil.getMessage(TOKEN_USE_UP_ERROR_CODE + ".suggestion"));
            eventData.put("error_reason", i18nUtil.getMessage(TOKEN_USE_UP_ERROR_CODE + ".reason"));
        } else {
            String errorCode = eventData.get("code") == null ? SYSTEM_ERROR_CODE : eventData.get("code").toString();

            Locale locale = LanguageUtils.getLanguageLocale();
            eventData.putIfAbsent("error_code", "openjiuwen." + errorCode);
            eventData.put("error_msg", safeGetMessage(errorCode, locale));
            eventData.put("error_suggestion", safeGetMessage(errorCode + ".suggestion", locale));
            eventData.put("error_reason", safeGetMessage(errorCode + ".reason", locale));
        }

        return eventData;
    }

    private String safeGetMessage(String key, Locale locale) {
        try {
            return messageSource.getMessage(key, new Object[] {0}, locale);
        } catch (Exception e) {
            return "";
        }
    }
}
