/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.service.v2;

import com.alibaba.fastjson.JSON;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.pagehelper.PageInfo;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.prompt.engineering.dto.BaseInfo;
import com.openjiuwen.studio.prompt.engineering.dto.ListEvalDataSetQo;
import com.openjiuwen.studio.prompt.engineering.dto.PromptBaseResp;
import com.openjiuwen.studio.prompt.engineering.dto.PromptEvalDataItem;
import com.openjiuwen.studio.prompt.engineering.entity.v2.PromptTaskDetailVo;
import com.openjiuwen.studio.prompt.engineering.entity.v2.PromptTaskEntity;
import com.openjiuwen.studio.prompt.engineering.entity.v2.PromptVar;
import com.openjiuwen.studio.prompt.engineering.enums.v2.PtTypeEnum;
import com.openjiuwen.studio.prompt.engineering.mapper.v2.PromptTaskMapper;
import com.openjiuwen.studio.prompt.engineering.service.IPromptEngineerDataSetService;
import com.openjiuwen.studio.prompt.engineering.service.PromptObsService;
import com.openjiuwen.studio.prompt.engineering.service.v2.fileparser.DataSetFileParser;
import com.openjiuwen.studio.prompt.engineering.utils.PromptDataSetUtil;

import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.io.FilenameUtils;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;
import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.MalformedURLException;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

@Slf4j
@Service
public class PromptEngineerDataSetService implements IPromptEngineerDataSetService {

    private static final String MULTI_JSON_FILE_PATH = "template/prompt/prompt_sample_multi.json";

    private static final String TEXT_JSON_FILE_PATH = "template/prompt/prompt_sample_text.json";

    private static final String PIC_FILE_PATH = "";

    private static final String MULTI_EXCEL_FILE_PATH = "template/prompt/prompt_sample_multi.xlsx";

    private static final String TEXT_EXCEL_FILE_PATH = "template/prompt/prompt_sample_text.xlsx";

    private static final String EVAL_DATA_PATH = "EvalData/%s/%s/%s/%s.json";

    private static final String EVAL_DATA_PREFIX = "EvalData/%s/%s/%s/";

    private static final String EVAL_PICTURE_PATH = "EvalData/%s/%s/%s/picture/%s";

    private static final String EVAL_PICTURE_ROOT_PATH = "EvalData/%s/%s/%s/picture/";

    private static final String EVAL_PICTURE_PREFIX = "EvalData/%s/%s/%s/picture/([^/?]+)";

    @Autowired
    private PromptObsService obsService;

    @Autowired
    private PromptTaskMapper promptTaskMapper;

    @Value("${prompt.tempurl.time: 2592000}") // 一个月
    private long EXPIRE_TIME;

    @Value("${prompt.evaldata.size: 500}")
    private int DATA_MAX_SIZE;

    @Value("${prompt.evaldata.vars.num: 20}")
    private int VARS_NUM;

    @Value("${prompt.evaldata.vars.namelength: 50}")
    private int VARS_NAME_LENGTH;

    @Value("${prompt.evaldata.vars.contentlength: 2000}")
    private int VARS_CONTENT_LENGTH;

    @Value("${prompt.evaldata.vars.picturesize: 10}")
    private int PICTURE_SIZE;

    @Autowired
    private I18nUtil i18nUtil;

    @jakarta.annotation.Resource
    private HttpServletResponse response;

    private Map<String, DataSetFileParser> strategyMap = new ConcurrentHashMap<>();

    public PromptEngineerDataSetService(List<DataSetFileParser> parserList) {
        // 初始化策略缓存
        if (CollectionUtils.isEmpty(parserList)) {
            return;
        }
        for (DataSetFileParser parser : parserList) {
            for (String type : parser.type().split(";")) {
                strategyMap.put(type, parser);
            }
        }
    }

    @Override
    public BaseInfo importEvalDataSetItems(String workspaceId, String projectId, String taskId, MultipartFile file) {
        validTaskId(projectId, workspaceId, taskId);    // 校验taskId存在
        log.info("operation log {}: start to import EvalData file", projectId);
        List<List<PromptVar>> promptVarsList = null;
        List<PromptEvalDataItem> promptEvalDataItemList = new ArrayList<>();

        String obsFilePath = String.format(EVAL_DATA_PATH, projectId, workspaceId, taskId, taskId); // 构造目标路径
        if (obsService.isExistObsFile(obsFilePath)) {   // 追加
            promptEvalDataItemList.addAll(getPromptEvalData(obsFilePath));
        }
        try {
            // 判断是excel、json、还是zip包
            String ext = FilenameUtils.getExtension(file.getOriginalFilename());
            if (!strategyMap.containsKey(ext)) {
                throw new AgentStudioException(StudioError.PROMPT_DATA_TYPE_ERROR);
            }
            promptVarsList = strategyMap.get(ext)
                .parseData(file, getVarsConfig(taskId, projectId, workspaceId), projectId, workspaceId, taskId,
                    DATA_MAX_SIZE - promptEvalDataItemList.size());

            for (List<PromptVar> promptVars : promptVarsList) {
                PromptEvalDataItem promptEvalDataItem = new PromptEvalDataItem();
                promptEvalDataItem.setId(UUID.randomUUID().toString());
                promptEvalDataItem.setContent(JsonUtils.toJson(promptVars));
                promptEvalDataItemList.add(promptEvalDataItem);
            }
            obsService.uploadObsFile(obsFilePath, JSON.toJSONString(promptEvalDataItemList), -1);
            return new BaseInfo().setCode(200).setMessage("success");
        } catch (AgentStudioException agentStudioException) {
            return new BaseInfo().setCode(400).setMessage(i18nUtil.getMessage(agentStudioException).getMessage());
        }
    }


    @Override
    public Resource downloadEvalDataSetTemplate(String projectId, String workspaceId, String ptType) {
        log.info("operation log {} : Start to download template.", projectId);
        try (OutputStream outputStream = response.getOutputStream()) {
            // 设置响应头
            response.setContentType("application/zip");
            String zipFileName = "template.zip";
            String encodedFileName = URLEncoder.encode(zipFileName, StandardCharsets.UTF_8).replace("+", "%20");
            response.setHeader("Content-Disposition",
                "attachment; filename=\"" + zipFileName + "\"; filename*=UTF-8''" + encodedFileName);

            byte[] zipBytes = buildZipContent(ptType);

            outputStream.write(zipBytes);
            outputStream.flush();

        } catch (Exception e) {
            log.error("Download template failed. projectId: {}, workspaceId: {}", projectId, workspaceId,
                e); // 补充上下文和堆栈
            throw new AgentStudioException(StudioError.DOWNLOAD_TEMPLATE_FAILED);
        }
        return null;
    }


    @Override
    public BaseInfo addSingleEvalDataSetItem(String projectId, String taskId, String workspaceId,
        PromptEvalDataItem body) {
        log.info("operation log {} : Start to add single EvalData item.", projectId);
        validTaskId(projectId, workspaceId, taskId);    // 校验taskId存在
        validItemContent(body.getContent());
        // 去除无效内容
        String content = clearInvalidVars(body.getContent(), projectId, workspaceId, taskId);
        body.setContent(content);

        String obsFilePath = String.format(EVAL_DATA_PATH, projectId, workspaceId, taskId, taskId); // 构造目标路径
        body.setId(UUID.randomUUID().toString());
        List<PromptEvalDataItem> promptEvalDataItemList = new LinkedList<>();
        if (obsService.isExistObsFile(obsFilePath)) {   // 追加
            promptEvalDataItemList = getPromptEvalData(obsFilePath);
            if (promptEvalDataItemList.size() >= DATA_MAX_SIZE) {
                log.error("eval data item size is more than {} !", DATA_MAX_SIZE);
                throw new AgentStudioException(StudioError.DATASET_NUMBER_LIMIT);
            }
        }
        promptEvalDataItemList.add(body);
        obsService.uploadObsFile(obsFilePath, JSON.toJSONString(promptEvalDataItemList), -1);
        return new BaseInfo().setId(body.getId()).setMessage("success");
    }


    @Override
    public BaseInfo addBatchEvalDataSetItem(String projectId, String taskId, String workspaceId,
        List<PromptEvalDataItem> body) {
        log.info("operation log {} : Start to add batch EvalData item.", projectId);
        if (CollectionUtils.isEmpty(body)) {
            log.error("batch eval item is empty !");
            throw new AgentStudioException(StudioError.UPLOAD_EVAL_DATA_FAILED);
        }
        if (body.size() > DATA_MAX_SIZE) {
            log.error("eval data item size is more than {} !", DATA_MAX_SIZE);
            throw new AgentStudioException(StudioError.DATASET_NUMBER_LIMIT);
        }
        for (PromptEvalDataItem item : body) {
            validItemContent(item.getContent());
            // 去除无效内容
            String content = clearInvalidVars(item.getContent(), projectId, workspaceId, taskId);
            item.setContent(content);
        }
        String obsFilePath = String.format(EVAL_DATA_PATH, projectId, workspaceId, taskId, taskId); // 构造目标路径

        List<PromptEvalDataItem> promptEvalDataItemList = new LinkedList<>();
        if (obsService.isExistObsFile(obsFilePath)) {   // 追加
            promptEvalDataItemList = getPromptEvalData(obsFilePath);
        }
        for (PromptEvalDataItem item : body) {
            item.setId(UUID.randomUUID().toString());
            promptEvalDataItemList.add(item);
        }
        if (promptEvalDataItemList.size() >= DATA_MAX_SIZE) {
            log.error("eval data item size is more than {} !", DATA_MAX_SIZE);
            throw new AgentStudioException(StudioError.DATASET_NUMBER_LIMIT);
        }
        obsService.uploadObsFile(obsFilePath, JSON.toJSONString(promptEvalDataItemList), -1);

        return new BaseInfo().setMessage("success");
    }


    @Override
    public BaseInfo deleteEvalDataSetItem(String projectId, String taskId, String itemId, String workspaceId) {
        log.info("operation log {} : Start to delete EvalData item.", projectId);
        validTaskId(projectId, workspaceId, taskId); // 越权校验

        String obsFilePath = String.format(EVAL_DATA_PATH, projectId, workspaceId, taskId, taskId);
        List<PromptEvalDataItem> promptEvalDataItemList;
        if (obsService.isExistObsFile(obsFilePath)) {
            promptEvalDataItemList = getPromptEvalData(obsFilePath);
        } else {
            log.error("eval data not found in {}!", obsFilePath);
            throw new AgentStudioException(StudioError.PROMPT_EVAL_DATA_NOT_FOUND);
        }
        promptEvalDataItemList = promptEvalDataItemList.stream()
            .filter(promptEvalDataItem -> !itemId.equals(promptEvalDataItem.getId()))
            .toList();
        if (promptEvalDataItemList.isEmpty()) {
            obsService.deleteObsFile(obsFilePath);
        } else {
            obsService.uploadObsFile(obsFilePath, JSON.toJSONString(promptEvalDataItemList), -1);
        }
        return new BaseInfo().setMessage("success").setId(itemId);
    }


    @Override
    public PromptBaseResp listEvalDataSet(String projectId, String taskId, ListEvalDataSetQo listEvalDataSetQo) {
        log.info("operation log {} : Start to query EvalData.", projectId);
        // 1. 越权校验
        validTaskId(projectId, listEvalDataSetQo.getWorkspaceId(), taskId);

        // 2. 构造目标路径
        String obsFilePath = String.format(EVAL_DATA_PATH, projectId, listEvalDataSetQo.getWorkspaceId(), taskId,
            taskId);

        // 3. 从对象存储中读取评估数据列表
        List<PromptEvalDataItem> promptEvalDataItemList;
        if (obsService.isExistObsFile(obsFilePath)) {
            promptEvalDataItemList = getPromptEvalData(obsFilePath);
        } else {
            log.error("eval data not found in {}!", obsFilePath);
            PageInfo<PromptEvalDataItem> resultPage = new PageInfo<>();
            resultPage.setTotal(0);
            resultPage.setPageNum(0);
            resultPage.setPageSize(listEvalDataSetQo.getPageSize());
            resultPage.setPages(0);
            log.info("query task's num:{}", resultPage.getTotal());
            return new PromptBaseResp().setCode(200).setMessage("success").setData(resultPage);
        }
        Collections.reverse(promptEvalDataItemList);
        // 4. 分页处理：跳过前面的数据，取当前页的数据
        AtomicBoolean needUpdate = new AtomicBoolean(false);
        List<PromptEvalDataItem> promptEvalDataItems = promptEvalDataItemList.stream()
            .skip((long) (listEvalDataSetQo.getPageNum() - 1) * listEvalDataSetQo.getPageSize())
            .limit(listEvalDataSetQo.getPageSize())
            .map(promptEvalDataItem -> {
                List<PromptVar> vars = JsonUtils.json2Obj(promptEvalDataItem.getContent(),
                    new TypeReference<List<PromptVar>>() { });
                needUpdate.set(isUpdateData(vars, projectId, listEvalDataSetQo.getWorkspaceId(), taskId));
                promptEvalDataItem.setContent(JsonUtils.toJson(vars));
                return promptEvalDataItem;
            })
            .toList();
        if (needUpdate.get()) {
            Collections.reverse(promptEvalDataItemList);
            // 更新data.json
            obsService.uploadObsFile(obsFilePath, JSON.toJSONString(promptEvalDataItemList), -1);
        }

        // 5. 构建分页对象
        PageInfo<PromptEvalDataItem> resultPage = new PageInfo<>(promptEvalDataItems);
        resultPage.setTotal(promptEvalDataItemList.size());
        resultPage.setPageNum(listEvalDataSetQo.getPageNum());
        resultPage.setPageSize(listEvalDataSetQo.getPageSize());
        resultPage.setPages((int) Math.ceil((double) promptEvalDataItemList.size() / listEvalDataSetQo.getPageSize()));

        log.info("query task's num:{}", resultPage.getTotal());
        return new PromptBaseResp().setCode(200).setMessage("success").setData(resultPage);
    }

    @Override
    public PromptEvalDataItem updateEvalDataSetItem(String projectId, String taskId, String itemId, String workspaceId,
        PromptEvalDataItem body) {
        log.info("operation log {} : Start to update EvalData item.", projectId);
        validTaskId(projectId, workspaceId, taskId);
        validItemContent(body.getContent());
        // 去除无效内容
        String content = clearInvalidVars(body.getContent(), projectId, workspaceId, taskId);
        body.setContent(content);

        // 构造目标路径
        String obsFilePath = String.format(EVAL_DATA_PATH, projectId, workspaceId, taskId, taskId);
        List<PromptEvalDataItem> promptEvalDataItemList;
        if (obsService.isExistObsFile(obsFilePath)) {
            promptEvalDataItemList = getPromptEvalData(obsFilePath);
        } else {
            log.error("eval data not found in {}!", obsFilePath);
            throw new AgentStudioException(StudioError.PROMPT_EVAL_DATA_NOT_FOUND);
        }

        List<PromptEvalDataItem> promptEvalDataItems = promptEvalDataItemList.stream().map(promptEvalDataItem -> {
            if (itemId.equals(promptEvalDataItem.getId())) {
                body.setId(itemId);
                return body;
            }
            return promptEvalDataItem;
        }).collect(Collectors.toList());

        obsService.uploadObsFile(obsFilePath, JSON.toJSONString(promptEvalDataItems), -1);
        return new PromptEvalDataItem().setId(itemId).setContent(body.getContent());
    }

    @Override
    public PromptBaseResp uploadPicture(String workspaceId, String projectId, String taskId, MultipartFile file) {
        log.info("operation log {} : Start to upload picture.", projectId);
        validTaskId(projectId, workspaceId, taskId);    // 校验taskId存在
        if (file.isEmpty() || !PromptDataSetUtil.isAllowedImage(file.getOriginalFilename())) {
            log.error("upload picture is empty or not allowed extension! file name: {}", file.getName());
            throw new AgentStudioException(StudioError.PROMPT_EVAL_DATA_FILE_ERROR);
        }

        if (file.getSize() / (1024 * 1024) > PICTURE_SIZE) {
            log.error("upload picture size is more than {}MB!, ignore upload", PICTURE_SIZE);
            throw new AgentStudioException(StudioError.PICTURE_SIZE_EXCEED, PICTURE_SIZE);
        }

        // 随机生成图片文件名
        String ext = FilenameUtils.getExtension(file.getOriginalFilename());
        String objectKey = String.format(EVAL_PICTURE_PATH, projectId, workspaceId, taskId,
            UUID.randomUUID().toString() + '.' + ext);
        try (InputStream inputStream = file.getInputStream()) {
            obsService.uploadObsFile(inputStream, objectKey);
        } catch (IOException e) {
            log.error("upload obs file failed, {}", e.getMessage());
            throw new AgentStudioException(StudioError.UPLOAD_FILE_TO_OBS_FAILED);
        }
        String tempUrl = obsService.getObsTempUrl(objectKey, EXPIRE_TIME);

        return new PromptBaseResp().setCode(200).setMessage("success").setData(tempUrl);
    }

    private List<PromptEvalDataItem> getPromptEvalData(String path) {
        String arrayContent = obsService.downloadObsFile(path);
        List<PromptEvalDataItem> promptEvalDataItemList = JsonUtils.json2Obj(arrayContent,
            new TypeReference<LinkedList<PromptEvalDataItem>>() { });
        if (promptEvalDataItemList == null) {
            log.error("eval item trans object failed !");
            throw new AgentStudioException(StudioError.UPLOAD_EVAL_DATA_FAILED);
        }
        return promptEvalDataItemList;
    }

    private void validItemContent(String content) {
        // 进一步验证 JSON 内容是否符合 List<PromptVar> 的结构
        // 30大约为变量类型字段的长度加一些转译符
        if (content.length() > (VARS_NAME_LENGTH + VARS_CONTENT_LENGTH + 30) * VARS_NUM) {
            log.error("eval item is too long !");
            throw new AgentStudioException(StudioError.JSON_CONTENT_LENGTH_EXCEED);
        }
        List<PromptVar> promptVarList = null;
        try {
            promptVarList = new ObjectMapper().readValue(content, new TypeReference<List<PromptVar>>() { });
        } catch (Exception e) {
            log.error("The JSON content format does not match the structure of List<PromptVar>.", e);
            throw new AgentStudioException(StudioError.UPLOAD_EVAL_DATA_FAILED);
        }
        validPromptVars(promptVarList);

    }

    public void deleteDateSet(PromptTaskDetailVo promptTaskDetailVo, String projectId, String workspaceId) {
        String deletePath = String.format(EVAL_DATA_PREFIX, projectId, workspaceId, promptTaskDetailVo.getId());
        obsService.deleteByPrefix(deletePath);
        log.info("delete eval data set success, path:{}", deletePath);
    }

    public void deleteDateSet(String id, String projectId, String workspaceId) {
        String deletePath = String.format(EVAL_DATA_PREFIX, projectId, workspaceId, id);
        if (obsService.isExistObsFile(deletePath)) {
            obsService.deleteByPrefix(deletePath);
            log.info("delete eval data set success, path:{}", deletePath);
        } else {
            log.info("eval data set not exist, path:{}", deletePath);
        }
    }

    public void validTaskId(String projectId, String workspaceId, String taskId) {
        // 校验taskId存在
        PromptTaskEntity promptTaskEntity = promptTaskMapper.selectByPrimaryKey(taskId, projectId, workspaceId);
        if (promptTaskEntity == null) {
            log.error("The task ID to be deleted does not exist. id:{}", taskId);
            throw new AgentStudioException(StudioError.OPTIMIZATION_TASK_ID_IS_NOT_EXIST);
        }
    }

    public List<List<PromptVar>> getAllEvalDataSet(String taskId, String projectId, String workspaceId) {
        // 越权校验
        validTaskId(projectId, workspaceId, taskId);
        // 构造目标路径
        String obsFilePath = String.format(EVAL_DATA_PATH, projectId, workspaceId, taskId, taskId);
        List<PromptEvalDataItem> promptEvalDataItemList;
        if (obsService.isExistObsFile(obsFilePath)) {
            promptEvalDataItemList = getPromptEvalData(obsFilePath);
        } else {
            log.error("eval data not found in {}!", obsFilePath);
            throw new AgentStudioException(StudioError.PROMPT_EVAL_DATA_NOT_FOUND);
        }
        AtomicBoolean needUpdate = new AtomicBoolean(false);
        List<List<PromptVar>> promptEvalDataItems = promptEvalDataItemList.stream().map(promptEvalDataItem -> {
            List<PromptVar> vars = JsonUtils.json2Obj(promptEvalDataItem.getContent(),
                new TypeReference<List<PromptVar>>() { });
            needUpdate.set(isUpdateData(vars, projectId, workspaceId, taskId));
            promptEvalDataItem.setContent(JsonUtils.toJson(vars));
            return vars;
        }).collect(Collectors.toCollection(ArrayList::new));

        if (needUpdate.get()) {
            // 更新data.json
            obsService.uploadObsFile(obsFilePath, JSON.toJSONString(promptEvalDataItemList), -1);
        }
        return promptEvalDataItems;
    }

    private boolean isUpdateData(List<PromptVar> vars, String projectId, String workspaceId, String taskId) {
        Pattern imagePattern = Pattern.compile(String.format(EVAL_PICTURE_PREFIX, projectId, workspaceId, taskId));
        boolean needUpdate = false;
        Map<String, PromptVar> varConfigMap = getVarsConfig(taskId, projectId, workspaceId);

        for (PromptVar promptVar : vars) {
            // 多模态图片判断是否过期
            try {
                if (varConfigMap.containsKey(promptVar.getName())
                    && varConfigMap.get(promptVar.getName()).getType() == PtTypeEnum.MULTI && isTempUrlExpire(
                    promptVar.getContent())) {
                    Matcher matcher = imagePattern.matcher(promptVar.getContent());
                    if (matcher.find()) {
                        // 第一个分组即为图片名（([^/?]+)捕获的内容）
                        String fileName = matcher.group(1);
                        String tempUrl = obsService.getObsTempUrl(
                            String.format(EVAL_PICTURE_PATH, projectId, workspaceId, taskId, fileName), EXPIRE_TIME);
                        promptVar.setContent(tempUrl);
                        needUpdate = true;
                    }
                }
            } catch (Exception e) {
                log.error("occur error when judge picture is expire !, {}", e.getMessage());
            }
        }
        return needUpdate;
    }

    public boolean isTempUrlExpire(String tempUrl) {
        try {
            URL url = new URL(tempUrl);

            // 解析查询参数
            Map<String, String> params = parseQueryParams(url.getQuery());

            // 检查是否包含Expires参数
            if (!params.containsKey("Expires") || !params.containsKey("AccessKeyId") || !params.containsKey(
                "Signature")) {
                return false;
            }

            // 解析Expires时间戳
            try {
                long expires = Long.parseLong(params.get("Expires"));
                // 对比当前时间（秒级时间戳）
                long currentTime = System.currentTimeMillis() / 1000;
                return currentTime > expires;
            } catch (NumberFormatException e) {
                return false;
            }
        } catch (MalformedURLException e) {
            // URL格式错误
            return false;
        }
    }

    /**
     * 解析查询参数为键值对
     */
    private Map<String, String> parseQueryParams(String query) {
        Map<String, String> params = new HashMap<>();
        String[] pairs = query.split("&");
        for (String pair : pairs) {
            int eqIndex = pair.indexOf('=');
            if (eqIndex != -1 && eqIndex < pair.length() - 1) {
                String key = pair.substring(0, eqIndex);
                String value = pair.substring(eqIndex + 1);
                params.put(key, value);
            }
        }
        return params;
    }

    // 构建 ZIP 文件内容
    public byte[] buildZipContent(String ptType) {
        ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();

        try (ZipOutputStream zipOutputStream = new ZipOutputStream(byteArrayOutputStream)) {

            String jsonPath = PtTypeEnum.TEXT.toString().equals(ptType) ? TEXT_JSON_FILE_PATH : MULTI_JSON_FILE_PATH;
            String excelPath = PtTypeEnum.TEXT.toString().equals(ptType) ? TEXT_EXCEL_FILE_PATH : MULTI_EXCEL_FILE_PATH;
            // 1. 添加 data.json 文件（原有逻辑）
            addFileToZip(zipOutputStream, jsonPath, "data.json");
            // 2. 新增：添加Excel文件到ZIP包
            addFileToZip(zipOutputStream, excelPath, "data.xlsx");
            if (PtTypeEnum.MULTI.toString().equals(ptType)) {
                // 3. 添加 picture/1.png 到 picture/4.png（原有逻辑）
                addPictureFilesToZip(zipOutputStream);
            }
        } catch (IOException e) {
            log.error("build zip file template failed, reason is {}", e.getMessage());
            throw new AgentStudioException(StudioError.DOWNLOAD_TEMPLATE_FAILED);
        }

        return byteArrayOutputStream.toByteArray();
    }

    public void copyObsFile(String projectId, String workspaceId, String oldTaskId, String newTaskId) {

        // 上传图片
        String oldPicPath = String.format(EVAL_PICTURE_ROOT_PATH, projectId, workspaceId, oldTaskId);
        List<String> picturePaths = obsService.listObjectKeys(oldPicPath);
        for (String picturePath : picturePaths) {
            String fileName = FilenameUtils.getName(picturePath);
            String newPicPath = String.format(EVAL_PICTURE_PATH, projectId, workspaceId, newTaskId, fileName);
            obsService.copyFile(picturePath, newPicPath);
        }
        // 上传data.json
        String oldObsPath = String.format(EVAL_DATA_PATH, projectId, workspaceId, oldTaskId, oldTaskId);
        String newObsPath = String.format(EVAL_DATA_PATH, projectId, workspaceId, newTaskId, newTaskId);

        Map<String, PromptVar> varConfigMap = getVarsConfig(oldTaskId, projectId, workspaceId);

        List<PromptEvalDataItem> promptEvalDataItemList;
        if (obsService.isExistObsFile(oldObsPath)) {
            promptEvalDataItemList = getPromptEvalData(oldObsPath);
            // 更新promptEvalDataItemList多模的内容，因为图片路径改变了
            Pattern imagePattern = Pattern.compile(
                String.format(EVAL_PICTURE_PREFIX, projectId, workspaceId, oldTaskId));
            for (PromptEvalDataItem promptEvalDataItem : promptEvalDataItemList) {
                List<PromptVar> promptVars = JsonUtils.json2Obj(promptEvalDataItem.getContent(),
                    new TypeReference<List<PromptVar>>() { });
                for (PromptVar promptVar : promptVars) {
                    if (varConfigMap.containsKey(promptVar.getName())
                        && varConfigMap.get(promptVar.getName()).getType() == PtTypeEnum.MULTI) {
                        Matcher matcher = imagePattern.matcher(promptVar.getContent());
                        if (matcher.find()) {
                            // 第一个分组即为图片名（([^/?]+)捕获的内容）
                            String fileName = matcher.group(1);
                            String tempUrl = obsService.getObsTempUrl(
                                String.format(EVAL_PICTURE_PATH, projectId, workspaceId, newTaskId, fileName),
                                EXPIRE_TIME);
                            promptVar.setContent(tempUrl);
                        }
                    }
                }
                promptEvalDataItem.setContent(JSON.toJSONString(promptVars));
            }
        } else {
            log.error("eval data not found in {}!", oldObsPath);
            throw new AgentStudioException(StudioError.PROMPT_EVAL_DATA_NOT_FOUND);
        }
        obsService.uploadObsFile(newObsPath, JSON.toJSONString(promptEvalDataItemList), -1);
    }

    private void validPromptVars(List<PromptVar> promptVars) {
        if (!CollectionUtils.isEmpty(promptVars)) {
            if (promptVars.size() > VARS_NUM) {
                log.error("prompt var nums is invalid");
                throw new AgentStudioException(StudioError.VARS_NUM_EXCEED, VARS_NUM);
            }
            Set<String> varNamesSet = new HashSet<>();
            for (PromptVar promptVar : promptVars) {
                if (StringUtils.isEmpty(promptVar.getContent())
                    || promptVar.getContent().length() > VARS_CONTENT_LENGTH) {
                    log.error("prompt var content length is invalid");
                    throw new AgentStudioException(StudioError.VARS_CONTENT_LENGTH_EXCEED, VARS_CONTENT_LENGTH);
                }
                if (StringUtils.isEmpty(promptVar.getName()) || promptVar.getName().length() > VARS_NAME_LENGTH) {
                    log.error("prompt var is invalid");
                    throw new AgentStudioException(StudioError.VARS_NAME_LENGTH_EXCEED, VARS_NAME_LENGTH);
                }
                // 重名校验
                if (varNamesSet.contains(promptVar.getName())) {
                    log.error("prompt var name is Duplicate");
                    throw new AgentStudioException(StudioError.VARS_NAME_DUPLICATE, promptVar.getName());
                }
                varNamesSet.add(promptVar.getName());
            }
        } else {
            log.error("prompt var is invalid");
            throw new AgentStudioException(StudioError.UPLOAD_EVAL_DATA_FAILED);
        }
    }

    Map<String, PromptVar> getVarsConfig(String taskId, String projectId, String workspaceId) {
        PromptTaskDetailVo promptTaskDetailVo = promptTaskMapper.selectByPrimaryKey(taskId, projectId, workspaceId)
            .convert2PromptTaskDetailVo();

        Map<String, PromptVar> varConfigMap = new HashMap<>();
        if (!CollectionUtils.isEmpty(promptTaskDetailVo.getPtVars())) {
            varConfigMap = promptTaskDetailVo.getPtVars()
                .stream()
                .collect(Collectors.toMap(PromptVar::getName, var -> var));
        }
        return varConfigMap;
    }

    private String clearInvalidVars(String content, String projectId, String workspaceId, String taskId) {
        Map<String, PromptVar> varConfigMap = getVarsConfig(taskId, projectId, workspaceId);
        List<PromptVar> promptVarList = null;
        try {
            promptVarList = new ObjectMapper().readValue(content, new TypeReference<List<PromptVar>>() { });
        } catch (Exception e) {
            log.error("The JSON content format does not match the structure of List<PromptVar>.", e);
            throw new AgentStudioException(StudioError.UPLOAD_EVAL_DATA_FAILED);
        }
        List<PromptVar> tempVars = new ArrayList<>();
        for (PromptVar promptVar : promptVarList) {
            if (varConfigMap.containsKey(promptVar.getName())) {
                tempVars.add(promptVar);
            }
        }
        return JSON.toJSONString(tempVars);
    }

    /**
     * 新增：添加File文件到ZIP
     */
    private void addFileToZip(ZipOutputStream zipOutputStream, String path, String fileName) throws IOException {
        // 读取resources中的Excel文件
        Resource resource = new ClassPathResource(path);
        if (!resource.exists()) {
            log.error("file not found! Path: {}", path);
            throw new AgentStudioException(StudioError.TEMPLATE_FILE_NOT_FOUND);
        }

        // 定义Excel在ZIP中的路径和文件名（可自定义，比如直接根目录或子目录）
        ZipEntry excelEntry = new ZipEntry(fileName);

        zipOutputStream.putNextEntry(excelEntry);

        // 读取Excel文件内容并写入ZIP
        try (InputStream inputStream = resource.getInputStream()) {
            byte[] buffer = new byte[4096]; // 增大缓冲区提升效率
            int bytesRead;
            while ((bytesRead = inputStream.read(buffer)) != -1) {
                zipOutputStream.write(buffer, 0, bytesRead);
            }
        }

        zipOutputStream.closeEntry();
        log.info("file added to zip successfully: {}", path);
    }

    /**
     * 原有逻辑：添加图片文件（抽离为独立方法，便于维护）
     */
    private void addPictureFilesToZip(ZipOutputStream zipOutputStream) throws IOException {
        Resource imageResource = new ClassPathResource(PIC_FILE_PATH);
        if (!imageResource.exists()) {
            throw new AgentStudioException(StudioError.TEMPLATE_FILE_NOT_FOUND);
        }

        try (InputStream inputStream = imageResource.getInputStream()) {
            byte[] imageBytes = inputStream.readAllBytes();

            for (int i = 1; i <= 4; i++) {
                ZipEntry imageEntry = new ZipEntry("picture/" + i + ".png");
                zipOutputStream.putNextEntry(imageEntry);
                zipOutputStream.write(imageBytes);
                zipOutputStream.closeEntry();
            }
        }
    }

}
