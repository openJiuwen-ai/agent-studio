/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.service.v2;

import static org.hibernate.validator.internal.util.Contracts.assertNotNull;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONException;
import com.alibaba.fastjson.TypeReference;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.prompt.engineering.dto.CreatePromptResp;
import com.openjiuwen.studio.prompt.engineering.dto.GetPromptListsQo;
import com.openjiuwen.studio.prompt.engineering.dto.PePromptNewListVo;
import com.openjiuwen.studio.prompt.engineering.dto.PePromptTemplateNewVo;
import com.openjiuwen.studio.prompt.engineering.entity.Industry;
import com.openjiuwen.studio.prompt.engineering.entity.PePromptTemplate;
import com.openjiuwen.studio.prompt.engineering.entity.v2.PromptVar;
import com.openjiuwen.studio.prompt.engineering.enums.Source;
import com.openjiuwen.studio.prompt.engineering.enums.v2.PtTypeEnum;
import com.openjiuwen.studio.prompt.engineering.mapper.PePromptTemplateMapper;
import com.openjiuwen.studio.prompt.engineering.service.IPromptApiService;
import com.openjiuwen.studio.prompt.engineering.service.PromptTransactionService;

import io.netty.util.internal.StringUtil;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.Strings;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.sql.Timestamp;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@Slf4j
public class PromptApiServiceImpl implements IPromptApiService {

    @Value("${admin.domain.name}")
    private String adminName;

    @Value("${agentBuilder.template.quota:500}")
    private Integer templateQuota;

    @Resource
    private PePromptTemplateMapper pePromptTemplateMapper;

    @Resource
    private PromptTransactionService conversionTransaction;


    @Override
    public CreatePromptResp savePromptTemplate(String projectId, String workspaceId, PePromptTemplateNewVo body) {
        log.info("save prompt template, projectId: {}, workspaceId: {}", projectId, workspaceId);

        if (body == null) {
            log.warn("save prompt template received null body, projectId: {}, workspaceId: {}", projectId, workspaceId);
            throw new AgentStudioException(StudioError.ARGUMENT_VALID_ERROR);
        }

        if (body.getId() == null || body.getId().isEmpty()) {
            log.info("create new prompt template");
            return new CreatePromptResp().setCode(200)
                    .setMessage("success")
                    .setData(createCustomPromptApiAction(projectId, workspaceId, body));
        } else {
            log.info("update existing prompt template");
            return updateCustomPromptApiAction(projectId, workspaceId, body);
        }
    }

    @Override
    public String createCustomPromptApiAction(String projectId, String workspaceId, PePromptTemplateNewVo body) {
        log.info("create prompt template, projectId: {}, workspaceId: {}", projectId, workspaceId);

        valid(projectId, workspaceId, body);

        int templateNum = pePromptTemplateMapper.countTemplateByProjectId(projectId, workspaceId);
        if (templateNum >= templateQuota) {
            log.warn("template quota exceeded, projectId: {}, workspaceId: {}, current count: {}",
                    projectId, workspaceId, templateNum);
            throw new AgentStudioException(StudioError.TEMPLATE_EXCEEDS_QUOTA, templateQuota.toString());
        }

        try {
            PePromptTemplate pePromptTemplate = new PePromptTemplate();
            BeanUtils.copyProperties(body, pePromptTemplate);
            pePromptTemplate.setId(UUID.randomUUID().toString());
            pePromptTemplate.setWorkspaceId(workspaceId);
            pePromptTemplate.setCreator(RequestContextUtils.getRequestUserName());
            pePromptTemplate.setUpdater(RequestContextUtils.getRequestUserName());
            pePromptTemplate.setDomainId(RequestContextUtils.getRequestUserDomainId());
            validVariables(pePromptTemplate);

            Industry industry = new Industry();
            industry.setId(body.getIndustryId());
            pePromptTemplate.setIndustry(industry);

            List<String> tagIds = body.getTags();
            log.info("insert new prompt template, projectId: {}, tag count: {}", projectId, tagIds.size());
            conversionTransaction.insertOneTemplate(pePromptTemplate, tagIds, projectId);
            log.info("prompt template created successfully, projectId: {}", projectId);
            return pePromptTemplate.getId();
        } catch (Exception e) {
            log.error("create prompt template failed, projectId: {}, error: {}", projectId, e.getMessage(), e);
            throw new AgentStudioException(StudioError.CREATE_TEMPLATE_ERROR);
        }
    }

    public String deleteCustomConnectorAction(String projectId, String workspaceId, String id) {
        log.info("delete prompt template, projectId: {}, workspaceId: {}", projectId, workspaceId);

        validProjectAndWorkspaceId(projectId, workspaceId);

        if (StringUtil.isNullOrEmpty(id)) {
            log.warn("delete prompt template with empty or null ID, projectId: {}, workspaceId: {}",
                    projectId, workspaceId);
            throw new AgentStudioException(StudioError.PROMPT_ID_IS_NOT_EXISTED);
        }

        try {
            pePromptTemplateMapper.deleteTemplateByTemplateId(id, workspaceId);
            log.info("prompt template deleted successfully, projectId: {}", projectId);
            return "success";
        } catch (Exception e) {
            log.error("delete prompt template failed, projectId: {}, error: {}", projectId, e.getMessage(), e);
            throw new AgentStudioException(StudioError.DELETE_TEMPLATE_ERROR);
        }
    }

    @Override
    public PePromptNewListVo getPromptLists(String projectId, GetPromptListsQo getPromptListsQo) {
        log.info("query prompt template list, projectId: {}", projectId);

        if (getPromptListsQo == null) {
            log.warn("query prompt template list with null request, projectId: {}", projectId);
            throw new AgentStudioException(StudioError.ARGUMENT_VALID_ERROR);
        }

        validProjectAndWorkspaceId(projectId, getPromptListsQo.getWorkspaceId());

        try {
            PageInfo<PePromptTemplateNewVo> resultPage = queryWithConditionPaged(projectId, getPromptListsQo);

            PePromptNewListVo peConversionVoPager = new PePromptNewListVo();
            peConversionVoPager.setCount(resultPage.getTotal());
            peConversionVoPager.setTotalPage(resultPage.getPages());
            peConversionVoPager.setHasNextPage(resultPage.isHasNextPage());
            peConversionVoPager.setData(resultPage.getList());
            return peConversionVoPager;
        } catch (Exception e) {
            log.error("query prompt template list failed, projectId: {}, error: {}", projectId, e.getMessage(), e);
            throw new AgentStudioException(StudioError.QUERY_TEMPLATE_ERROR);
        }
    }

    public String Date2String(Date date) {
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")
            .withZone(ZoneId.systemDefault());

        return formatter.format(date.toInstant());
    }

    @Override
    public CreatePromptResp updateCustomPromptApiAction(String projectId, String workspaceId, PePromptTemplateNewVo body) {
        log.info("update prompt template, projectId: {}, workspaceId: {}", projectId, workspaceId);

        valid(projectId, workspaceId, body);

        if (StringUtil.isNullOrEmpty(body.getId())) {
            log.warn("update prompt template with empty or null ID, projectId: {}, workspaceId: {}",
                    projectId, workspaceId);
            throw new AgentStudioException(StudioError.PROMPT_ID_IS_NOT_EXISTED);
        }


        PePromptTemplate pePromptTemplate = pePromptTemplateMapper.queryTemplateIds(body.getId(), workspaceId);
        if (pePromptTemplate == null) {
            log.warn("template not found, projectId: {}, workspaceId: {}, templateId: {}",
                    projectId, workspaceId, body.getId());
            throw new AgentStudioException(StudioError.DATA_NOT_EXIST);
        }

        pePromptTemplate.setUpdater(RequestContextUtils.getRequestUserName());
        pePromptTemplate.setName(
                StringUtil.isNullOrEmpty(body.getName()) ? pePromptTemplate.getName() : body.getName());
        pePromptTemplate.setContent(body.getContent());
        pePromptTemplate.setDescription(
                body.getDescription() == null ? pePromptTemplate.getDescription() : body.getDescription());
        pePromptTemplate.setSource(body.getSource());
        pePromptTemplate.setPtType(body.getPtType());
        pePromptTemplate.setVariables(
                body.getVariables() == null ? pePromptTemplate.getVariables() : body.getVariables());
        pePromptTemplate.setDomainId(RequestContextUtils.getRequestUserDomainId());
        validVariables(pePromptTemplate);

        String industry = body.getIndustryId() == null ? pePromptTemplate.getIndustry().getId() : body.getIndustryId();
        Integer cnt = pePromptTemplateMapper.updateTemplate(pePromptTemplate, industry);
        if (cnt < 1) {
            log.warn("update template failed, projectId: {}, workspaceId: {}, templateId: {}",
                    projectId, workspaceId, body.getId());
            throw new AgentStudioException(StudioError.DATA_NOT_EXIST);
        }

        List<String> tagIds = body.getTags();
        if (!CollectionUtils.isEmpty(tagIds)) {
            log.info("binding tags to template, projectId: {}, workspaceId: {}, tag count: {}",
                    projectId, workspaceId, tagIds.size());
            pePromptTemplateMapper.bindingTemplateIdAndTagId(body.getId(), tagIds, workspaceId);
        } else {
            log.info("unbinding all tags from template, projectId: {}, workspaceId: {}",
                    projectId, workspaceId);
            pePromptTemplateMapper.unbindTemplateIdAndTagId(body.getId(), workspaceId);
        }

        log.info("prompt template updated successfully, projectId: {}, workspaceId: {}",
                projectId, workspaceId);
        return new CreatePromptResp().setCode(200).setMessage("success to update").setData(pePromptTemplate.getId());
    }

    /**
     * 查询模板并分页
     *
     * @param projectId
     * @return PageInfo<PeConversionVo>
     */
    private PageInfo<PePromptTemplateNewVo> queryWithConditionPaged(String projectId, GetPromptListsQo getPromptListsQo) {
        Integer offset = getPromptListsQo.getOffset();
        Integer limit = getPromptListsQo.getLimit();
        String workspaceId = getPromptListsQo.getWorkspaceId();

        log.info("query prompt template list, projectId: {}, workspaceId: {}", projectId, workspaceId);

        if (isInvalidOffsetOrLimit(offset, limit)) {
            log.warn("invalid offset or limit, projectId: {}, workspaceId: {}, offset: {}, limit: {}",
                    projectId, workspaceId, offset, limit);
            throw new AgentStudioException(StudioError.LIMIT_OR_OFFSET_INVALID);
        }

        try {
            PageInfo<String> resultPageTemp = PageHelper.offsetPage(offset, limit)
                    .doSelectPageInfo(() -> pePromptTemplateMapper.queryTemplateIdsByCondition2(projectId, workspaceId,
                            getPromptListsQo.getName()));

            PageInfo<PePromptTemplateNewVo> resultPage = new PageInfo<>();
            BeanUtils.copyProperties(resultPageTemp, resultPage);

            if (!resultPageTemp.getList().isEmpty()) {
                List<PePromptTemplate> pePromptTemplates = pePromptTemplateMapper.queryTemplateDetailByTemplateIds(
                        resultPageTemp.getList(), workspaceId);
                List<PePromptTemplateNewVo> result = pePromptTemplates.stream()
                        .map(PePromptTemplate::convertToPePromptTemplateNewVO)
                        .collect(Collectors.toList());
                resultPage.setList(result);
            }
            return resultPage;
        } catch (Exception e) {
            log.error("query prompt template list failed, projectId: {}, workspaceId: {}, error: {}",
                    projectId, workspaceId, e.getMessage(), e);
            throw new AgentStudioException(StudioError.QUERY_LIST_FAILED);
        }
    }

    private boolean isInvalidOffsetOrLimit(Integer offset, Integer limit) {
        if (offset == null || offset < 0 || offset > 65535) {
            return true;
        }
        return limit == null || limit < 1 || limit > 1000;
    }

    private String generateUniqueCopyName(String name, String projectId, String workspaceId) {
        int suffix = 1;
        String newName;
        for (int i = 0; i < 1000; i++) {
            newName = name + "_copy" + suffix++;
            if (pePromptTemplateMapper.isNameExist2(newName, projectId, workspaceId) == null) {
                log.info("generated unique copy name: {}, projectId: {}, workspaceId: {}",
                        newName, projectId, workspaceId);
                return newName;
            }
        }

        log.warn("copy name generation failed, projectId: {}, workspaceId: {}",
                projectId, workspaceId);
        throw new AgentStudioException(StudioError.COPY_LIMIT_EXCEEDED, projectId);
    }

    public String copyCustomPromptApiAction(String projectId, String workspaceId, String id) {
        log.info("copy prompt template, projectId: {}, workspaceId: {}", projectId, workspaceId);

        validProjectAndWorkspaceId(projectId, workspaceId);

        if (StringUtil.isNullOrEmpty(id)) {
            log.warn("copy prompt template with empty or null ID, projectId: {}, workspaceId: {}",
                projectId, workspaceId);
            throw new AgentStudioException(StudioError.PROMPT_ID_IS_NOT_EXISTED);
        }

        PePromptTemplate promptTemplate = pePromptTemplateMapper.queryTemplate(id);
        if (promptTemplate == null) {
            log.warn("template not found, projectId: {}, workspaceId: {}, templateId: {}",
                projectId, workspaceId, id);
            throw new AgentStudioException(StudioError.QUERY_TEMPLATE_ERROR);
        }

        promptTemplate.setId(UUID.randomUUID().toString());
        promptTemplate.setName(generateUniqueCopyName(promptTemplate.getName(), projectId, workspaceId));
        promptTemplate.setWorkspaceId(workspaceId);
        promptTemplate.setCreator(RequestContextUtils.getRequestUserName());
        promptTemplate.setUpdater(RequestContextUtils.getRequestUserName());
        promptTemplate.setCreatedOn(new Timestamp(System.currentTimeMillis()));
        promptTemplate.setUpdatedOn(new Timestamp(System.currentTimeMillis()));

        try {
            pePromptTemplateMapper.insertOneTemplate(promptTemplate, projectId, promptTemplate.getIndustry().getId());
            log.info("prompt template copied successfully, projectId: {}, workspaceId: {}",
                projectId, workspaceId);
            return promptTemplate.getId();
        } catch (Exception e) {
            log.error("copy prompt template failed, projectId: {}, workspaceId: {}, error: {}",
                projectId, workspaceId, e.getMessage(), e);
            throw new AgentStudioException(StudioError.QUERY_TEMPLATE_ERROR);
        }
    }

    private void validProjectAndWorkspaceId(String projectId, String workspaceId) {
        if (StringUtil.isNullOrEmpty(projectId)) {
            log.warn("empty or null project ID, projectId: {}", projectId);
            throw new AgentStudioException(StudioError.PROJECT_ID_NOT_FOUND, projectId);
        }
        if (StringUtil.isNullOrEmpty(workspaceId)) {
            log.warn("empty or null workspace ID, workspaceId: {}", workspaceId);
            throw new AgentStudioException(StudioError.WORKSPACE_ID_NOT_FOUND, workspaceId);
        }
    }

    private boolean isAdmin(String userName) {
        // 校验是否为admin用户
        if (!Strings.CS.equals(userName, adminName)) {
            return false;
        }
        return true;
    }

    private void valid(String projectId, String workspaceId, PePromptTemplateNewVo body) {
        validProjectAndWorkspaceId(projectId, workspaceId);

        if (body == null) {
            log.warn("empty or null request body, projectId: {}, workspaceId: {}",
                    projectId, workspaceId);
            throw new AgentStudioException(StudioError.REQUEST_BODY_NOT_EMPTY);
        }

        if (Boolean.TRUE.equals(
                pePromptTemplateMapper.isNameExist(body.getName(), body.getId(), projectId, workspaceId))) {
            log.warn("name already exists, projectId: {}, workspaceId: {}, name: {}",
                    projectId, workspaceId, body.getName());
            throw new AgentStudioException(StudioError.NAME_IS_EXIST);
        }

        if (PtTypeEnum.fromValue(body.getPtType()) == null) {
            log.warn("invalid ptType, projectId: {}, workspaceId: {}, ptType: {}",
                    projectId, workspaceId, body.getPtType());
            throw new AgentStudioException(StudioError.INVALID_PT_TYPE);
        }

        SimpleUser userInfo = RequestContextUtils.getRequestUser();
        if (Arrays.stream(Source.values()).noneMatch(s -> s.name().equals(body.getSource()))) {
            log.error("invalid source value: {}", body.getSource());
            throw new AgentStudioException(StudioError.INVALID_SOURCE);
        }

        if (!isAdmin(userInfo.getDomainName()) && Source.PRESET.name().equals(body.getSource())) {
            log.error("only admin tenant can operate preset template");
            throw new AgentStudioException(StudioError.AUTH_FAILED);
        }
    }


    private void validVariables(PePromptTemplate pePromptTemplate) {
        PtTypeEnum ptType = PtTypeEnum.fromValue(pePromptTemplate.getPtType());
        if (!StringUtil.isNullOrEmpty(pePromptTemplate.getVariables())) {
            try {
                log.info("validating variables for template.");
                List<PromptVar> varList = JSON.parseObject(pePromptTemplate.getVariables(),
                    new TypeReference<List<PromptVar>>() { });
                varList.forEach(var -> {
                    assertNotNull(var.getName(), "The name field in PromptVar is empty.");
                    assertNotNull(var.getType(), "The type field in PromptVar is empty.");

                    // 如果 pt_type 是 TEXT，则每个变量的 type 必须也是 TEXT
                    if (ptType == PtTypeEnum.TEXT && !var.getType().equals(PtTypeEnum.TEXT)) {
                        log.warn("invalid variable type for TEXT template.");
                        throw new AgentStudioException(StudioError.INVALID_VARIABLE_TYPE_FOR_TEXT_TEMPLATE);
                    }
                });
            } catch (JSONException e) {
                log.warn("invalid variables format, error: {}", e.getMessage());
                throw new AgentStudioException(StudioError.INVALID_VARIABLES);
            }
        }
    }

}
