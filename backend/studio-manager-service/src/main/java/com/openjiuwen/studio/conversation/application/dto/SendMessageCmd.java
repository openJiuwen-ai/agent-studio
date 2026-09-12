/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.conversation.application.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

/**
 * 发送消息命令（多轮对话入口，触发一轮运行）
 */
@Data
public class SendMessageCmd {
    /**
     * 用户输入
     */
    @JsonProperty("query")
    private String query;

    /**
     * 执行目标类型：SUPERVISOR（默认团队）或 APP（用户配置的智能体应用）。
     */
    @JsonProperty("select_type")
    private String selectType = "SUPERVISOR";

    /**
     * 用户配置的单/多智能体应用 ID，仅 APP 路径使用。
     */
    @JsonProperty("app_id")
    private String appId;

    /**
     * 模型部署id（=t_model_service.ID），Supervisor 路径使用。
     */
    @JsonProperty("model_deployment_id")
    private String modelDeploymentId;

    /**
     * 浏览器请求的本轮推荐技能 ID，运行前必须由服务端目录重新校验。
     */
    @JsonProperty("recommended_skill_ids")
    private List<String> recommendedSkillIds = new ArrayList<>();

    /**
     * 本轮上传文件引用，元素包含可访问 URL 和原始文件名。
     */
    @JsonProperty("file_ids")
    private List<java.util.Map<String, String>> fileIds = new ArrayList<>();

    public void setFileIds(List<java.util.Map<String, String>> fileIds) {
        this.fileIds = fileIds == null ? new ArrayList<>() : new ArrayList<>(fileIds);
    }

    public void setRecommendedSkillIds(List<String> recommendedSkillIds) {
        this.recommendedSkillIds = recommendedSkillIds == null ? new ArrayList<>() : new ArrayList<>(recommendedSkillIds);
    }
}
