package com.openjiuwen.studio.agent.manager.entity;

import lombok.Data;

@Data
public class SpaciousInfo {

    private String originalResourceId;

    private String targetResourceId;

    private String latestVersionId;

    private String latestVersionName;
}
