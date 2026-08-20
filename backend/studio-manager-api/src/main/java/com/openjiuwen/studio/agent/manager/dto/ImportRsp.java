/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import com.openjiuwen.studio.agent.common.dto.ImportRes;
import io.swagger.annotations.ApiModel;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 导入插件响应体
 */
@ApiModel(description = "导入插件响应体")

@Validated

public class ImportRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("succeed_len")
    private Integer succeedLen = 0;

    @JsonProperty("count")
    private Integer count = 0;

    @JsonProperty("succeed_ids")
    @Valid
    @Size()
    private List<@Length() String> succeedIds = null;

    @JsonProperty("failed_len")
    private Integer failedLen = 0;

    @JsonProperty("imported_len")
    private Integer importedLen = 0;

    @JsonProperty("updated_len")
    private Integer updatedLen = 0;

    @JsonProperty("skipped_len")
    private Integer skippedLen = 0;

    @JsonProperty("failed_ids")
    @Valid
    @Size()
    private List<@Length() String> failedIds = null;

    @JsonProperty("inner_plugins_msg")
    @Valid
    @Size()
    private List<ExtraMsg> innerPluginsMsg = null;

    @JsonProperty("auth_plugins_msg")
    @Valid
    @Size()
    private List<ExtraMsg> authPluginsMsg = null;

    @JsonProperty("auth_mcps_msg")
    @Valid
    @Size()
    private List<ExtraMsg> authMcpsMsg = null;

    @JsonProperty("import_list")
    @Valid
    @Size()
    private List<ImportRes> importList = null;

    public Integer getSucceedLen() {
        return succeedLen;
    }

    public ImportRsp setSucceedLen(Integer succeedLen) {
        this.succeedLen = succeedLen;
        return this;
    }

    public Integer getCount() {
        return count;
    }

    public ImportRsp setCount(Integer count) {
        this.count = count;
        return this;
    }

    public List<String> getSucceedIds() {
        return succeedIds;
    }

    public ImportRsp setSucceedIds(List<String> succeedIds) {
        this.succeedIds = succeedIds;
        return this;
    }

    public Integer getFailedLen() {
        return failedLen;
    }

    public ImportRsp setFailedLen(Integer failedLen) {
        this.failedLen = failedLen;
        return this;
    }

    public Integer getImportedLen() {
        return importedLen;
    }

    public ImportRsp setImportedLen(Integer importedLen) {
        this.importedLen = importedLen;
        return this;
    }

    public Integer getUpdatedLen() {
        return updatedLen;
    }

    public ImportRsp setUpdatedLen(Integer updatedLen) {
        this.updatedLen = updatedLen;
        return this;
    }

    public Integer getSkippedLen() {
        return skippedLen;
    }

    public ImportRsp setSkippedLen(Integer skippedLen) {
        this.skippedLen = skippedLen;
        return this;
    }

    public List<String> getFailedIds() {
        return failedIds;
    }

    public ImportRsp setFailedIds(List<String> failedIds) {
        this.failedIds = failedIds;
        return this;
    }

    public List<ExtraMsg> getInnerPluginsMsg() {
        return innerPluginsMsg;
    }

    public ImportRsp setInnerPluginsMsg(List<ExtraMsg> innerPluginsMsg) {
        this.innerPluginsMsg = innerPluginsMsg;
        return this;
    }

    public List<ExtraMsg> getAuthPluginsMsg() {
        return authPluginsMsg;
    }

    public ImportRsp setAuthPluginsMsg(List<ExtraMsg> authPluginsMsg) {
        this.authPluginsMsg = authPluginsMsg;
        return this;
    }

    public List<ExtraMsg> getAuthMcpsMsg() {
        return authMcpsMsg;
    }

    public ImportRsp setAuthMcpsMsg(List<ExtraMsg> authMcpsMsg) {
        this.authMcpsMsg = authMcpsMsg;
        return this;
    }

    public List<ImportRes> getImportList() {
        return importList;
    }

    public ImportRsp setImportList(List<ImportRes> importList) {
        this.importList = importList;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ImportRsp {\n");

        sb.append("    succeedLen: ").append(toIndentedString(succeedLen)).append("\n");
        sb.append("    count: ").append(toIndentedString(count)).append("\n");
        sb.append("    succeedIds: ").append(toIndentedString(succeedIds)).append("\n");
        sb.append("    failedLen: ").append(toIndentedString(failedLen)).append("\n");
        sb.append("    importedLen: ").append(toIndentedString(importedLen)).append("\n");
        sb.append("    updatedLen: ").append(toIndentedString(updatedLen)).append("\n");
        sb.append("    skippedLen: ").append(toIndentedString(skippedLen)).append("\n");
        sb.append("    failedIds: ").append(toIndentedString(failedIds)).append("\n");
        sb.append("    innerPluginsMsg: ").append(toIndentedString(innerPluginsMsg)).append("\n");
        sb.append("    authPluginsMsg: ").append(toIndentedString(authPluginsMsg)).append("\n");
        sb.append("    authMcpsMsg: ").append(toIndentedString(authMcpsMsg)).append("\n");
        sb.append("    importList: ").append(toIndentedString(importList)).append("\n");
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
        ImportRsp importRsp = (ImportRsp) o;
        return Objects.equals(this.succeedLen, importRsp.succeedLen) && Objects.equals(this.count, importRsp.count)
            && Objects.equals(this.succeedIds, importRsp.succeedIds) && Objects.equals(this.failedLen,
            importRsp.failedLen) && Objects.equals(this.failedIds, importRsp.failedIds) && Objects.equals(
            this.importedLen, importRsp.importedLen) && Objects.equals(this.updatedLen, importRsp.updatedLen)
            && Objects.equals(this.skippedLen, importRsp.skippedLen) && Objects.equals(this.innerPluginsMsg,
            importRsp.innerPluginsMsg) && Objects.equals(this.authPluginsMsg,
            importRsp.authPluginsMsg) && Objects.equals(this.authMcpsMsg, importRsp.authMcpsMsg) && Objects.equals(
            this.importList, importRsp.importList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(succeedLen, count, succeedIds, failedLen, importedLen, updatedLen, skippedLen, failedIds,
            innerPluginsMsg, authPluginsMsg, authMcpsMsg, importList);
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
