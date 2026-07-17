/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.model;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import lombok.experimental.Accessors;

import org.apache.commons.lang3.StringUtils;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Getter
@Setter
@NoArgsConstructor
@Accessors(chain = true)
public class ModelApiLog {
    private String id;

    private String requestId;

    private String api;

    private Boolean stream;

    private String modelName = "Unknown";

    private String modelId = "Unknown";

    private String provider = "Unknown";

    private String serviceKey = "Unknown";

    private int apiStatus;

    private long duration;

    private String promptTokens;

    private String completionTokens;

    private String totalTokens;

    private String threadId;

    private String domainId;

    private String projectId;

    private String workspaceId;

    private String userName;

    private String userId;

    private long createTime;

    private long firstToken;

    private String authId;

    private long startTime;

    private int streamEvents;

    private boolean requestVerify;

    private boolean responseVerify;

    private boolean isFreeModel;

    private boolean isInvokeByAsset = false;

    private boolean canUseAssetFreeTrial = false;

    private int freeTokens;

    private String ipAddress;

    private String input;

    private String output;

    private String reason;

    private String status;

    private String ownerProjectId;

    private String ownerDomainId;

    private Map<String, StringBuilder> outputMap = new HashMap<>();

    public String getOutput() {
        List<String> outputList = new ArrayList<>();
        if (StringUtils.isNotEmpty(output)) {
            outputList.add(output);
        }

        for (StringBuilder builder : outputMap.values()) {
            outputList.add(builder.toString());
        }

        return String.join(System.lineSeparator(), outputList);
    }
}
