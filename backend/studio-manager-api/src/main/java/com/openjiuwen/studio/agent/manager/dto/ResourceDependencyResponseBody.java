/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * agent依赖资源rsp。
 */
@ApiModel(description = "agent依赖资源rsp。")

@Validated

public class ResourceDependencyResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("dependencies")
    private List<ResourceDependency> dependencies = new ArrayList<ResourceDependency>();

    public List<ResourceDependency> getDependencies() {
        return dependencies;
    }

    public ResourceDependencyResponseBody setDependencies(List<ResourceDependency> dependencies) {
        this.dependencies = dependencies;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ResourceDependencyResponseBody {\n");
        sb.append("    dependencies: ").append(toIndentedString(dependencies)).append("\n");
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
        ResourceDependencyResponseBody resourceDependencyResponseBody = (ResourceDependencyResponseBody) o;
        return Objects.equals(this.dependencies, resourceDependencyResponseBody.dependencies);
    }

    @Override
    public int hashCode() {
        return Objects.hash(dependencies);
    }

    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }
}
