/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.utils;

import org.apache.commons.lang3.StringUtils;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * 敏感文本脱敏工具：把敏感值（如加密环境变量明文）在目标文本中的出现替换为固定掩码。
 * 覆盖明文、JSON 转义形态与 URL 百分号编码形态（+ 与 %20、大写与小写十六进制），
 * 供调测回显脱敏与日志脱敏共用，避免明文经回显或日志泄漏。
 */
public final class SensitiveTextMasker {

    /** 固定脱敏掩码（六位星号），与前端回填值及环境变量查询接口的脱敏口径一致。 */
    public static final String MASK = "******";

    /** JSON 数字字面量，用于识别「裸数字」敏感值，避免在 JSON 文本中把数值字面量替换成非法 JSON。 */
    private static final Pattern JSON_NUMBER_PATTERN = Pattern.compile("-?\\d+(\\.\\d+)?([eE][+-]?\\d+)?");

    /** 百分号编码中的十六进制片段，用于生成小写十六进制变体，覆盖部分编码器的输出格式。 */
    private static final Pattern PERCENT_HEX_PATTERN = Pattern.compile("%([0-9A-F]{2})");

    private SensitiveTextMasker() {
    }

    /**
     * 将文本中出现的敏感值替换为固定掩码。
     *
     * @param text 目标文本
     * @param secretValues 敏感值集合
     * @param jsonContext 文本是否为 JSON：为 true 时数字/布尔字面量不能裸替换成掩码（会破坏 JSON 合法性），
     *                    字符串字面量整体替换，裸字面量替换为「带引号的掩码」
     * @return 脱敏后的文本；文本为空或敏感值为空时原样返回
     */
    public static String mask(String text, Collection<String> secretValues, boolean jsonContext) {
        if (StringUtils.isEmpty(text) || secretValues == null || secretValues.isEmpty()) {
            return text;
        }
        // 先长后短，避免短值先命中后导致长值被截断无法匹配
        List<String> ordered = new ArrayList<>(secretValues);
        ordered.sort((left, right) -> Integer.compare(right.length(), left.length()));
        String masked = text;
        for (String secretValue : ordered) {
            if (StringUtils.isEmpty(secretValue)) {
                continue;
            }
            for (String form : collectSecretForms(secretValue)) {
                masked = maskStandaloneToken(masked, form, jsonContext);
            }
        }
        return masked;
    }

    /**
     * 收集敏感值在文本中可能出现的编码形态：原始明文、JSON 转义形态、URL 编码形态（+ 与 %20，大写与小写十六进制）。
     */
    private static Set<String> collectSecretForms(String secretValue) {
        Set<String> forms = new LinkedHashSet<>();
        forms.add(secretValue);
        forms.add(toJsonEscaped(secretValue));
        String urlEncoded = URLEncoder.encode(secretValue, StandardCharsets.UTF_8);
        String urlEncodedSpace = urlEncoded.replace("+", "%20");
        forms.add(urlEncoded);
        forms.add(urlEncodedSpace);
        forms.add(toLowerPercentHex(urlEncoded));
        forms.add(toLowerPercentHex(urlEncodedSpace));
        forms.remove("");
        return forms;
    }

    /**
     * 将百分号编码中的十六进制转为小写，覆盖输出小写十六进制的编码器。
     */
    private static String toLowerPercentHex(String encoded) {
        return PERCENT_HEX_PATTERN.matcher(encoded).replaceAll(match -> "%" + match.group(1).toLowerCase());
    }

    /**
     * 按 token 边界替换敏感值：仅替换两侧均非字母/数字/下划线的独立出现，避免把夹在长 token 内的相同字符整体破坏。
     * jsonContext 为 true 且敏感值为数字/布尔字面量时，交由 {@link #maskJsonScalar} 处理，保证替换后仍是合法 JSON。
     */
    private static String maskStandaloneToken(String text, String secretValue, boolean jsonContext) {
        if (StringUtils.isEmpty(secretValue)) {
            return text;
        }
        if (jsonContext && isJsonScalarLiteral(secretValue)) {
            return maskJsonScalar(text, secretValue);
        }
        Pattern pattern = Pattern.compile("(?<![A-Za-z0-9_])" + Pattern.quote(secretValue) + "(?![A-Za-z0-9_])");
        return pattern.matcher(text).replaceAll(MASK);
    }

    /**
     * 在 JSON 文本中替换数字/布尔形态的敏感值，替换后仍是合法 JSON，覆盖两种位置：
     * - 位于 JSON 字符串内部（如 {@code {"msg":"count 123456 items"}}）：替换为「裸掩码」，字符串内容仍合法；
     * - 位于字符串之外（schema 类型 integer/number/boolean 归一后的裸数字/布尔字面量）：替换为「带引号的掩码」。
     * 两种情况都覆盖，避免数字/布尔型密钥经回显字符串或裸字面量泄露明文。
     */
    private static String maskJsonScalar(String text, String secretValue) {
        StringBuilder result = new StringBuilder(text.length());
        int secretLength = secretValue.length();
        boolean inString = false;
        boolean escaped = false;
        int index = 0;
        while (index < text.length()) {
            char current = text.charAt(index);
            if (inString) {
                // 字符串内部命中：替换为裸掩码（不追加引号），输出仍是合法 JSON
                if (!escaped && text.regionMatches(index, secretValue, 0, secretLength)
                    && isJsonScalarBoundary(text, index - 1) && isJsonScalarBoundary(text, index + secretLength)) {
                    result.append(MASK);
                    index += secretLength;
                    continue;
                }
                result.append(current);
                if (escaped) {
                    escaped = false;
                } else if (current == '\\') {
                    escaped = true;
                } else if (current == '"') {
                    inString = false;
                }
                index++;
                continue;
            }
            if (current == '"') {
                inString = true;
                result.append(current);
                index++;
                continue;
            }
            // 字符串外命中（裸数字/布尔字面量）：替换为带引号掩码。
            // 额外排除紧邻正负号的情况，避免把 -123456 这类带符号数字拆成 -"******" 破坏 JSON 合法性
            boolean afterSign = index > 0 && (text.charAt(index - 1) == '-' || text.charAt(index - 1) == '+');
            if (!afterSign && text.regionMatches(index, secretValue, 0, secretLength)
                && isJsonScalarBoundary(text, index - 1) && isJsonScalarBoundary(text, index + secretLength)) {
                result.append('"').append(MASK).append('"');
                index += secretLength;
                continue;
            }
            result.append(current);
            index++;
        }
        return result.toString();
    }

    /**
     * 判断 JSON 文本中指定位置是否为 token 边界（越界，或非字母/数字/下划线/点）。
     */
    private static boolean isJsonScalarBoundary(String text, int index) {
        if (index < 0 || index >= text.length()) {
            return true;
        }
        char c = text.charAt(index);
        return !(Character.isLetterOrDigit(c) || c == '_' || c == '.');
    }

    /**
     * 判断值是否为 JSON 数字/布尔字面量（不含引号形式），此类值在 JSON 中裸替换会破坏 JSON 合法性。
     */
    private static boolean isJsonScalarLiteral(String value) {
        return "true".equals(value) || "false".equals(value) || JSON_NUMBER_PATTERN.matcher(value).matches();
    }

    /**
     * 取敏感值在 JSON 字符串中的转义形态（不含首尾引号），用于覆盖文本里的转义字面量。
     * 手动转义常见字符，避免引入对 JSON 库的依赖。
     */
    private static String toJsonEscaped(String value) {
        StringBuilder builder = new StringBuilder(value.length());
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '"':
                    builder.append("\\\"");
                    break;
                case '\\':
                    builder.append("\\\\");
                    break;
                case '\b':
                    builder.append("\\b");
                    break;
                case '\f':
                    builder.append("\\f");
                    break;
                case '\n':
                    builder.append("\\n");
                    break;
                case '\r':
                    builder.append("\\r");
                    break;
                case '\t':
                    builder.append("\\t");
                    break;
                default:
                    if (c < 0x20) {
                        builder.append(String.format("\\u%04x", (int) c));
                    } else {
                        builder.append(c);
                    }
            }
        }
        return builder.toString();
    }
}
