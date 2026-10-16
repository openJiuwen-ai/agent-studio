/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.config;

import java.lang.annotation.Annotation;
import java.util.Iterator;

import org.hibernate.validator.constraints.Length;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import com.fasterxml.jackson.databind.JavaType;

import io.swagger.v3.core.converter.AnnotatedType;
import io.swagger.v3.core.converter.ModelConverter;
import io.swagger.v3.core.converter.ModelConverterContext;
import io.swagger.v3.core.util.Json;
import io.swagger.v3.oas.models.media.Schema;

import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/**
 * ModelConverter：在 schema 解析链上从 Bean Validation 注解补充约束信息。
 * springdoc 2.8.8 已原生解析 jakarta @Size/@Pattern/@NotBlank，此转换器补充 hibernate @Length 的
 * maxLength/minLength。显式 @Schema 已设置的属性优先，不覆盖；无上限（max=Integer.MAX_VALUE）不输出。
 */
@Component
public class ValidationAnnotationSchemaCustomizer implements ModelConverter {

    private static final Logger log = LoggerFactory.getLogger(ValidationAnnotationSchemaCustomizer.class);

    public ValidationAnnotationSchemaCustomizer() {
        log.info("[VASC] ValidationAnnotationSchemaCustomizer initialized");
    }

    @Override
    public Schema resolve(AnnotatedType type, ModelConverterContext context, Iterator<ModelConverter> chain) {
        Schema schema = chain.hasNext() ? chain.next().resolve(type, context, chain) : null;
        if (schema == null) {
            return null;
        }
        Annotation[] annotations = type.getCtxAnnotations();
        if (annotations == null) {
            return schema;
        }
        boolean isString;
        boolean isArray;
        if (type.getType() != null) {
            JavaType javaType = Json.mapper().getTypeFactory().constructType(type.getType());
            isString = javaType.isTypeOrSubTypeOf(String.class);
            isArray = javaType.isContainerType();
        } else {
            isString = "string".equals(schema.getType());
            isArray = "array".equals(schema.getType());
        }
        for (Annotation annotation : annotations) {
            if (annotation instanceof Length) {
                applyLength((Length) annotation, schema, isString);
            } else if (annotation instanceof Size) {
                applySize((Size) annotation, schema, isString, isArray);
            } else if (annotation instanceof Pattern) {
                applyPattern((Pattern) annotation, schema);
            }
        }
        return schema;
    }

    private void applyLength(Length length, Schema schema, boolean isString) {
        if (isString) {
            if (schema.getMaxLength() == null && length.max() < Integer.MAX_VALUE) {
                schema.setMaxLength(length.max());
            }
            if (schema.getMinLength() == null && length.min() > 0) {
                schema.setMinLength(length.min());
            }
        }
    }

    private void applySize(Size size, Schema schema, boolean isString, boolean isArray) {
        if (isArray) {
            if (schema.getMaxItems() == null && size.max() < Integer.MAX_VALUE) {
                schema.setMaxItems(size.max());
            }
            if (schema.getMinItems() == null && size.min() > 0) {
                schema.setMinItems(size.min());
            }
        } else if (isString) {
            if (schema.getMaxLength() == null && size.max() < Integer.MAX_VALUE) {
                schema.setMaxLength(size.max());
            }
            if (schema.getMinLength() == null && size.min() > 0) {
                schema.setMinLength(size.min());
            }
        }
    }

    private void applyPattern(Pattern pattern, Schema schema) {
        if (schema.getPattern() == null && pattern.regexp() != null && !pattern.regexp().isEmpty()) {
            schema.setPattern(pattern.regexp());
        }
    }
}
