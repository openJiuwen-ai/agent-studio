/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 提示词迭代结果信息
 */
@ApiModel(description = "提示词迭代结果信息")

@Validated
public class PromptIterationResultVo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    @Pattern(regexp = "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
    private String id = null;

    @JsonProperty("taskId")
    @Schema(description = "任务ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890", required = true)
    @Pattern(regexp = "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
    @NotBlank
    private String taskId = null;

    @JsonProperty("iterNum")
    @Schema(description = "迭代序号", example = "1", required = true)
    @NotNull
    @Range(min = 0L, max = 100L)
    private Integer iterNum = null;

    @JsonProperty("oriPt")
    @Schema(description = "oriPt", example = "示例文本")
    private String oriPt = null;

    @JsonProperty("resPt")
    @Schema(description = "结果Pt", example = "示例文本")
    private String resPt = null;

    @JsonProperty("resAcc")
    @Schema(description = "结果Acc", example = "示例文本")
    private String resAcc = null;

    @JsonProperty("createdTime")
    @Schema(description = "创建时间", example = "1700000000000")
    private Long createdTime = null;

    public String getId() {
        return id;
    }

    public PromptIterationResultVo setId(String id) {
        this.id = id;
        return this;
    }

    public String getTaskId() {
        return taskId;
    }

    public PromptIterationResultVo setTaskId(String taskId) {
        this.taskId = taskId;
        return this;
    }

    public Integer getIterNum() {
        return iterNum;
    }

    public PromptIterationResultVo setIterNum(Integer iterNum) {
        this.iterNum = iterNum;
        return this;
    }

    public String getOriPt() {
        return oriPt;
    }

    public PromptIterationResultVo setOriPt(String oriPt) {
        this.oriPt = oriPt;
        return this;
    }

    public String getResPt() {
        return resPt;
    }

    public PromptIterationResultVo setResPt(String resPt) {
        this.resPt = resPt;
        return this;
    }

    public String getResAcc() {
        return resAcc;
    }

    public PromptIterationResultVo setResAcc(String resAcc) {
        this.resAcc = resAcc;
        return this;
    }

    public Long getCreatedTime() {
        return createdTime;
    }

    public PromptIterationResultVo setCreatedTime(Long createdTime) {
        this.createdTime = createdTime;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PromptIterationResultVo {\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    taskId: ").append(toIndentedString(taskId)).append("\n");
        sb.append("    iterNum: ").append(toIndentedString(iterNum)).append("\n");
        sb.append("    oriPt: ").append(toIndentedString(oriPt)).append("\n");
        sb.append("    resPt: ").append(toIndentedString(resPt)).append("\n");
        sb.append("    resAcc: ").append(toIndentedString(resAcc)).append("\n");
        sb.append("    createdTime: ").append(toIndentedString(createdTime)).append("\n");
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
        PromptIterationResultVo promptIterationResultVo = (PromptIterationResultVo) o;
        return Objects.equals(this.id, promptIterationResultVo.id) && Objects.equals(this.taskId,
            promptIterationResultVo.taskId) && Objects.equals(this.iterNum, promptIterationResultVo.iterNum)
            && Objects.equals(this.oriPt, promptIterationResultVo.oriPt) && Objects.equals(this.resPt,
            promptIterationResultVo.resPt) && Objects.equals(this.resAcc, promptIterationResultVo.resAcc)
            && Objects.equals(this.createdTime, promptIterationResultVo.createdTime);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, taskId, iterNum, oriPt, resPt, resAcc, createdTime);
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
