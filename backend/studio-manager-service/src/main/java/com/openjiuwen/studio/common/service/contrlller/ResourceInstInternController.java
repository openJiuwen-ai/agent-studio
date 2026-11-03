/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.common.service.contrlller;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.ValidateUtils;
import com.openjiuwen.studio.common.service.model.skuinst.LicenseInst;
import com.openjiuwen.studio.common.service.model.skuinst.LicenseReportReq;
import com.openjiuwen.studio.common.service.model.skuinst.ResourceInst;
import com.openjiuwen.studio.common.service.service.ResourceInstService;

import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 资源订购实例
 */
@Slf4j
@RestController
public class ResourceInstInternController implements ResourceInstInternApi {

    @Autowired
    private ResourceInstService resourceInstService;

    @Override
    public ResponseEntity<List<ResourceInst>> queryResourceInsts(String token, String domainId) {
        try {
            log.info("AgentBuilder queryResourceInsts start");
            if (ValidateUtils.isNotEmptyString(token)) {
                domainId = RequestContextUtils.getRequestUserDomainId();
                log.info("AgentBuilder query resource insts, operation log userId: {}",
                    RequestContextUtils.getRequestUserId());
            }
            List<ResourceInst> resourceInsts = resourceInstService.queryResourceInsts(domainId, true);
            log.info("AgentBuilder queryResourceInsts end");
            return ResponseEntity.ok(resourceInsts);
        } catch (AgentStudioException e) {
            throw e;
        } catch (Exception e) {
            log.error("AgentBuilder query tenant info failed", e);
            throw new AgentStudioException(StudioError.UNEXPECTED_ERROR);
        }
    }

    @Override
    public ResponseEntity<List<LicenseInst>> queryLicense(String resId, String attrCode, String skuCode, String token,
        String domainId) {
        try {
            log.info("AgentBuilder query license start");
            if (ValidateUtils.isNotEmptyString(token)) {
                domainId = RequestContextUtils.getRequestUserDomainId();
                log.info("AgentBuilder query license, operation log userId: {}", RequestContextUtils.getRequestUserId());
            }
            List<LicenseInst> licenseInsts = resourceInstService.queryLicense(resId, attrCode, skuCode, domainId);
            log.info("AgentBuilder query license end");
            return ResponseEntity.ok(licenseInsts);
        } catch (AgentStudioException e) {
            throw e;
        } catch (Exception e) {
            log.error("AgentBuilder query tenant info failed", e);
            throw new AgentStudioException(StudioError.UNEXPECTED_ERROR);
        }
    }

    @Override
    public ResponseEntity<String> report(LicenseReportReq req, String token, String domainId) {
        try {
            log.info("AgentBuilder report license start");
            if (ValidateUtils.isNotEmptyString(token)) {
                domainId = RequestContextUtils.getRequestUserDomainId();
                log.info("AgentBuilder report license, operation log userId: {}", RequestContextUtils.getRequestUserId());
            }
            resourceInstService.reportLicense(req, domainId);
            log.info("AgentBuilder report license end");
            return ResponseEntity.ok("Success.");
        } catch (AgentStudioException e) {
            throw e;
        } catch (Exception e) {
            log.error("AgentBuilder query tenant info failed", e);
            throw new AgentStudioException(StudioError.UNEXPECTED_ERROR);
        }
    }
}
