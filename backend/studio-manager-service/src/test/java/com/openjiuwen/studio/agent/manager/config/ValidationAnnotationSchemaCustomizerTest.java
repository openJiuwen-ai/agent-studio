/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.config;

import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import io.swagger.v3.core.converter.AnnotatedType;
import io.swagger.v3.core.converter.ModelConverter;
import io.swagger.v3.core.converter.ModelConverters;
import io.swagger.v3.oas.models.media.Schema;

import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.hibernate.validator.constraints.Length;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

/**
 * J5 定制器（ValidationAnnotationSchemaCustomizer）单测：
 * 在 swagger ModelConverters 真实解析链（openapi31 模式，与项目一致）下验证约束注解到 schema 的映射。
 */
class ValidationAnnotationSchemaCustomizerTest {

    private static final ValidationAnnotationSchemaCustomizer CUSTOMIZER = new ValidationAnnotationSchemaCustomizer();

    @BeforeAll
    static void register() {
        ModelConverters.getInstance(true).addConverter(CUSTOMIZER);
    }

    static class TestDto {
        @Length(min = 1, max = 64)
        private String name;

        @Length()
        private String noLimit;

        @Size(max = 100)
        private List<String> ids;

        @Size(max = 256)
        private String desc;

        @Pattern(regexp = "^[a-z0-9_]+$")
        private String code;

        @Length(max = 64)
        @io.swagger.v3.oas.annotations.media.Schema(maxLength = 100)
        private String schemaPriority;

        private Integer plain;

        public String getName() {
            return name;
        }

        public String getNoLimit() {
            return noLimit;
        }

        public List<String> getIds() {
            return ids;
        }

        public String getDesc() {
            return desc;
        }

        public String getCode() {
            return code;
        }

        public String getSchemaPriority() {
            return schemaPriority;
        }

        public Integer getPlain() {
            return plain;
        }
    }

    private Map<String, Schema> properties() {
        Schema root = ModelConverters.getInstance(true)
            .resolveAsResolvedSchema(new AnnotatedType().type(TestDto.class))
            .schema;
        return root.getProperties();
    }

    @Test
    void lengthMaxMinToSchema() {
        Schema name = properties().get("name");
        assertEquals(64, name.getMaxLength());
        assertEquals(1, name.getMinLength());
    }

    @Test
    void lengthWithoutMaxNotOutput() {
        Schema noLimit = properties().get("noLimit");
        assertNull(noLimit.getMaxLength());
    }

    @Test
    void sizeOnListToMaxItems() {
        Schema ids = properties().get("ids");
        assertEquals(100, ids.getMaxItems());
    }

    @Test
    void sizeOnStringToMaxLength() {
        Schema desc = properties().get("desc");
        assertEquals(256, desc.getMaxLength());
    }

    @Test
    void patternToSchema() {
        Schema code = properties().get("code");
        assertEquals("^[a-z0-9_]+$", code.getPattern());
    }

    @Test
    void explicitSchemaTakesPriority() {
        Schema schemaPriority = properties().get("schemaPriority");
        assertEquals(100, schemaPriority.getMaxLength());
    }

    @Test
    void nonStringTypeUntouched() {
        Schema plain = properties().get("plain");
        assertNull(plain.getMaxLength());
        assertNull(plain.getMinLength());
    }

    @Test
    void noAnnotationsReturnsSchema() {
        Schema result = CUSTOMIZER.resolve(
            new AnnotatedType().type(String.class),
            new io.swagger.v3.core.converter.ModelConverterContextImpl(java.util.Collections.emptyList()),
            java.util.Collections.emptyIterator());
        assertNull(result);
    }
}
