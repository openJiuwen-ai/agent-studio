/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Map;
import java.util.Objects;

/**
 * BaseMeta
 */

@Validated

public class BaseMeta implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("openapi_snippet")
    @Schema(description = "OpenAPI片段", example = "{\"path\":\"/api/test\"}")
    @Valid
    private Object openapiSnippet = null;

    @JsonProperty("props")
    @Schema(description = "属性", example = "{\"key\":\"value\"}")
    @Valid
    private Object props = null;

    @JsonProperty("props_present")
    @Schema(description = "已存在的属性集合", example = "{\"key\":\"value\"}")
    @Valid
    @Size()
    private Map<String, Object> propsPresent = null;

    @JsonProperty("json_example")
    @Schema(description = "JSON示例", example = "{\"key\":\"value\"}")
    @Valid
    private Object jsonExample = null;

    @JsonProperty("xml_example")
    @Schema(description = "XML示例", example = "<root></root>")
    private String xmlExample = null;

    @JsonProperty("definition")
    @Schema(description = "定义", example = "{\"type\":\"object\"}")
    @Valid
    private Object definition = null;

    public Object getOpenapiSnippet() {
        return openapiSnippet;
    }

    public BaseMeta setOpenapiSnippet(Object openapiSnippet) {
        this.openapiSnippet = openapiSnippet;
        return this;
    }

    public Object getProps() {
        return props;
    }

    public BaseMeta setProps(Object props) {
        this.props = props;
        return this;
    }

    public Map<String, Object> getPropsPresent() {
        return propsPresent;
    }

    public BaseMeta setPropsPresent(Map<String, Object> propsPresent) {
        this.propsPresent = propsPresent;
        return this;
    }

    public Object getJsonExample() {
        return jsonExample;
    }

    public BaseMeta setJsonExample(Object jsonExample) {
        this.jsonExample = jsonExample;
        return this;
    }

    public String getXmlExample() {
        return xmlExample;
    }

    public BaseMeta setXmlExample(String xmlExample) {
        this.xmlExample = xmlExample;
        return this;
    }

    public Object getDefinition() {
        return definition;
    }

    public BaseMeta setDefinition(Object definition) {
        this.definition = definition;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class BaseMeta {\n");

        sb.append("    openapiSnippet: ").append(toIndentedString(openapiSnippet)).append("\n");
        sb.append("    props: ").append(toIndentedString(props)).append("\n");
        sb.append("    propsPresent: ").append(toIndentedString(propsPresent)).append("\n");
        sb.append("    jsonExample: ").append(toIndentedString(jsonExample)).append("\n");
        sb.append("    xmlExample: ").append(toIndentedString(xmlExample)).append("\n");
        sb.append("    definition: ").append(toIndentedString(definition)).append("\n");
        sb.append("}");
        return sb.toString();
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (o == null || getClass() != o.getClass()) {
            return false;
        }
        BaseMeta baseMeta = (BaseMeta) o;
        return Objects.equals(this.openapiSnippet, baseMeta.openapiSnippet) && Objects.equals(this.props,
            baseMeta.props) && Objects.equals(this.propsPresent, baseMeta.propsPresent) && Objects.equals(
            this.jsonExample, baseMeta.jsonExample) && Objects.equals(this.xmlExample, baseMeta.xmlExample)
            && Objects.equals(this.definition, baseMeta.definition);
    }

    @Override
    public int hashCode() {
        return Objects.hash(openapiSnippet, props, propsPresent, jsonExample, xmlExample, definition);
    }

    /**
     * Convert the given object to string with each line indented by 4 spaces
     * (except the first line).
     */
    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }
}
