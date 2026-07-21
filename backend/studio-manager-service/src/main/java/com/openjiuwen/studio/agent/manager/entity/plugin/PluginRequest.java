package com.openjiuwen.studio.agent.manager.entity.plugin;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.Map;

@Data
public class PluginRequest {

    private String url;

    private String method;

    private Map<String, String> headers;

    private Map<String, String> params;

    private Map<String, Object> data;

    private Map<String, Object> json;

    @JsonProperty("form_data")
    private Map<String, Object> formParams;

    private Integer timeout = 60;

}
