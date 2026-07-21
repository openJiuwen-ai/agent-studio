/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.service;

import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.CN_LANGUAGE;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.CONTENT_LENGTH_EXCEED;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.EN_LANGUAGE;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.INDUSTRY_NOT_FOUND;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.LOCAL_NAME_TEMPLATE_CONTENT;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.LOCAL_NAME_TEMPLATE_CREATED_ON;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.LOCAL_NAME_TEMPLATE_CREATOR;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.LOCAL_NAME_TEMPLATE_DESCP;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.LOCAL_NAME_TEMPLATE_INDUSTRY;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.LOCAL_NAME_TEMPLATE_LABEL;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.LOCAL_NAME_TEMPLATE_MODIFIED_ON;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.LOCAL_NAME_TEMPLATE_NAME;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.LOCAL_NAME_TEMPLATE_VAR;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.NUM_ONE;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.PROMPT_NAME_DUPLICATE;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.PROMPT_NAME_EXISTS;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.PROMPT_NAME_INVALID;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.ROWS_EXCEED_LIMIT;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.TAG_NOT_FOUND;
import static com.openjiuwen.studio.prompt.engineering.enums.FileType.FILE_TYPE_EXCEL;

import com.alibaba.excel.EasyExcel;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.prompt.engineering.annotation.LimitOffset;
import com.openjiuwen.studio.prompt.engineering.annotation.RedisRateLimit;
import com.openjiuwen.studio.prompt.engineering.constant.CommonConstant;
import com.openjiuwen.studio.prompt.engineering.dto.ManualPePromptTemplateDto;
import com.openjiuwen.studio.prompt.engineering.dto.PePromptTemplateDto;
import com.openjiuwen.studio.prompt.engineering.dto.PePromptTemplateListVo;
import com.openjiuwen.studio.prompt.engineering.dto.PePromptTemplateVo;
import com.openjiuwen.studio.prompt.engineering.dto.QueryTemplateCondition;
import com.openjiuwen.studio.prompt.engineering.entity.Industry;
import com.openjiuwen.studio.prompt.engineering.entity.PePromptTemplate;
import com.openjiuwen.studio.prompt.engineering.entity.PeTag;
import com.openjiuwen.studio.prompt.engineering.entity.PeTask;
import com.openjiuwen.studio.prompt.engineering.entity.TemplateOneRow;
import com.openjiuwen.studio.prompt.engineering.enums.Source;
import com.openjiuwen.studio.prompt.engineering.enums.TemplateImportEnum;
import com.openjiuwen.studio.prompt.engineering.listenner.DynamicExcelListener;
import com.openjiuwen.studio.prompt.engineering.mapper.PeIndustryMapper;
import com.openjiuwen.studio.prompt.engineering.mapper.PePromptTemplateMapper;
import com.openjiuwen.studio.prompt.engineering.mapper.PeTagMapper;
import com.openjiuwen.studio.prompt.engineering.mapper.PeTaskMapper;
import com.openjiuwen.studio.prompt.engineering.utils.ExcelI18nHandler;
import com.openjiuwen.studio.prompt.engineering.utils.ExcelUtil;
import com.openjiuwen.studio.prompt.engineering.utils.FileUtil;
import com.openjiuwen.studio.prompt.engineering.utils.HttpUtil;
import com.openjiuwen.studio.prompt.engineering.utils.StringUtil;
import com.openjiuwen.studio.prompt.engineering.vo.TemplateDownloadVo;

import cn.afterturn.easypoi.handler.inter.II18nHandler;
import jakarta.annotation.Resource;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.CellType;
import org.apache.poi.ss.usermodel.DataFormatter;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.xssf.usermodel.XSSFCell;
import org.apache.poi.xssf.usermodel.XSSFRow;
import org.apache.poi.xssf.usermodel.XSSFSheet;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.MessageSource;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStream;
import java.text.MessageFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.ListIterator;
import java.util.Map;
import java.util.Objects;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

/**
 * PromptTemplate service
 */
@Component
@Slf4j
public class PromptTemplateService implements IPromptLibraryService {

    private static final Pattern TEMPLATE_NAME_PATTERN = Pattern.compile(
        "^[\\u4e00-\\u9fa5a-zA-Z][\\u4e00-\\u9fa5\\w\\-()]{0,32}[\\u4e00-\\u9fa5a-zA-Z0-9()]$");

    @Autowired
    private MessageSource messageSource;

    @Value("${agentBuilder.template.quota:500}")
    private Integer templateQuota;

    @Value("${agentBuilder.template.download.quota:100}")
    private Integer templateDownloadQuota;

    @Value("${prompt.contentlenth: 10000}")
    private int promptContentMaxLength;

    @Value("${agentBuilder.template.import.quota:100}")
    private Integer templateImportQuota;

    @Value("${admin.domain.name}")
    private String adminName;

    @Value("${spring.is-soft-delete: true}")
    private Boolean isSoftDelete;

    @Resource
    private PromptTransactionService conversionTransaction;

    @Resource
    private PeTaskMapper peTaskMapper;

    @Resource
    private PePromptTemplateMapper pePromptTemplateMapper;

    @Resource
    private HttpServletResponse response;

    @Resource
    private PeIndustryMapper industryMapper;

    @Autowired
    private ShareInnerPromptService shareInnerPromptService;

    @Autowired
    @Qualifier("PeTagMapper")
    private PeTagMapper tagMapper;


    @Transactional
    public String createPromptTemplate(String projectId, String workspaceId, PePromptTemplateDto body) {
        log.info("operation log {} : create prompt template", projectId);
        checkReq(body, projectId, workspaceId);
        SimpleUser userInfo = RequestContextUtils.getRequestUser();
        List<PeTask> peTasks = peTaskMapper.queryTaskDetailsByTaskIds(Collections.singletonList(body.getTaskId()), workspaceId);
        if (CollectionUtils.isEmpty(peTasks)) {
            throw new AgentStudioException(StudioError.TASK_ID_IS_NOT_EXIST, body.getTaskId());
        }
        Industry industry = peTasks.get(0).getIndustry();
        body.setIndustryId(Objects.nonNull(industry) ? industry.getId() : null);
        try {

            PePromptTemplate pePromptTemplate = PePromptTemplate.convertToPePromptTemplate(body);
            pePromptTemplate.setWorkspaceId(workspaceId);
            pePromptTemplate.setCreator(userInfo.getUserName());
            pePromptTemplate.setUpdater(userInfo.getUserName());
            // 继承工程任务绑定的标签
            List<String> tagIdsByTaskId = peTaskMapper.queryTagIdsByTaskId(body.getTaskId(), workspaceId);

            conversionTransaction.insertOneTemplate(pePromptTemplate, tagIdsByTaskId, projectId);
            return HttpStatus.OK.toString();
        } catch (Exception e) {
            throw new AgentStudioException(StudioError.CREATE_TEMPLATE_ERROR);
        }
    }


    @Transactional
    public String savePromptTemplate(String projectId, String workspaceId, PePromptTemplateDto body) {
        log.info("operation log {} : save prompt template", projectId);

        // 校验模板名称不可以重复
        if (Boolean.TRUE.equals(pePromptTemplateMapper.isNameExist(body.getName(), body.getId(), projectId, workspaceId))) {
            throw new AgentStudioException(StudioError.NAME_IS_EXIST);
        }
        // 一个projectId下暂定最多保存500条模板
        int templateNum = pePromptTemplateMapper.countTemplateByProjectId(projectId, workspaceId);
        if (templateNum >= templateQuota) {
            throw new AgentStudioException(StudioError.TEMPLATE_EXCEEDS_QUOTA, templateQuota.toString());
        }
        SimpleUser userInfo = RequestContextUtils.getRequestUser();
        try {
            PePromptTemplate pePromptTemplate = PePromptTemplate.convertToPePromptTemplate(body);
            pePromptTemplate.setCreator(userInfo.getUserName());
            pePromptTemplate.setUpdater(userInfo.getUserName());
            pePromptTemplate.setWorkspaceId(workspaceId);
            pePromptTemplate.setSource(Source.NO_SOURCE.name());
            pePromptTemplate.setDomainId(RequestContextUtils.getRequestUserDomainId());
            // 前端传入的标签
            List<String> tagIds = body.getTags();
            conversionTransaction.insertOneTemplate(pePromptTemplate, tagIds, projectId);
            return HttpStatus.OK.toString();
        } catch (Exception e) {
            throw new AgentStudioException(StudioError.CREATE_TEMPLATE_ERROR);
        }
    }

    @Override
    @Transactional
    public String deletePromptTemplate(String projectId, String templateId, String workspaceId) {
        log.info("Operation log - ProjectId: {}, WorkspaceId: {} : Start deleting prompt template", projectId, workspaceId);

        SimpleUser userInfo = RequestContextUtils.getRequestUser();
        List<PePromptTemplate> pePromptTemplates = pePromptTemplateMapper.queryTemplateDetailByTemplateIds(
                Collections.singletonList(templateId), workspaceId);

        if (CollectionUtils.isEmpty(pePromptTemplates)) {
            log.warn("Template not found - ProjectId: {}, WorkspaceId: {}, TemplateId: {}", projectId, workspaceId, templateId);
            throw new AgentStudioException(StudioError.DATA_NOT_EXIST);
        }

        String source = pePromptTemplates.get(0).getSource();
        if (!isAdmin(userInfo.getDomainName()) && Source.PRESET.name().equals(source)) {
            log.warn("Permission denied - ProjectId: {}, WorkspaceId: {}, TemplateId: {}, User is not admin and template is preset",
                    projectId, workspaceId, templateId);
            throw new AgentStudioException(StudioError.AUTH_FAILED);
        }
        // 是否共享校验
        shareInnerPromptService.cancelPromptShared(templateId, projectId, workspaceId);

        try {
            log.info("Start deleting prompt template, is soft delest : {}", isSoftDelete);
            if (isSoftDelete) {
                // 执行软删除，不真正删除数据
                List<PeTag> tags = pePromptTemplates.get(0).getTags();
                List<String> tagIdsList = new ArrayList<>();

                for (PeTag tag : tags) {
                    tagIdsList.add(tag.getId());
                }
                pePromptTemplateMapper.copyToHistory(templateId, workspaceId, tagIdsList.toString());
                log.info("Prompt template soft deleted successfully - ProjectId: {}, WorkspaceId: {}, TemplateId: {}",
                        projectId, workspaceId, templateId);
            }
            pePromptTemplateMapper.unbindTemplateIdAndTagId(templateId, workspaceId);
            pePromptTemplateMapper.deleteTemplateByTemplateId(templateId, workspaceId);
            return templateId;

        } catch (Exception e) {
            log.error("Failed to soft delete prompt template - ProjectId: {}, WorkspaceId: {}, TemplateId: {}",
                    projectId, workspaceId, templateId, e);
            throw new AgentStudioException(StudioError.DELETE_TEMPLATE_ERROR);
        }
    }

    @Transactional
    public String batchDeletePromptTemplate(String projectId, String workspaceId, List<String> templateIds) {
        log.info("operation log {} : batch delete prompt template", projectId);
        SimpleUser userInfo = RequestContextUtils.getRequestUser();
        List<PePromptTemplate> pePromptTemplates = pePromptTemplateMapper.queryTemplateDetailByTemplateIds(templateIds, workspaceId);
        if (CollectionUtils.isEmpty(pePromptTemplates)) {
            throw new AgentStudioException(StudioError.DATA_NOT_EXIST);
        }
        String source = pePromptTemplates.get(0).getSource();
        if (!isAdmin(userInfo.getDomainName()) && Source.PRESET.name().equals(source)) {
            throw new AgentStudioException(StudioError.AUTH_FAILED);
        }
        try {
            pePromptTemplateMapper.batchUnbindTemplateIdAndTagId(templateIds, workspaceId);
            pePromptTemplateMapper.batchDeleteTemplateByTemplateId(templateIds, workspaceId);
            return HttpStatus.OK.toString();
        } catch (Exception e) {
            throw new AgentStudioException(StudioError.DELETE_TEMPLATE_ERROR);
        }
    }


    public Boolean checkAuth(String projectId, String workspaceId) {
        log.info("operation log {} : check auth", projectId);
        SimpleUser userInfo = RequestContextUtils.getRequestUser();
        if (userInfo == null) {
            return false;
        }
        return Strings.CS.equals(adminName, userInfo.getDomainName());
    }

    @Override
    @LimitOffset
    public PePromptTemplateListVo listPromptTemplates(String projectId, String workspaceId, String category, QueryTemplateCondition body) {
        log.info("Operation log - ProjectId: {}, WorkspaceId: {} : Start listing prompt templates", projectId, workspaceId);
        // 查询转译
        body.setTemplateName(StringUtil.escapeLikeParam(body.getTemplateName()));
        body.setContent(StringUtil.escapeLikeParam(body.getContent()));
        body.setDescription(StringUtil.escapeLikeParam(body.getDescription()));
        try {
            PageInfo<PePromptTemplateVo> resultPage = queryWithConditionPaged(body, projectId, workspaceId, category);

            log.info("Listed prompt templates");

            PePromptTemplateListVo peConversionVoPager = new PePromptTemplateListVo();
            peConversionVoPager.setCount(resultPage.getTotal());
            peConversionVoPager.setTotalPage(resultPage.getPages());
            peConversionVoPager.setHasNextPage(resultPage.isHasNextPage());
            peConversionVoPager.setData(resultPage.getList());

            log.info("Prompt templates returned - ProjectId: {}, WorkspaceId: {}, Data size: {}",
                    projectId, workspaceId, peConversionVoPager.getData().size());

            return peConversionVoPager;
        } catch (Exception e) {
            log.error("Failed to list prompt templates - ProjectId: {}, WorkspaceId: {}", projectId, workspaceId, e);
            throw new AgentStudioException(StudioError.QUERY_LIST_FAILED);
        }
    }


    public String manualCreatePromptTemplate(String projectId, String workspaceId, ManualPePromptTemplateDto body) {
        log.info("operation log {} : create manual prompt template", projectId);
        // 校验是否为admin用户
        SimpleUser userInfo = RequestContextUtils.getRequestUser();
        if (!Strings.CS.equals(userInfo.getDomainName(), adminName)) {
            log.error("only admin tenant can operate preset template");
            throw new AgentStudioException(StudioError.AUTH_FAILED);
        }
        // 校验模板名称不可以重复
        if (Boolean.TRUE.equals(pePromptTemplateMapper.isNameExist(body.getName(), body.getId(), projectId, workspaceId))) {
            throw new AgentStudioException(StudioError.NAME_IS_EXIST);
        }
        // 一个projectId下暂定最多保存500条模板
        int templateNum = pePromptTemplateMapper.countPresetTemplateByProjectId(projectId, workspaceId);
        if (templateNum >= templateQuota) {
            throw new AgentStudioException(StudioError.TEMPLATE_EXCEEDS_QUOTA, List.of(templateQuota.toString()));
        }

        try {
            PePromptTemplate pePromptTemplate = PePromptTemplate.convertToPePromptTemplate(body);
            pePromptTemplate.setWorkspaceId(workspaceId);
            pePromptTemplate.setSource(Source.PRESET.name());
            pePromptTemplate.setCreator(userInfo.getUserName());
            pePromptTemplate.setUpdater(userInfo.getUserName());
            List<String> tagIdsByTaskId = body.getTagList();

            conversionTransaction.insertOneTemplate(pePromptTemplate, tagIdsByTaskId, projectId);
            return HttpStatus.OK.toString();
        } catch (Exception e) {
            throw new AgentStudioException(StudioError.CREATE_TEMPLATE_ERROR);
        }
    }


    public PePromptTemplateVo queryPromptTemplate(String projectId, String id, String workspaceId) {
        log.info("operation log {} : query prompt template", projectId);
        try {
            // 先查官方预置
            List<PePromptTemplate> pePromptTemplates = pePromptTemplateMapper.queryTemplateDetailByCreatorTemplateIds(Collections.singletonList(id));
            // 再查个人空间
            if (CollectionUtils.isEmpty(pePromptTemplates)) {
                pePromptTemplates = pePromptTemplateMapper.queryTemplateDetailByTemplateIds(Collections.singletonList(id), workspaceId);
            }
            List<PePromptTemplateVo> result = pePromptTemplates.stream()
                    .map(PePromptTemplate::convertToPePromptTemplateVO)
                    .collect(Collectors.toList());
            return result.get(0);
        } catch (Exception e) {
            throw new AgentStudioException(StudioError.QUERY_TEMPLATE_ERROR);
        }
    }

    /**
     * 查询模板并分页
     *
     * @param body 查询条件
     * @return PageInfo<PeConversionVo>
     */
    private PageInfo<PePromptTemplateVo> queryWithConditionPaged(QueryTemplateCondition body, String projectId, String workspaceId, String category) {
        log.info("Querying prompt templates with condition - ProjectId: {}, WorkspaceId: {}", projectId, workspaceId);

        try {
            PageInfo<String> resultPageTemp = PageHelper.offsetPage(body.getOffset(), body.getLimit())
                    .doSelectPageInfo(() -> pePromptTemplateMapper.queryTemplateIdsByCondition(body, projectId, workspaceId, category));

            log.info("Fetched template IDs");

            PageInfo<PePromptTemplateVo> resultPage = new PageInfo<>();
            BeanUtils.copyProperties(resultPageTemp, resultPage);

            if (CollectionUtils.isNotEmpty(resultPageTemp.getList())) {
                List<PePromptTemplate> pePromptTemplates = pePromptTemplateMapper.queryTemplateDetailByTemplateId(
                        resultPageTemp.getList(), workspaceId);

                log.info("Fetched template details - ProjectId: {}, WorkspaceId: {}, Count: {}",
                        projectId, workspaceId, pePromptTemplates.size());

                List<PePromptTemplateVo> result = pePromptTemplates.stream().map(pePromptTemplate -> {
                    PePromptTemplateVo pePromptTemplateVo = pePromptTemplate.convertToPePromptTemplateVO();
                    if (Strings.CI.equals(pePromptTemplate.getSource(), Source.PRESET.name())
                        && Strings.CI.equals(HttpUtil.getLanguage(), CommonConstant.EN_LANGUAGE)) {
                        pePromptTemplateVo.setCreator("Official Preset");
                    }
                    return pePromptTemplateVo;
                }).collect(Collectors.toList());

                resultPage.setList(result);
            }

            log.info("Prompt template query completed - ProjectId: {}, WorkspaceId: {}, Total: {}, Data size: {}",
                    projectId, workspaceId, resultPage.getTotal(), resultPage.getList().size());

            return resultPage;
        } catch (Exception e) {
            log.error("Failed to query prompt templates - ProjectId: {}, WorkspaceId: {}", projectId, workspaceId, e);
            throw new AgentStudioException(StudioError.QUERY_TEMPLATE_ERROR);
        }
    }


    @Transactional
    public String updatePromptTemplate(String projectId, String workspaceId, ManualPePromptTemplateDto body) {
        log.info("operation log {} : update prompt template", projectId);
        SimpleUser userInfo = RequestContextUtils.getRequestUser();
        if (!isAdmin(userInfo.getDomainName()) && Source.PRESET.name().equals(body.getSource())) {
            log.error("only admin tenant can operate preset template");
            throw new AgentStudioException(StudioError.AUTH_FAILED);
        }
        // 校验模板名称不可以重复
        if (Boolean.TRUE.equals(pePromptTemplateMapper.isNameExist(body.getName(), body.getId(), projectId, workspaceId))) {
            throw new AgentStudioException(StudioError.NAME_IS_EXIST);
        }

        try {
            String industry_id = body.getIndustryId();
            // 更新标签 模板内容 模板名称
            PePromptTemplate pePromptTemplate = PePromptTemplate.convertToPePromptTemplate(body);
            pePromptTemplate.setUpdater(userInfo.getUserName());
            pePromptTemplate.setWorkspaceId(workspaceId);
            Integer cnt = pePromptTemplateMapper.updateTemplate(pePromptTemplate, industry_id);
            if (cnt < NUM_ONE) {
                throw new AgentStudioException(StudioError.DATA_NOT_EXIST);
            }
            List<String> tagIds = body.getTagList();
            pePromptTemplateMapper.unbindTemplateIdAndTagId(body.getId(), workspaceId);
            if (!CollectionUtils.isEmpty(tagIds)) {
                pePromptTemplateMapper.bindingTemplateIdAndTagId(body.getId(), tagIds, workspaceId);
            }
            return HttpStatus.OK.toString();
        } catch (Exception e) {
            throw new AgentStudioException(StudioError.UPDATE_TEMPLATE_ERROR);
        }
    }

    public String downloadPromptSampleTemplate(String projectId, String workspaceId) {
        log.info("operation log {} : export prompt sample template", projectId);
        XSSFWorkbook xssfWorkbook = new XSSFWorkbook();
        XSSFSheet sheet = xssfWorkbook.createSheet();
        XSSFRow headRow = sheet.createRow(CommonConstant.NUM_ZERO);
        XSSFRow firstRow = sheet.createRow(NUM_ONE);
        for (int i = 0; i < TemplateImportEnum.values().length; i++) {
            String column;
            String sampleValue;
            if (EN_LANGUAGE.equals(HttpUtil.getLanguage())) {
                column = TemplateImportEnum.values()[i].getColumnEn();
                sampleValue = TemplateImportEnum.values()[i].getSampleValueEn();
            } else {
                column = TemplateImportEnum.values()[i].getColumn();
                sampleValue = TemplateImportEnum.values()[i].getSampleValue();
            }
            XSSFCell headCell = headRow.createCell(i);
            headCell.setCellType(CellType.STRING);
            headCell.setCellValue(column);
            XSSFCell firstRowCell = firstRow.createCell(i);
            firstRowCell.setCellType(CellType.STRING);
            firstRowCell.setCellValue(sampleValue);
        }
        // 导出文件
        ExcelUtil.exportExcelFile(xssfWorkbook, response, StudioError.EXPORT_PROMPT_TEMPLATE_FAILED);
        return null;
    }



    @Override
    public String downloadPromptTemplateV2(String projectId, String workspaceId, List<String> templateIds) {
        log.info("Operation started - ProjectId: {}, WorkspaceId: {}, TemplateIds: {}", projectId, workspaceId, templateIds);


        try {
            checkDownloadedTemplateNum(templateIds);
            log.info("Download validation passed, proceeding to export - TemplateIds: {}", templateIds);

            XSSFWorkbook xssfWorkbook = new XSSFWorkbook();
            log.info("Started creating Excel workbook for template download");

            II18nHandler i18nHandler = new ExcelI18nHandler(messageSource);
            XSSFSheet sheet = xssfWorkbook.createSheet();
            List<TemplateDownloadVo> templateDownloadVos = queryDownloadVoList(templateIds, workspaceId, projectId);
            log.info("Fetched {} template records for export", templateDownloadVos.size());

            XSSFRow headRow = sheet.createRow(CommonConstant.NUM_ZERO);
            List<String> headersStr = new ArrayList<>();
            headersStr.add(i18nHandler.getLocaleName(LOCAL_NAME_TEMPLATE_NAME));
            headersStr.add(i18nHandler.getLocaleName(LOCAL_NAME_TEMPLATE_CONTENT));
            headersStr.add(i18nHandler.getLocaleName(LOCAL_NAME_TEMPLATE_DESCP));
            headersStr.add(i18nHandler.getLocaleName(LOCAL_NAME_TEMPLATE_LABEL));
            headersStr.add(i18nHandler.getLocaleName(LOCAL_NAME_TEMPLATE_INDUSTRY));
            headersStr.add(i18nHandler.getLocaleName(LOCAL_NAME_TEMPLATE_VAR));
            headersStr.add(i18nHandler.getLocaleName(LOCAL_NAME_TEMPLATE_CREATOR));
            headersStr.add(i18nHandler.getLocaleName(LOCAL_NAME_TEMPLATE_CREATED_ON));
            headersStr.add(i18nHandler.getLocaleName(LOCAL_NAME_TEMPLATE_MODIFIED_ON));

            for (int i = 0; i < headersStr.size(); i++) {
                XSSFCell headCell = headRow.createCell(i);
                headCell.setCellValue(headersStr.get(i));
            }

            for (int i = 0; i < templateDownloadVos.size(); i++) {
                TemplateDownloadVo templateDownloadVo = templateDownloadVos.get(i);
                XSSFRow valueRow = sheet.createRow(NUM_ONE + i);
                XSSFCell valueCell1 = valueRow.createCell(0);
                valueCell1.setCellValue(templateDownloadVo.getTemplateName());
                XSSFCell valueCell2 = valueRow.createCell(1);
                valueCell2.setCellValue(templateDownloadVo.getContent());
                XSSFCell valueCell3 = valueRow.createCell(2);
                valueCell3.setCellValue(templateDownloadVo.getDescription());
                XSSFCell valueCell4 = valueRow.createCell(3);
                valueCell4.setCellValue(templateDownloadVo.getTag());
                XSSFCell valueCell5 = valueRow.createCell(4);
                valueCell5.setCellValue(templateDownloadVo.getIndustry());
                XSSFCell valueCell6 = valueRow.createCell(5);
                valueCell6.setCellValue(templateDownloadVo.getVariables());
                XSSFCell valueCell7 = valueRow.createCell(6);
                valueCell7.setCellValue(templateDownloadVo.getCreator());
                XSSFCell valueCell8 = valueRow.createCell(7);
                valueCell8.setCellValue(templateDownloadVo.getCreatedOn());
                XSSFCell valueCell9 = valueRow.createCell(8);
                valueCell9.setCellValue(templateDownloadVo.getUpdatedOn());
            }

            log.info("Excel content filled successfully, preparing to export");

            ExcelUtil.exportExcelFile(xssfWorkbook, response, StudioError.EXPORT_EVALUATION_RESULT_FAILED);
            return null;
        } catch (Exception e) {
            log.error("Failed to export template - ProjectId: {}, WorkspaceId: {}", projectId, workspaceId, e);
            throw new AgentStudioException(StudioError.EXPORT_PROMPT_TEMPLATE_FAILED);
        }
    }

    private void checkDownloadedTemplateNum(List<String> templateIds) {
        // 校验一次性导出是否满足不超过100个提示词
        if (templateIds.size() >= templateDownloadQuota) {
            throw new AgentStudioException(StudioError.DOWNLOAD_TEMPLATE_EXCEEDS_QUOTA, List.of(templateDownloadQuota
                    .toString()));
        }
    }

    public List<TemplateDownloadVo> queryDownloadVoList(List<String> templateIds, String workspaceId, String projectId) {
        log.info("Querying template download data - TemplateIds: {}, WorkspaceId: {}", templateIds, workspaceId);

        try {
            if (CollectionUtils.isNotEmpty(templateIds)) {
                List<PePromptTemplate> officialTemplates = pePromptTemplateMapper.queryTemplateDetailByCreatorTemplateIds(templateIds);
                log.info("Fetched {} official templates done.", officialTemplates.size());

                List<PePromptTemplate> personalTemplates = pePromptTemplateMapper.queryTemplateDetailByPersonTemplateIds(templateIds, workspaceId);
                log.info("Fetched {} personal templates done.", personalTemplates.size());

                List<PePromptTemplate> pePromptTemplates = new ArrayList<>();
                if (projectId.equals(RequestContextUtils.getRequestProjectId()) && workspaceId.equals(RequestContextUtils.getRequestWorkspaceId())) {
                    pePromptTemplates.addAll(officialTemplates);
                }
                pePromptTemplates.addAll(personalTemplates);

                List<TemplateDownloadVo> result = new ArrayList<>();
                for (PePromptTemplate template : pePromptTemplates) {
                    TemplateDownloadVo vo = template.convertToTemplateDownloadVo();
                    result.add(vo);
                }

                log.info("Converted {} templates to download VO", result.size());
                return result;
            }

            log.info("No template IDs provided, returning empty list");
            return Collections.emptyList();
        } catch (Exception e) {
            log.error("Failed to query template download data - TemplateIds: {}, WorkspaceId: {}", templateIds, workspaceId, e);
            throw new AgentStudioException(StudioError.QUERY_TEMPLATE_ERROR);
        }
    }

    private void checkReq(PePromptTemplateDto body, String projectId, String workspaceId) {
        log.info("Validating request - ProjectId: {}, WorkspaceId: {}, TemplateName: {}", projectId, workspaceId, body.getName());

        try {
            // 校验 taskId 是否存在
            if (!Boolean.TRUE.equals(peTaskMapper.isIdExist(body.getTaskId(), workspaceId))) {
                log.warn("TaskId not found - TaskId: {}, WorkspaceId: {}", body.getTaskId(), workspaceId);
                throw new AgentStudioException(StudioError.TASK_ID_IS_NOT_EXIST, body.getTaskId());
            }

            // 校验模板名称是否重复
            if (Boolean.TRUE.equals(pePromptTemplateMapper.isNameExist(body.getName(), body.getId(), projectId, workspaceId))) {
                log.warn("Template name already exists - Name: {}, ProjectId: {}, WorkspaceId: {}", body.getName(), projectId, workspaceId);
                throw new AgentStudioException(StudioError.NAME_IS_EXIST);
            }

            // 校验模板数量是否超过配额
            int templateNum = pePromptTemplateMapper.countTemplateByProjectId(projectId, workspaceId);
            log.info("Current template count in project - ProjectId: {}, Count: {}", projectId, templateNum);

            if (templateNum >= templateQuota) {
                log.warn("Template quota exceeded - ProjectId: {}, Current: {}, Max: {}", projectId, templateNum, templateQuota);
                throw new AgentStudioException(StudioError.TEMPLATE_EXCEEDS_QUOTA, List.of(templateQuota.toString()));
            }
        } catch (Exception e) {
            log.error("Failed to validate request - ProjectId: {}, WorkspaceId: {}", projectId, workspaceId, e);
            throw new AgentStudioException(StudioError.ARGUMENT_VALID_ERROR);
        }
    }

    private boolean isAdmin(String userName) {
        // 校验是否为admin用户
        if (!Strings.CS.equals(userName, adminName)) {
            return false;
        }
        return true;
    }


    public List<String> importPromptTemplate(String workspaceId, String projectId, MultipartFile file) {
        log.info("operation log {} : import promptTemplate", projectId);
        if (!FileUtil.validateFileType(file, FILE_TYPE_EXCEL)) {
            throw new AgentStudioException(StudioError.FILE_CONTENT_TYPE_IS_UNMATCHED, Arrays.asList(file
                    .getContentType(), FILE_TYPE_EXCEL.getFileType()));
        }
        FileUtil.validateFile(file, FILE_TYPE_EXCEL);
        // 校验是否为admin用户
        SimpleUser userInfo = RequestContextUtils.getRequestUser();
        if (!Strings.CS.equals(userInfo.getDomainName(), adminName)) {
            log.error("only admin tenant can operate preset template");
            throw new AgentStudioException(StudioError.AUTH_FAILED);
        }
        List<String> message;
        try (InputStream in = file.getInputStream()) {
            message = processExcel(in, userInfo, projectId, workspaceId, true);
        } catch (Exception e) {
            log.error("Failed to upload file [{}]", file.getOriginalFilename(), e);
            throw new AgentStudioException(StudioError.UPLOAD_FILE_FAILED);
        }
        return message;
    }

    @RedisRateLimit
    @Override
    public List<String> importPromptTemplateV2(String workspaceId, String projectId, MultipartFile file) {
        log.info("operation log {} : import promptTemplate V2", projectId);
        if (!FileUtil.validateFileType(file, FILE_TYPE_EXCEL)) {
            throw new AgentStudioException(StudioError.FILE_CONTENT_TYPE_IS_UNMATCHED,
                file.getContentType(), FILE_TYPE_EXCEL.getFileType());
        }
        FileUtil.validateFile(file, FILE_TYPE_EXCEL);
        // 校验是否为admin用户
        SimpleUser userInfo = RequestContextUtils.getRequestUser();

        List<String> message;
        try (InputStream in = file.getInputStream()) {
            message = processExcel(in, userInfo, projectId, workspaceId, false);
        } catch (Exception e) {
            log.error("Failed to upload file [{}]", file.getOriginalFilename(), e);
            throw new AgentStudioException(StudioError.UPLOAD_FILE_FAILED);
        }
        return message;
    }

    private List<String> processExcel(InputStream in, SimpleUser userInfo, String projectId, String workspaceId, boolean isV1) throws IOException {
        log.info("Processing Excel file - ProjectId: {}, WorkspaceId: {}, IsV1: {}", projectId, workspaceId, isV1);

        // 初始化监听器（仅解析第一个Sheet）
        DynamicExcelListener listener = new DynamicExcelListener();

        // 核心：仅读取第一个Sheet（索引0）
        EasyExcel.read(in, listener)
            .sheet(0) // 固定读取第一个Sheet（索引从0开始）
            .headRowNumber(1) // 表头在第一行
            .doRead();

        // 返回第一个Sheet的解析结果
        Map<Integer, String> headerMap = listener.getHeaderMap();

        checkHeaderRow(headerMap);

        List<TemplateOneRow> allRows = listener.getRowDataList();

        List<TemplateOneRow> templates = allRows.stream()
                .filter(Objects::nonNull)
                .collect(Collectors.toList());
        log.info("Parsed {} valid rows from Excel", templates.size());

        Map<String, String> tagNameAndIdLookup = tagNameAndIdLookup(workspaceId);
        Map<String, String> industryNameAndIdLookup = industryNameAndIdLookup(workspaceId);

        // 校验所有数据
        List<String> message = checkAllRow(templates, tagNameAndIdLookup, industryNameAndIdLookup, projectId, workspaceId, isV1);
        log.info("Validation completed with {} messages", message.size());

        Iterator<TemplateOneRow> iterator = templates.iterator();
        ArrayList<ManualPePromptTemplateDto> manualPePromptTemplateDtos = new ArrayList<>();
        String source = null;
        if (Strings.CS.equals(userInfo.getDomainName(), adminName)) {
            source = Source.PRESET.toString();
        } else {
            source = Source.NO_SOURCE.toString();
        }

        while (iterator.hasNext()) {
            TemplateOneRow next = iterator.next();
            String tag = next.getTag();
            List<String> tagIds;
            if (StringUtils.isBlank(tag)) {
                tagIds = Collections.emptyList();
            } else {
                tagIds = Arrays.stream(tag.split(","))
                    .map(e -> tagNameAndIdLookup.getOrDefault(e, ""))
                    .collect(Collectors.toList());
            }

            ManualPePromptTemplateDto manualPePromptTemplateDto = new ManualPePromptTemplateDto();
            manualPePromptTemplateDto.setName(next.getTemplateName());
            manualPePromptTemplateDto.setContent(next.getContent());
            manualPePromptTemplateDto.setDescription(next.getDescription());
            manualPePromptTemplateDto.setIndustryId(industryNameAndIdLookup.getOrDefault(next.getIndustry(), ""));
            manualPePromptTemplateDto.setTagList(tagIds);
            manualPePromptTemplateDto.setSource(source);
            manualPePromptTemplateDtos.add(manualPePromptTemplateDto);
        }

        List<PePromptTemplate> pePromptTemplates = new ArrayList<>();
        String name = userInfo.getUserName();
        manualPePromptTemplateDtos.forEach(item -> {
            PePromptTemplate pePromptTemplate = PePromptTemplate.convertToPePromptTemplate(item);
            pePromptTemplate.setCreator(name);
            pePromptTemplate.setUpdater(name);
            pePromptTemplate.setWorkspaceId(workspaceId);
            pePromptTemplate.setDomainId(RequestContextUtils.getRequestUserDomainId());
            pePromptTemplates.add(pePromptTemplate);
        });

        conversionTransaction.batchInsertTemplate(pePromptTemplates, projectId);
        log.info("Batch insert completed for {} templates", pePromptTemplates.size());

        return message;

    }

    private void checkHeaderRow(Map<Integer, String> headerRow) {
        log.info("Validating Excel header row");

        try {
            for (TemplateImportEnum item : TemplateImportEnum.values()) {
                int index = item.getIndex();
                String expectedColumn;
                if (EN_LANGUAGE.equals(HttpUtil.getLanguage())) {
                    expectedColumn = item.getColumnEn();
                } else {
                    expectedColumn = item.getColumn();
                }

                String actualColumn = headerRow.get(index);

                if (!Objects.equals(expectedColumn, actualColumn)) {
                    log.warn("Header mismatch at index {} - Expected: {}, Actual: {}", index, expectedColumn, actualColumn);
                    throw new AgentStudioException(StudioError.EXCEL_HEADER_ERROR);
                }
            }

            log.info("Excel header row validated successfully");
        } catch (Exception e) {
            log.error("Failed to validate Excel header row", e);
            throw new AgentStudioException(StudioError.EXCEL_HEADER_ERROR);
        }
    }

    private List<String> checkAllRow(List<TemplateOneRow> templates, Map<String, String> tagNameAndIdLookup,
         Map<String, String> industryNameAndIdLookup, String projectId, String workspaceId, boolean isV1) {

        // 有不符合校验的返回相应的内容
        List<String> messages = new ArrayList<>();
        II18nHandler i18nHandler = new ExcelI18nHandler(messageSource);
        // 校验一次性导入是否满足不超过100个提示词，总的数量是否超过500个
        int currentTemplateCount = pePromptTemplateMapper.countPresetTemplateByProjectId(projectId, workspaceId);
        int totalExceedMax = Math.subtractExact(templateQuota, currentTemplateCount);
        int maxImportNum = (totalExceedMax < 0 || templateImportQuota < 0)
            ? 0
            : Math.min(totalExceedMax, templateImportQuota);
        if (templates.size() > maxImportNum) {
            IntStream.range(maxImportNum, templates.size())
                .forEach(index -> messages.add(MessageFormat.format(i18nHandler.getLocaleName(
                    ROWS_EXCEED_LIMIT), maxImportNum, index)));

            // 压缩List到合适的大小
            ListIterator<TemplateOneRow> iterator = templates.listIterator(templates.size());
            while (iterator.hasPrevious()) {
                int currentIndex = iterator.previousIndex();
                if (currentIndex >= maxImportNum) {
                    iterator.previous();
                    iterator.remove();
                } else {
                    break;
                }
            }
        }

        // 模板名称校验
        List<String> templateNames = templates.stream()
            .filter(Objects::nonNull)
            .map(TemplateOneRow::getTemplateName)
            .collect(Collectors.collectingAndThen(Collectors.toList(), ArrayList::new));
        HashSet<Integer> removeIndex = new HashSet<>();
        HashSet<String> templateNameSet = new HashSet<>();

        for (int i = 0; i < templateNames.size(); i++) {
            String templateName = templateNames.get(i);

            // 校验重复模板名称
            if (!templateNameSet.add(templateName)) {
                messages.add(MessageFormat.format(i18nHandler.getLocaleName(PROMPT_NAME_DUPLICATE), templateName, i));
                removeIndex.add(i);
            }

            // 输入的模板名称是否合法
            if (!TEMPLATE_NAME_PATTERN.matcher(templateName).matches()) {
                messages.add(MessageFormat.format(i18nHandler.getLocaleName(PROMPT_NAME_INVALID), templateName, i));
                removeIndex.add(i);
            }

            // 新增的模板名称和存量的有无重复
            List<String> storageNames = null;
            if (isV1) {
                storageNames = pePromptTemplateMapper.queryTemplateNameByName(templateNames, workspaceId);
            } else {
                storageNames = pePromptTemplateMapper.queryTemplateNameByNameV2(templateNames, projectId, workspaceId);
            }

            if (storageNames.contains(templateName)) {
                messages.add(MessageFormat.format(i18nHandler.getLocaleName(PROMPT_NAME_EXISTS), templateName, i));
                removeIndex.add(i);
            }

            // 模板内容超过4000个字符时，异常报错信息需要优化
            String thisContent = templates.get(i).getContent();
            if (StringUtils.length(thisContent) > promptContentMaxLength) {
                messages.add(MessageFormat.format(i18nHandler.getLocaleName(CONTENT_LENGTH_EXCEED), thisContent.length(), promptContentMaxLength, i));
                removeIndex.add(i);
            }

            // 行业为必填
            String thisIndustry = templates.get(i).getIndustry();
            if (StringUtils.isEmpty(industryNameAndIdLookup.getOrDefault(thisIndustry, ""))) {
                messages.add(MessageFormat.format(i18nHandler.getLocaleName(INDUSTRY_NOT_FOUND), thisIndustry, i));
                removeIndex.add(i);
            }

            // 校验标签是否存在
            String tag = templates.get(i).getTag();
            if (StringUtils.isBlank(tag)) {
                continue;
            }
            List<String> tagList = Arrays.stream(tag.split(",")).distinct().toList();
            List<String> notExistTag = tagList.stream()
                .filter(e -> StringUtils.isEmpty(tagNameAndIdLookup.getOrDefault(e, "")))
                .collect(Collectors.toList());
            if (CollectionUtils.isNotEmpty(notExistTag)) {
                messages.add(MessageFormat.format(i18nHandler.getLocaleName(TAG_NOT_FOUND), tag, i));
                removeIndex.add(i);
            }
        }
        ListIterator<Integer> iterator = new ArrayList<>(removeIndex).listIterator(removeIndex.size());
        while (iterator.hasPrevious()) {
            int currentIndex = iterator.previous();
            templates.remove(currentIndex);
        }
        return messages;
    }

    private TemplateOneRow parseOneRow(Row data) {
        if (isRowEmpty(data)) {
            return null;
        }
        TemplateOneRow oneRow = new TemplateOneRow();
        oneRow.setTemplateName(getCellStringOrNull(data, TemplateImportEnum.TEMPLATE_NAME.getIndex()));
        oneRow.setContent(getCellStringOrNull(data, TemplateImportEnum.CONTENT.getIndex()));
        oneRow.setDescription(getCellStringOrNull(data, TemplateImportEnum.DESCRIPTION.getIndex()));
        oneRow.setTag(getCellStringOrNull(data, TemplateImportEnum.TAG.getIndex()));
        oneRow.setIndustry(getCellStringOrNull(data, TemplateImportEnum.INDUSTRY.getIndex()));
        oneRow.setVars(getCellStringOrNull(data, TemplateImportEnum.VARIABLE.getIndex()));
        return oneRow;
    }

    private boolean isRowEmpty(Row row) {
        for (int i = 0; i < TemplateImportEnum.values().length; i++) {
            Cell cell = row.getCell(i);
            if (cell != null && cell.getCellType() != CellType.BLANK) {
                return false;
            }
        }
        return true;
    }

    private String getCellStringOrNull(Row data, int cellIdx) {
        Cell cell = data.getCell(cellIdx);
        if (null == cell) {
            return "";
        } else {
            return new DataFormatter().formatCellValue(cell);
        }
    }

    private Map<String, String> tagNameAndIdLookup(String workspaceId) {
        return tagMapper.queryAll().stream().collect(Collectors.toMap(PeTag::getName, PeTag::getId, (k1, k2) -> k1));
    }

    private Map<String, String> industryNameAndIdLookup(String workspaceId) {
        return industryMapper.queryAll()
                .stream()
                .collect(Collectors.toMap(Industry::getName, Industry::getId, (k1, k2) -> k1));
    }
}
