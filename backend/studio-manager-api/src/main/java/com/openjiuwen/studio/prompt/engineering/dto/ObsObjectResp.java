/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * ObsObjectResp
 */

@Validated
public class ObsObjectResp implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("obs_object_map")
    @Schema(description = "OBS对象Map", example = "")
    @Valid
    private Map<String, List<ObsResp>> obsObjectMap = null;

    public Map<String, List<ObsResp>> getObsObjectMap() {
        return obsObjectMap;
    }

    public ObsObjectResp setObsObjectMap(Map<String, List<ObsResp>> obsObjectMap) {
        this.obsObjectMap = obsObjectMap;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ObsObjectResp {\n");
        sb.append("    obsObjectMap: ").append(toIndentedString(obsObjectMap)).append("\n");
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
        ObsObjectResp obsObjectResp = (ObsObjectResp) o;
        return Objects.equals(this.obsObjectMap, obsObjectResp.obsObjectMap);
    }

    @Override
    public int hashCode() {
        return Objects.hash(obsObjectMap);
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
