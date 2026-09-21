/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * license状态。
 */
@ApiModel(description = "license状态。")

@Validated

public class LicenseStateResp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("code")
    @Schema(description = "状态码", example = "0")
    @Range(min = 0L, max = 10L)
    private Integer code = null;

    @JsonProperty("message")
    @Schema(description = "消息", example = "license有效")
    private String message = null;

    @JsonProperty("esn")
    @Schema(description = "设备序列号", example = "ESN123456789")
    private String esn = null;

    @JsonProperty("expires_in")
    @Schema(description = "过期时间（秒）", example = "31536000")
    private Long expiresIn = null;

    @JsonProperty("last_update")
    @Schema(description = "最后更新时间戳", example = "1700000000")
    private Long lastUpdate = null;

    @JsonProperty("cpu")
    @Schema(description = "CPU核数", example = "8.0")
    private Float cpu = null;

    @JsonProperty("bbom")
    @Schema(description = "BOM标识", example = "1")
    private Long bbom = null;

    @JsonProperty("expiry_threshold_days")
    @Schema(description = "过期阈值天数", example = "30")
    private Integer expiryThresholdDays = null;

    public Integer getCode() {
        return code;
    }

    public LicenseStateResp setCode(Integer code) {
        this.code = code;
        return this;
    }

    public String getMessage() {
        return message;
    }

    public LicenseStateResp setMessage(String message) {
        this.message = message;
        return this;
    }

    public String getEsn() {
        return esn;
    }

    public LicenseStateResp setEsn(String esn) {
        this.esn = esn;
        return this;
    }

    public Long getExpiresIn() {
        return expiresIn;
    }

    public LicenseStateResp setExpiresIn(Long expiresIn) {
        this.expiresIn = expiresIn;
        return this;
    }

    public Long getLastUpdate() {
        return lastUpdate;
    }

    public LicenseStateResp setLastUpdate(Long lastUpdate) {
        this.lastUpdate = lastUpdate;
        return this;
    }

    public Float getCpu() {
        return cpu;
    }

    public LicenseStateResp setCpu(Float cpu) {
        this.cpu = cpu;
        return this;
    }

    public Long getBbom() {
        return bbom;
    }

    public LicenseStateResp setBbom(Long bbom) {
        this.bbom = bbom;
        return this;
    }

    public Integer getExpiryThresholdDays() {
        return expiryThresholdDays;
    }

    public LicenseStateResp setExpiryThresholdDays(Integer expiryThresholdDays) {
        this.expiryThresholdDays = expiryThresholdDays;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class LicenseStateResp {\n");

        sb.append("    code: ").append(toIndentedString(code)).append("\n");
        sb.append("    message: ").append(toIndentedString(message)).append("\n");
        sb.append("    esn: ").append(toIndentedString(esn)).append("\n");
        sb.append("    expiresIn: ").append(toIndentedString(expiresIn)).append("\n");
        sb.append("    lastUpdate: ").append(toIndentedString(lastUpdate)).append("\n");
        sb.append("    cpu: ").append(toIndentedString(cpu)).append("\n");
        sb.append("    bbom: ").append(toIndentedString(bbom)).append("\n");
        sb.append("    expiryThresholdDays: ").append(toIndentedString(expiryThresholdDays)).append("\n");
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
        LicenseStateResp licenseStateResp = (LicenseStateResp) o;
        return Objects.equals(this.code, licenseStateResp.code) && Objects.equals(this.message,
            licenseStateResp.message) && Objects.equals(this.esn, licenseStateResp.esn) && Objects.equals(
            this.expiresIn, licenseStateResp.expiresIn) && Objects.equals(this.lastUpdate, licenseStateResp.lastUpdate)
            && Objects.equals(this.cpu, licenseStateResp.cpu) && Objects.equals(this.bbom, licenseStateResp.bbom)
            && Objects.equals(this.expiryThresholdDays, licenseStateResp.expiryThresholdDays);
    }

    @Override
    public int hashCode() {
        return Objects.hash(code, message, esn, expiresIn, lastUpdate, cpu, bbom, expiryThresholdDays);
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
