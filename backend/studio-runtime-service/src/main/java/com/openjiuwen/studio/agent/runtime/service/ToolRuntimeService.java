/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.runtime.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.dto.run.RunToolRequestBody;
import com.openjiuwen.studio.agent.common.dto.tool.RunToolResponseBody;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.service.DelegateExchangeTokenService;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.common.utils.UrlCheckUtils;
import com.openjiuwen.studio.agent.runtime.config.FileConfig;
import com.openjiuwen.studio.agent.runtime.constant.Constant;
import com.openjiuwen.studio.agent.runtime.dto.AudioResult;
import com.openjiuwen.studio.agent.runtime.dto.Base64ToImageReq;
import com.openjiuwen.studio.agent.runtime.dto.OcrRecognizeRsp;
import com.openjiuwen.studio.agent.runtime.dto.OcrResultInfo;
import com.openjiuwen.studio.agent.runtime.dto.OcrResultInfoWordsBlockList;
import com.openjiuwen.studio.agent.runtime.dto.ResolveAudioFileInfo;
import com.openjiuwen.studio.agent.runtime.dto.ResolveAudioFileReq;
import com.openjiuwen.studio.agent.runtime.dto.ResolveAudioFileRsp;
import com.openjiuwen.studio.agent.runtime.dto.ResolveDocumentReq;
import com.openjiuwen.studio.agent.runtime.dto.ResolveDocumentRsp;
import com.openjiuwen.studio.agent.runtime.dto.ResolveDocumentRspData;
import com.openjiuwen.studio.agent.runtime.dto.ResolvePageInfo;
import com.openjiuwen.studio.agent.runtime.dto.ToBase64Rsp;
import com.openjiuwen.studio.agent.runtime.dto.ToImageRsp;
import com.openjiuwen.studio.agent.runtime.dto.Url2Base64Req;
import com.openjiuwen.studio.agent.runtime.dto.md.CustomIAMAuthInfo;
import com.openjiuwen.studio.agent.runtime.dto.md.HisIAMAuthInfo;
import com.openjiuwen.studio.agent.runtime.dto.md.SgovAuthInfo;
import com.openjiuwen.studio.agent.runtime.model.RequestResult;
import com.openjiuwen.studio.agent.runtime.rce.client.OCRClient;
import com.openjiuwen.studio.agent.runtime.rce.client.SISClient;
import com.openjiuwen.studio.agent.runtime.rce.client.UniFactoryClient;
import com.openjiuwen.studio.agent.runtime.rce.model.GetLASRJobResultRsp;
import com.openjiuwen.studio.agent.runtime.rce.model.SmartDocumentRecognizerReq;
import com.openjiuwen.studio.agent.runtime.rce.model.SmartDocumentRecognizerRsp;
import com.openjiuwen.studio.agent.runtime.rce.model.SubmitLASRJobReq;
import com.openjiuwen.studio.agent.runtime.rce.model.UniFactoryShowTaskRsp;
import com.openjiuwen.studio.agent.runtime.rce.model.UniFactoryUploadFileReq;
import com.openjiuwen.studio.agent.runtime.rce.model.UniFactoryUploadFileRsp;
import com.openjiuwen.studio.agent.runtime.service.plugin.PluginTransform;
import com.openjiuwen.studio.agent.runtime.service.plugin.impl.PluginCustomIAMAdapter;
import com.openjiuwen.studio.agent.runtime.service.plugin.impl.PluginHisIamAdapter;
import com.openjiuwen.studio.agent.runtime.service.plugin.impl.PluginHisSgovAdapter;
import com.openjiuwen.studio.agent.runtime.utils.CommonUtils;
import com.openjiuwen.studio.agent.runtime.utils.OkHttpUtils;

import inet.ipaddr.IPAddressString;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.Operation;
import io.swagger.v3.oas.models.PathItem;
import io.swagger.v3.oas.models.parameters.Parameter;
import io.swagger.v3.oas.models.security.SecurityScheme;
import io.swagger.v3.parser.OpenAPIV3Parser;
import io.swagger.v3.parser.core.models.SwaggerParseResult;
import jodd.util.StringUtil;
import lombok.SneakyThrows;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.MapUtils;
import org.apache.commons.io.FilenameUtils;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.core.io.Resource;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.scheduling.TaskScheduler;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.MalformedURLException;
import java.net.URI;
import java.net.URISyntaxException;
import java.net.URL;
import java.net.UnknownHostException;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * 预置插件运行态service
 *
 */
@Slf4j
@Service
public class ToolRuntimeService implements IToolRuntimeService {
    /**
     * 接口测试OBS临时目录
     */
    public static final String TOOL_TEST_OBS_PATH = "temp/tools/openapi";

    /**
     * base64转图片OBS路径
     */
    public static final String BASE64_IMAGE_OBS_PATH = "Image";

    /**
     * 用于提取文件名的正则表达式
     */
    private static final Pattern FILE_NAME_PATTERN = Pattern.compile(".+/([^/?]+)(\\?.+)?$");

    /**
     * 本地部署OCR服务project_id占位
     */
    public static final String OCR_PROJECT_ID = "123";

    /**
     * UniFactory接口预留字段
     */
    private static final String DEFAULT_APP_ID = "123";

    /**
     * 音频识别通用模型特征串
     */
    private static final String CHINESE_8K_GENERAL = "chinese_8k_general";

    /**
     * 加密的字段，例如apikey鉴权的秘钥，返回前端******
     */
    public static final String ENCRYPTED_VALUE = "******";

    /**
     * 支持的图片格式
     */
    private static final String[] SUPPORTED_IMAGE_TYPES = {
            "image/jpeg", "image/jpg", "image/png", "image/gif",
            "image/bmp", "image/webp", "image/svg+xml", "image/tiff"
    };

    /**
     * 预置插件前缀
     */
    private static final String PRESET = "preset_";

    public static final long IMAGE_FILE_SIZE = 10L * 1024 * 1024;

    @Autowired
    private ObsService obsService;

    @Autowired
    private OkHttpUtils okHttpUtils;

    @Autowired
    private OCRClient ocrClient;

    @Autowired
    private SISClient sisClient;

    @Autowired
    private UniFactoryClient uniFactoryClient;

    @Autowired
    private TaskScheduler taskScheduler;

    @Autowired
    private DelegateExchangeTokenService delegateExchangeTokenService;

    @Autowired
    private UrlCheckUtils urlCheckUtils;

    @Autowired
    private PluginTransform pluginTransform;

    @Autowired
    private PluginHisIamAdapter pluginHisIamAdapter;

    @Autowired
    private PluginHisSgovAdapter pluginHisSgovAdapter;

    @Autowired
    private PluginCustomIAMAdapter pluginCustomIAMAdapter;

    @Value("${tool.request.max-image-size}")
    private  long imageFileSize;

    @Value("${agent.max-resolve-file-number}")
    private int maxResolveFileNumber;

    @Value("${storage.expires:7}")
    private int obsExpireTime;

    @Value("${env.type}")
    private String envType;

    @Value("${op.svc.project-id}")
    private String opProjectId;

    @Value("${tool.request.timeout}")
    private int toolRequestTimeout;

    @Value("${workflow.connector_config_host_blacklist}")
    private String connectorConfigHostBlacklist;

    @Value("#{'${workflow.connector_config_host_whitelist}'.split(',')}")
    private Set<String> connectorConfigHostWhitelist;

    @Value("${tool.url.enable-check}")
    private boolean enableUrlCheck;

    @Value("${isHcs:false}")
    private boolean isHcs;

    @Value("${knowledge.lakeSearch.authorization:}")
    private String authValue;

    /**
     * 从URL中提取文件名
     *
     * @param fileUrl 文件URL
     * @return 文件名
     */
    public static String extractFileName(String fileUrl) {
        Matcher matcher = FILE_NAME_PATTERN.matcher(fileUrl);
        if (matcher.find()) {
            return matcher.group(1); // 返回第一个捕获组的内容
        }
        return ""; // 如果没有匹配到，返回空字符串
    }

    /**
     * host 合法性检查
     *
     * @param swaggerUrl 调用url
     * @param hostBlackList 连接器host黑名单
     */
    public void checkSwaggerUrlValid(String swaggerUrl, String hostBlackList) {
        log.info("Start: check url {} from black list.", swaggerUrl);
        if (hostBlackList.isEmpty()) {
            return;
        }
        Set<String> connectorHostBlackList = Arrays.stream(hostBlackList.split(","))
                .map(String::trim)
                .collect(Collectors.toSet());
        if (!enableUrlCheck) {
            log.info("not check from black list");
            return;
        }
        try {
            URL url = new URL(swaggerUrl);
            String host = url.getHost();
            checkHostValid(host, connectorHostBlackList);
            try {
                InetAddress[] addresses = InetAddress.getAllByName(host);
                for (InetAddress address : addresses) {
                    checkHostValid(address.getHostAddress(), connectorHostBlackList);
                }
            } catch (UnknownHostException e) {
                // 不做控制，运行态DNS一样，有问题会调不通，没有影响
                log.warn("swagger base url is Unknown Host: {}", host);
            }
        } catch (MalformedURLException e) {
            throw new AgentStudioException(StudioError.INVALID_URL);
        } catch (Exception e) {
            // 捕获其他异常，防止程序崩溃
            log.error("Error while checking swagger URL: {}", swaggerUrl, e);
            throw new AgentStudioException(StudioError.INVALID_URL);
        }
        log.info("End: check url from black list.");
    }

    /**
     * host 合法性检查
     *
     * @param host host
     * @param connectorHostBlackList 连接器host黑名单
     */
    private static void checkHostValid(String host, Set<String> connectorHostBlackList) {
        // 判断host是否在黑名单中
        if (connectorHostBlackList.contains(host)) {
            log.warn("checkHostValid failed, host: {}", host);
            throw new AgentStudioException(StudioError.INVALID_URL);
        }

        // 判断网段
        try {
            IPAddressString hostAddress = new IPAddressString(host);
            for (String ips : connectorHostBlackList) {
                if (StringUtils.isEmpty(ips)) continue;
                try {
                    IPAddressString ipAddress = new IPAddressString(ips);
                    if (ipAddress.contains(hostAddress) || host.contains(ips)) {
                        log.warn("checkHostValid failed, ipAddress:{}, hostAddress: {}, host: {}, ips:{}", ipAddress,
                                hostAddress, host, ips);
                        throw new AgentStudioException(StudioError.INVALID_URL);
                    }
                } catch (IllegalArgumentException e) {
                    // 忽略非法的IP格式
                    log.warn("Invalid IP format in blacklist: {}", ips);
                }
            }
        } catch (IllegalArgumentException e) {
            // host 不是合法的IP地址，可能是域名，不进行网段判断
            log.warn("Host is not a valid IP address, skip subnet check: {}", host);
        }
    }

    private String processNestedStructure(String rawJson) {
        log.info("Start processing JSON: {}", rawJson);

        JSONObject root = JSON.parseObject(rawJson);
        log.info("Parsed JSON: {}", root.toJSONString());

        // 遍历 JSON 中的所有字段
        for (String key : root.keySet()) {
            Object value = root.get(key);

            // 如果值是数组
            if (value instanceof JSONArray) {
                JSONArray outerArray = (JSONArray) value;

                // 遍历数组中的每个对象
                for (Object item : outerArray) {
                    if (item instanceof JSONObject) {
                        JSONObject innerObj = (JSONObject) item;

                        // 如果对象中也有同名字段
                        if (innerObj.containsKey(key)) {
                            Object innerValue = innerObj.get(key);

                            // 替换最外层的字段值为内层的值
                            root.put(key, innerValue);
                            log.info("Replaced outer field '{}' with inner value", key);
                            break;
                        }
                    }
                }
            }

            // 如果值是对象
            else if (value instanceof JSONObject) {
                JSONObject innerObj = (JSONObject) value;

                // 如果对象中也有同名字段
                if (innerObj.containsKey(key)) {
                    Object innerValue = innerObj.get(key);

                    // 替换最外层的字段值为内层的值
                    root.put(key, innerValue);
                    log.info("Replaced outer field '{}' with inner value", key);
                }
            }
        }

        String newJson = root.toJSONString();
        log.info("Processed JSON result: {}", newJson);

        return newJson;
    }


    @Override
    public RunToolResponseBody runTool(String projectId, RunToolRequestBody body) {
        // 插件调测
        log.info("[runTool] operation log {}: start to run tool", projectId);
        String toolId = body.getToolObsKey();
        String pluginId = toolId.split("#")[0];
        body.setParameter(processNestedStructure(body.getParameter()));
        log.info("[runTool] start to run, pluginId {}, toolId {} ", pluginId, toolId);
        JSONObject requestBody = JSON.parseObject(body.getParameter());
        log.info("[runTool] get requestBody {}", requestBody);

        if (requestBody == null) {
            log.error("[runTool] parse json object failed: {}", body.getParameter());
            throw new AgentStudioException(StudioError.METHOD_ARGUMENT_NOT_VALID);
        }
        // 下载OBS文件
        String objectKey = String.format("%s/%s.json", TOOL_TEST_OBS_PATH, toolId);
        String openapiJson = obsService.downloadObsFile(objectKey);
        log.info("[runTool] download openapi json success, start to parse file");

        // 解析openapi文件
        SwaggerParseResult parseResult = new OpenAPIV3Parser().readContents(openapiJson);
        // 检查解析错误，当前OBS路径上的openapi为管理面生成，后续解析过程不做强非空校验；若改为读取用户上传，需要进行强校验
        if (parseResult.getMessages() != null) {
            parseResult.getMessages().forEach(s -> log.warn("[runTool] parse open api error message, msg={}", s));
        }
        OpenAPI openAPI = parseResult.getOpenAPI();

        // 获取第一个path
        Optional<PathItem> optionalPathItem = openAPI.getPaths().values().stream().findFirst();
        if (optionalPathItem.isEmpty()) {
            log.error("[runTool] open api path is empty");
            throw new AgentStudioException(StudioError.OPEN_API_PARSE_FAILED, "open api path is empty");
        }

        // 解析Method
        Operation operation;
        OkHttpUtils.Method method;
        if (optionalPathItem.get().getPost() != null) {
            operation = optionalPathItem.get().getPost();
            method = OkHttpUtils.Method.POST;
        } else if (optionalPathItem.get().getGet() != null) {
            operation = optionalPathItem.get().getGet();
            method = OkHttpUtils.Method.GET;
        } else {
            log.error("[runTool] method is supported.");
            throw new AgentStudioException(StudioError.OPEN_API_PARSE_FAILED);
        }

        // 解析Parameters
        Map<String, String> urlParamsMap = new HashMap<>();
        Map<String, String> pathParams = new HashMap<>();
        Map<String, String> headers = new HashMap<>();
        parseParams(operation, requestBody, urlParamsMap, headers, pathParams);
        log.info("[runTool] pathParams parse to {}", pathParams);

        // 构造鉴权信息，用于前端展示的信息返回ENCRYPTED_VALUE
        Map<String, String> urlParamsEncrypted = new HashMap<>();
        urlParamsEncrypted.putAll(urlParamsMap);

        Map<String, String> headersEncrypted = new HashMap<>(headers);
        buildEncryptParams(projectId, openAPI, urlParamsMap, urlParamsEncrypted, headers, headersEncrypted);

        // 构造请求url
        String url = operation.getServers().get(0).getUrl();

        // 替换url占位符
        log.info("[runTool] before url replace: {}", url);
        for (Map.Entry<String, String> entry : pathParams.entrySet()) {
            String key = entry.getKey();
            String value = entry.getValue();
            url = url.replaceAll("\\{" + key + "\\}", Matcher.quoteReplacement(value));
        }
        log.info("[runTool] after url replace: {}", url);

        // 如果是预置插件就不做黑名单网段IP校验
        log.info("[runTool] plugin is preset ? {}", pluginId.startsWith(PRESET));
        log.info("[runTool] plugin in whitelist ? {}", connectorConfigHostWhitelist.contains(pluginId));

        if (!pluginId.startsWith(PRESET) && !connectorConfigHostWhitelist.contains(pluginId)) {
            checkSwaggerUrlValid(url, connectorConfigHostBlacklist);
        }

        urlCheckUtils.checkUrl(projectId, url);
        String urlShown = url;
        if (MapUtils.isNotEmpty(urlParamsMap)) {
            StringBuilder sb = new StringBuilder(urlShown);
            sb.append("?");
            urlParamsEncrypted.forEach((k, v) -> {
                sb.append(String.format("%s=%s&", k, v));
            });
            urlShown = sb.toString().substring(0, sb.toString().length() - 1);
        }
        // 发送请求
        log.info("[runTool] open api file parse success, start to make request {}", urlShown);

        // 构造请求体
        String requestBodyJson;
        if (operation.getRequestBody() != null && Boolean.parseBoolean(
                getExtensionValue(operation.getRequestBody().getExtensions(), Constant.OpenAPI.X_ARRAY_ENCAPSULATION))) {
            // 外层封装为数组，原始接口的返回在测试接口时不再解封
            JSONArray jsonArray = new JSONArray();
            jsonArray.add(requestBody);
            requestBodyJson = JSON.toJSONString(jsonArray);
        } else {
            requestBodyJson = JSON.toJSONString(requestBody);
        }

        RequestResult requestResult;
        // 区分json和form-data
        log.info("[runTool] Handling {} request.", headers.get(Constant.CONTENT_TYPE));
        if (StringUtil.equals(headers.get(Constant.CONTENT_TYPE), Constant.MULTIPART_FORM_DATA)) {
            Map<String, String> formParams = new HashMap<>();
            Map<String, MultipartFile> fileParams = new HashMap<>();
            // 下载url数据
            for (String key : requestBody.keySet()) {
                String value = requestBody.getString(key);
                MultipartFile file = downloadFileAsMultipartFile(value);
                if(file != null) {
                    fileParams.put(key, file);
                } else {
                    formParams.put(key, value);
                }
            }
            requestResult = okHttpUtils.callFormData(url, method, headers, urlParamsMap, formParams, fileParams);
        } else {
            requestResult = okHttpUtils.call(url, method, headers, urlParamsMap, requestBodyJson);
        }
        log.info("[runTool] call tool finished, return code {}", requestResult.getCode());

        // 构造工具测试响应结果
        return new RunToolResponseBody().setRawRequestUrl(urlShown)
                .setRawRequestHeaders(headersEncrypted)
                .setRawRequestBody(requestBodyJson)
                .setRawResponse(requestResult.getResponse())
                .setRawResponseCode(requestResult.getCode())
                // 逻辑失败有两种情况，一种为返回非200，一种为接口异常；当前工具测试第二种情况算失败
                .setSuccess(StringUtils.isEmpty(requestResult.getExceptionMessage()))
                .setErrorMessage(requestResult.getExceptionMessage());
    }

    /**
     * 从指定URL下载文件并转换为MultipartFile对象
     *
     * @param fileUrl 文件下载地址
     * @return MultipartFile对象
     */
    @SneakyThrows
    public MultipartFile downloadFileAsMultipartFile(String fileUrl) {
        long startTime = System.currentTimeMillis();
        InputStream inputStream = obsService.getByUrl(fileUrl);
        ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
        try {
            // 将输入流读取到字节数组
            byte[] buffer = new byte[1024];
            int length;
            while ((length = inputStream.read(buffer)) != -1) {
                outputStream.write(buffer, 0, length);
            }
            byte[] fileBytes = outputStream.toByteArray();

            // 创建MultipartFile对象
            String fileName = extractFileName(fileUrl); // 从 URL 中提取文件名
            log.info("downloadFileAsMultipartFile:{}, cost: {} ms", fileUrl, System.currentTimeMillis() - startTime);
            return new MockMultipartFile(fileName, fileName, "application/octet-stream", fileBytes);
        } finally {
            closeResources(inputStream, outputStream);
        }
    }

    /**
     * 关闭资源
     */
    private void closeResources(InputStream inputStream, OutputStream outputStream) {
        if (inputStream != null) {
            try {
                inputStream.close();
            } catch (IOException e) {
                log.warn("Failed to close the input stream", e);
            }
        }

        if (outputStream != null) {
            try {
                outputStream.close();
            } catch (IOException e) {
                log.warn("Failed to close the output stream", e);
            }
        }
    }

    private void buildEncryptParams(String projectId, OpenAPI openAPI, Map<String, String> urlParams,
                                    Map<String, String> urlParamsEncrypted, Map<String, String> headers, Map<String, String> headersEncrypted) {
        if (openAPI.getComponents() == null)
            return;
        for (Map.Entry<String, SecurityScheme> entry : openAPI.getComponents().getSecuritySchemes().entrySet()) {
            if (Constant.OpenAPI.API_KEY.equals(entry.getKey())) {
                SecurityScheme securityScheme = entry.getValue();
                if (StringUtils.isBlank(getExtensionValue(securityScheme.getExtensions(), Constant.OpenAPI.X_VALUE))) {
                    log.info("The AuthInfo of the OP account has been cleared; skipping SCC decryption.");
                    return;
                }
                String value = CryptoUtils
                    .decrypt(getExtensionValue(securityScheme.getExtensions(), Constant.OpenAPI.X_VALUE));
                switch (securityScheme.getIn()) {
                    case QUERY -> {
                        urlParams.put(securityScheme.getName(), value);
                        urlParamsEncrypted.put(securityScheme.getName(), ENCRYPTED_VALUE);
                    }
                    case HEADER -> {
                        headers.put(securityScheme.getName(), value);
                        headersEncrypted.put(securityScheme.getName(), ENCRYPTED_VALUE);
                    }
                }
            } else if (Constant.OpenAPI.HIS_IAM.equals(entry.getKey())) {
                SecurityScheme securityScheme = entry.getValue();
                HisIAMAuthInfo hisIAMAuthInfo = pluginTransform.transformAuthInfo2HisIAMAuthInfo(securityScheme);
                pluginHisIamAdapter.requestHeaderHandler(hisIAMAuthInfo, headers);
                headersEncrypted.put(Constant.X_AUTH_TOKEN, ENCRYPTED_VALUE);
            } else if (Constant.OpenAPI.HIS_SGOV.equals(entry.getKey())) {
                SecurityScheme securityScheme = entry.getValue();
                SgovAuthInfo sgovAuthInfo = pluginTransform.transformAuthInfo2SgovAuthInfo(securityScheme);
                pluginHisSgovAdapter.requestHeaderHandler(sgovAuthInfo, headers);
                headersEncrypted.put(Constant.X_AUTH_TOKEN, ENCRYPTED_VALUE);
            } else if (Constant.OpenAPI.CUSTOM_IAM.equals(entry.getKey())) {
                SecurityScheme securityScheme = entry.getValue();
                CustomIAMAuthInfo customIAMAuthInfo = pluginTransform.transformAuthInfo2CustomIAMAuthInfo(securityScheme);
                pluginCustomIAMAdapter.requestHeaderHandler(customIAMAuthInfo, headers);
                headersEncrypted.put(Constant.X_AUTH_TOKEN, ENCRYPTED_VALUE);
            }
        }
    }

    private void parseParams(Operation operation, JSONObject requestBody, Map<String, String> urlParams,
                             Map<String, String> headers, Map<String, String> pathParams) {
        for (Parameter parameter : operation.getParameters()) {
            String parameterName = parameter.getName();

            if (Constant.OpenAPI.IN_QUERY.equals(parameter.getIn()) && requestBody.containsKey(parameter.getName())) {
                // 提取urlParameter
                String queryValue = StringUtils.defaultString(requestBody.getString(parameterName));
                // 将queryParam从请求体中移除
                requestBody.remove(parameterName);
                urlParams.put(parameterName, queryValue);
            } else if (Constant.OpenAPI.IN_HEADER.equals(parameter.getIn())) {
                // 提取headerParameter，先从自定义字段获取header的值（已加密）
                String headerValue = getExtensionValue(parameter.getExtensions(), Constant.OpenAPI.X_VALUE);
                if (StringUtils.isNotEmpty(headerValue)) {
                    headers.put(parameterName, CryptoUtils.decrypt(headerValue));
                    continue;
                }
                // 如果取不到，则从请求体中获取
                headerValue = requestBody.getString(parameterName);
                if (StringUtils.isNotEmpty(headerValue)) {
                    headers.put(parameterName, headerValue);
                    // 将headerParam从请求体中移除
                    requestBody.remove(parameterName);
                }
            } else if (Constant.OpenAPI.IN_PATH.equals(parameter.getIn())) {
                // 提取pathParameter
                if (operation.getServers().get(0).getUrl().contains("{" + parameterName + "}")
                        && StringUtils.isNotEmpty(requestBody.getString(parameterName))) {
                    pathParams.put(parameterName, requestBody.getString(parameterName));
                }
                // 将pathParam从请求体中移除
                requestBody.remove(parameterName);
            }
        }
    }

    /**
     * @param body body
     * @return
     */
    @Override
    public ToImageRsp base64ToImage(Base64ToImageReq body) {
        ToImageRsp response = new ToImageRsp();

        try {
            // 1. 参数校验
            if (body == null) {
                response.setSuccess(false);
                response.setMessage("The request body cannot be empty.");
                return response;
            }

            String base64Data = body.getBase64();
            String mimeType = body.getMimetype(); // 必须提供MIME类型

            if (StringUtils.isBlank(base64Data)) {
                response.setSuccess(false);
                response.setMessage("The Base64 data cannot be empty.");
                return response;
            }

            if (StringUtils.isBlank(mimeType)) {
                response.setSuccess(false);
                response.setMessage("The MIME type of the target image is not provided.");
                return response;
            }

            // 清理输入
            base64Data = base64Data.trim();
            mimeType = mimeType.trim();
            mimeType = normalizeMimeType(mimeType);

            // 2. 验证MIME类型是否为图片格式
            if (!isSupportedImageType(mimeType)) {
                response.setSuccess(false);
                response.setMessage("The image format is not supported.");
                return response;
            }

            // 3. 如果输入看起来像Data URL，给出警告或拒绝处理
            if (base64Data.startsWith("data:")) {
                // 或者可以选择提取Base64部分
                int commaIndex = base64Data.indexOf(',');
                if (commaIndex > 0) {
                    base64Data = base64Data.substring(commaIndex + 1);
                } else {
                    response.setSuccess(false);
                    response.setMessage("The data URL format is incorrect.");
                    return response;
                }
            }

            // 4. 清理Base64字符串（移除换行符和空格）
            String cleanBase64 = base64Data.replaceAll("\\s+", "");

            // 5. 解码Base64
            byte[] imageBytes;
            try {
                imageBytes = Base64.getDecoder().decode(cleanBase64);
            } catch (IllegalArgumentException e) {
                response.setSuccess(false);
                response.setMessage("Base64 decoding failed: " + e.getMessage() +
                        ", Please ensure that an effective Base64-encoded string is provided.");
                return response;
            }

            // 6. 验证文件大小
            long maxSize = 10L * 1024 * 1024; // 10MB
            if (imageBytes.length > maxSize) {
                response.setSuccess(false);
                response.setMessage("The image size exceeds the 10 MB limit.");
                return response;
            }

            // 7. 验证图片有效性（根据提供的MIME类型）
            if (!isValidImage(imageBytes, mimeType)) {
                response.setSuccess(false);
                response.setMessage("The file is not a valid image or does not match the provided MIME type: " + mimeType + ".");
                return response;
            }
            // 8. 生成文件名（包含时间戳和随机数，避免冲突）
            String fileExtension = mimeType.split("/")[1];
            String fileName = generateFileName(fileExtension);

            // 9. 上传到OBS,获取下载链接
            try {
                ByteArrayInputStream inputStream = new ByteArrayInputStream(imageBytes);
                String objectKey = String.format("%s/%s", BASE64_IMAGE_OBS_PATH, fileName);
                String path =
                        obsService.putObjectToBucket(obsService.getStagingBucket(), objectKey, inputStream, obsExpireTime);
                String obsUrl = obsService.getStagingDownloadUrl(path, 3600L);

                // 10. 构建成功响应
                response.setSuccess(true);
                response.setImage(imageBytes);
                response.setMessage("Uploaded to OBS successfully !");
                response.setUrl(obsUrl);
                response.setMimetype(mimeType);
                response.setFilesize((long) imageBytes.length);
                response.setPath(path);
            } catch (AgentStudioException e) {
                response.setSuccess(false);
                response.setMessage("OBS upload failed.：" + e.getMessage());
            }
        } catch (Exception e) {
            response.setSuccess(false);
            response.setMessage("The conversion process is abnormal.：" + e.getMessage());
        }
        return response;
    }


    /**
     * 生成文件名
     */
    private String generateFileName(String extension) {
        // 格式：images/年/月/日/UUID.扩展名
        String datePath = java.time.LocalDate.now().format(java.time.format.DateTimeFormatter.ofPattern("yyyy/MM/dd"));
        String uuid = UUID.randomUUID().toString().replace("-", "");
        return String.format("images/%s/%s.%s", datePath, uuid, extension);
    }

    /**
     * 验证是否支持的图片类型
     */
    private boolean isSupportedImageType(String mimeType) {
        if (mimeType == null) {
            return false;
        }

        // 标准化MIME类型
        String normalized = normalizeMimeType(mimeType);

        for (String supportedType : SUPPORTED_IMAGE_TYPES) {
            if (supportedType.equalsIgnoreCase(normalized)) {
                return true;
            }
        }
        return false;
    }

    /**
     * 标准化MIME类型
     */
    private String normalizeMimeType(String mimeType) {
        if (mimeType == null) {
            return null;
        }

        String normalized = mimeType.toLowerCase(Locale.ROOT).trim();

        // 移除参数部分
        if (normalized.contains(";")) {
            normalized = normalized.substring(0, normalized.indexOf(';'));
        }

        // 处理别名
        return switch (normalized) {
            case "jpg", "jpeg" -> "image/jpeg";
            case "png" -> "image/png";
            case "gif" -> "image/gif";
            case "bmp" -> "image/bmp";
            case "webp" -> "image/webp";
            case "svg" -> "image/svg+xml";
            case "tif", "tiff" -> "image/tiff";
            default -> {
                // 确保以image/开头
                if (!normalized.startsWith("image/")) {
                    normalized = "image/" + normalized;
                }
                yield normalized;
            }
        };
    }


    /**
     * 验证图片有效性
     */
    private boolean isValidImage(byte[] data, String mimeType) {
        if (data == null || data.length < 4) {
            return false;
        }

        String normalized = normalizeMimeType(mimeType);

        try {
            return switch (normalized) {
                case "image/png" -> isValidPng(data);
                case "image/jpeg" -> isValidJpeg(data);
                case "image/gif" -> isValidGif(data);
                case "image/bmp" -> isValidBmp(data);
                case "image/webp" -> isValidWebp(data);
                case "image/svg+xml" -> isValidSvg(data);
                case "image/tiff" -> isValidTiff(data);
                default -> true;
            };
        } catch (Exception e) {
            return false;
        }
    }

    private boolean isValidPng(byte[] data) {
        return data.length >= 8 &&
                data[0] == (byte) 0x89 && data[1] == (byte) 0x50 &&
                data[2] == (byte) 0x4E && data[3] == (byte) 0x47 &&
                data[4] == (byte) 0x0D && data[5] == (byte) 0x0A &&
                data[6] == (byte) 0x1A && data[7] == (byte) 0x0A;
    }

    private boolean isValidJpeg(byte[] data) {
        return data[0] == (byte) 0xFF && data[1] == (byte) 0xD8 && data[2] == (byte) 0xFF;
    }

    private boolean isValidGif(byte[] data) {
        return data.length >= 6 &&
                data[0] == (byte) 0x47 && data[1] == (byte) 0x49 &&
                data[2] == (byte) 0x46 && data[3] == (byte) 0x38 &&
                (data[4] == (byte) 0x37 || data[4] == (byte) 0x39) &&
                data[5] == (byte) 0x61;
    }

    private boolean isValidBmp(byte[] data) {
        return data[0] == (byte) 0x42 && data[1] == (byte) 0x4D;
    }

    private boolean isValidWebp(byte[] data) {
        return data.length >= 12 &&
                data[0] == (byte) 0x52 && data[1] == (byte) 0x49 &&
                data[2] == (byte) 0x46 && data[3] == (byte) 0x46 &&
                data[8] == (byte) 0x57 && data[9] == (byte) 0x45 &&
                data[10] == (byte) 0x42 && data[11] == (byte) 0x50;
    }

    private boolean isValidSvg(byte[] data) {
        try {
            String content = new String(data, 0, Math.min(data.length, 500), "UTF-8");
            return content.toLowerCase(Locale.ROOT).contains("<svg");
        } catch (Exception e) {
            return false;
        }
    }

    private boolean isValidTiff(byte[] data) {
        return data[0] == (byte) 0x49 && data[1] == (byte) 0x49 || data[0] == (byte) 0x4D && data[1] == (byte) 0x4D;
    }

    /**
     * Url转为base64
     * @return
     */
    @Override
    public ToBase64Rsp url2Base64(Url2Base64Req body) {
        String url = body.getUrl();
        ToBase64Rsp response = new ToBase64Rsp();
        response.setSuccess(false);
        response.setMimetype("application/octet-stream");

        InputStream inputStream = null;
        ByteArrayOutputStream outputStream = null;
        byte[] buffer = new byte[4096];
        try {
            // 1. 参数校验
            if (url == null || url.trim().isEmpty()) {
                response.setSuccess(false);
                response.setMessage("URL cannot be empty.");
                return response;
            }
            checkSwaggerUrlValid(url, connectorConfigHostBlacklist);
            urlCheckUtils.checkUrl("projectId", url);

            // 2. 使用现有接口获取文件流
            inputStream = obsService.getByUrl(url);
            if (inputStream == null) {
                response.setSuccess(false);
                response.setMessage("Unable to obtain the file stream from the URL.");
                return response;
            }

            // 3. 从URL提取文件名和扩展名
            String fileName = extractFileNameFromUrl(url);
            if (StringUtils.isBlank(fileName)) {
                fileName = "image"; // 默认文件名
            }

            // 4. 将输入流读取到字节数组
            outputStream = new ByteArrayOutputStream();
            int bytesRead;
            long totalBytes = 0L;

            while ((bytesRead = inputStream.read(buffer)) != -1) {
                outputStream.write(buffer, 0, bytesRead);
                totalBytes += bytesRead;

                // 检查文件大小限制
                if (totalBytes > imageFileSize) {
                    response.setSuccess(false);
                    response.setMessage(("The file size exceeds:" + imageFileSize + "Byte."));
                    return response;
                }
            }

            byte[] imageBytes = outputStream.toByteArray();

            if (imageBytes.length == 0) {
                response.setSuccess(false);
                response.setMessage("The image content is empty.");
                return response;
            }

            // 5. 检查是否返回了错误信息（如XML错误页面）
            if (isErrorResponse(imageBytes)) {
                response.setSuccess(false);
                response.setMessage("The link is invalid or the request faild.");
                return response;
            }

            // 5. 创建MockMultipartFile
            // 如果无法从URL推断，则使用默认的application/octet-stream，在file2Base64中会检测
            // 先尝试从URL推断MIME类型，如果不确定，可以在file2Base64方法中再检测
            String mimeTypeFromUrl = inferMimeTypeFromUrl(url);
            if (StringUtils.isBlank(mimeTypeFromUrl)) {
                mimeTypeFromUrl = "application/octet-stream";
            }

            // MockMultipartFile的构造需要指定文件名，contentType（可选）
            MultipartFile multipartFile = new MockMultipartFile(
                    fileName,          // 文件名
                    fileName,          // 原始文件名
                    mimeTypeFromUrl,   // 内容类型
                    imageBytes              // 文件内容
            );

            // 6. 调用已有的file2Base64方法，传入从URL推断的MIME类型（如果为空，则使用multipartFile的contentType）
            return file2Base64(multipartFile, mimeTypeFromUrl, body.isIsDataUrl());
        } catch (IOException e) {
            response.setSuccess(false);
            response.setMessage("Failed to read the file.: " + e.getMessage());
            log.error("Failed to convert the file to Base64.", e);
        } catch (Exception e) {
            response.setSuccess(false);
            response.setMessage("Convert Exception occurred: " + e.getMessage());
            log.error("An exception occurred when the file was converted to Base64.", e);
        } finally {
            // 8. 关闭流
            closeResources(inputStream, outputStream);
        }
        return response;
    }

    /**
     * 检查是否返回了错误响应（如XML错误信息）
     */
    public boolean isErrorResponse(byte[] data) {
        if (data == null || data.length < 100) {
            return false;
        }

        try {
            // 将前200个字节转换为字符串进行检查
            int lengthToCheck = Math.min(data.length, 500);
            String content = new String(data, 0, lengthToCheck, StandardCharsets.UTF_8);

            // 检查是否是XML格式的错误信息
            if (isXmlError(content)) {
                return true;
            }

            // 检查是否是HTML错误页面
            if (isHtmlErrorPage(content)) {
                return true;
            }

            // 检查是否包含常见的错误关键词
            return containsErrorKeywords(content);

        } catch (Exception e) {
            // 如果转换失败，说明可能是二进制数据，不是错误文本
            return false;
        }
    }

    /**
     * 检查是否是XML错误
     */
    private boolean isXmlError(String content) {
        content = content.trim().toLowerCase(Locale.ROOT);

        // 检查是否是XML格式
        if (!content.startsWith("<?xml") && !content.startsWith("<error")) {
            return false;
        }

        // 检查是否包含常见的XML错误标签
        String[] errorTags = {
                "<error>", "<code>", "<message>", "<requestid>",
                "<hostid>", "<errormessage>", "<errorno>"
        };

        int errorTagCount = 0;
        for (String tag : errorTags) {
            if (content.contains(tag)) {
                errorTagCount++;
            }
        }

        // 如果包含多个错误相关的标签，很可能是错误响应
        return errorTagCount >= 2;
    }

    /**
     * 检查是否是HTML错误页面
     */
    private boolean isHtmlErrorPage(String content) {
        content = content.trim().toLowerCase(Locale.ROOT);

        // 检查是否是HTML
        if (!content.startsWith("<!doctype") && !content.startsWith("<html")) {
            return false;
        }

        // 检查是否包含错误相关的关键词
        String[] errorKeywords = {
                "error", "404", "not found", "forbidden", "unauthorized",
                "bad request", "internal server error", "service unavailable",
                "gateway timeout", "request timeout"
        };

        for (String keyword : errorKeywords) {
            if (content.contains(keyword)) {
                return true;
            }
        }

        return false;
    }

    /**
     * 检查是否包含常见的错误关键词
     */
    private boolean containsErrorKeywords(String content) {
        content = content.toLowerCase(Locale.ROOT);

        // 常见的错误关键词
        String[] errorKeywords = {
                "error", "exception", "failed", "failure", "invalid",
                "expired", "timeout", "deadline", "not found", "forbidden",
                "unauthorized", "bad request", "server error", "service unavailable"
        };

        for (String keyword : errorKeywords) {
            if (content.contains(keyword)) {
                return true;
            }
        }

        return false;
    }

    /**
     * 从URL中提取文件名
     */
    private String extractFileNameFromUrl(String url) {
        try {
            // 移除查询参数
            String path = new URL(url).getPath();
            if (path == null || path.isEmpty()) {
                return null;
            }

            // 获取最后一个斜杠后的部分
            int lastSlashIndex = path.lastIndexOf('/');
            if (lastSlashIndex >= 0 && lastSlashIndex < path.length() - 1) {
                return path.substring(lastSlashIndex + 1);
            }
            return null;
        } catch (Exception e) {
            log.warn("Failed to extract the file name from the URL", e);
            return null;
        }
    }

    /**
     * 从URL推断MIME类型（根据扩展名）
     */
    private String inferMimeTypeFromUrl(String url) {
        // 使用之前实现的方法
        return getMimeTypeFromExtension(extractFileExtension(url));
    }

    /**
     * 从URL提取文件扩展名
     */
    private String extractFileExtension(String url) {
        try {
            String path = new URL(url).getPath();
            if (path.contains(".")) {
                return path.substring(path.lastIndexOf('.') + 1).toLowerCase(Locale.ROOT);
            }
        } catch (Exception e) {
            log.warn("Failed to extract the file extension.", e);
        }
        return "";
    }


    /**
     * @param mimetype  mimetype
     * @param file      file
     * @param isDataUrl isDataUrl
     */
    @Override
    public ToBase64Rsp file2Base64(MultipartFile file, String mimetype, Boolean isDataUrl) {
        ToBase64Rsp response = new ToBase64Rsp();
        try {
            // 1. 参数校验
            if (file == null || file.isEmpty()) {
                response.setSuccess(false);
                response.setMessage("The file cannot be empty.");
                return response;
            }

            // 2. 获取文件信息
            String fileName = file.getOriginalFilename();
            long fileSize = file.getSize();

            // 3. 文件大小限制
            if (fileSize > imageFileSize) { // 3MB
                response.setSuccess(false);
                response.setMessage("The file size exceeds:" + imageFileSize + "Byte.");
                return response;
            }

            // 4. 获取实际的MIME类型（优先使用传入的，否则从文件获取）
            String actualMimeType = determineActualMimeType(mimetype, file, fileName);

            // 5. 验证是否为图片
            if (!isImageMimeType(actualMimeType)) {
                response.setSuccess(false);
                response.setMessage("Only image files are supported, mimeType should start with image/. Current file type:：" + (actualMimeType == null ? "Unknown" : actualMimeType));
                return response;
            }

            // 6. 转换为Base64
            byte[] fileBytes = file.getBytes();
            String base64String = Base64.getEncoder().encodeToString(fileBytes);

            //  验证图片有效性（
            if (!isValidImage(fileBytes, actualMimeType)) {
                response.setSuccess(false);
                response.setMessage("The file is not a valid image or does not match the provided MIME type: " + actualMimeType);
                return response;
            }
            // 7. 可以添加Data URL前缀
            String dataUrl = null;
            if (!StringUtils.isBlank(actualMimeType)) {
                dataUrl = "data:" + actualMimeType + ";base64," + base64String;
            }

            // 8. 设置返回结果
            // 或者使用dataUrl，根据需求
            if (isDataUrl != null && isDataUrl) {
                response.setBase64(dataUrl);
            } else {
                response.setBase64(base64String);
            }
            response.setMimetype(actualMimeType);
            response.setSuccess(true);
            response.setFilesize(fileSize);
            response.setMessage("The file is successfully converted to Base64.");

        } catch (IOException e) {
            response.setSuccess(false);
            response.setMessage("Failed to read the file.: " + e.getMessage());
            log.error("Failed to convert the file to Base64.", e);
        } catch (Exception e) {
            response.setSuccess(false);
            response.setMessage("Convert Exception occurred: " + e.getMessage());
            log.error("An exception occurred when the file was converted to Base64.", e);
        }
        return response;
    }

    // 验证是否为图片MIME类型
    private boolean isImageMimeType(String mimeType) {
        if (mimeType == null) {
            return false;
        }
        return mimeType.startsWith("image/");
    }

    private String determineActualMimeType(String providedMimeType, MultipartFile file, String fileName) {
        // 优先使用传入的MIME类型
        if (providedMimeType != null && !providedMimeType.trim().isEmpty() && providedMimeType.startsWith("image/")) {
            return providedMimeType.trim();
        }
        // 根据文件扩展名推断
        return inferMimeTypeFromFileName(fileName);
    }

    // 辅助方法：根据文件名推断MIME类型
    public String inferMimeTypeFromFileName(String fileName) {
        if (fileName == null) {
            return "application/octet-stream";
        }

        String extension = fileName.substring(fileName.lastIndexOf('.') + 1).toLowerCase(Locale.ROOT);
        return getMimeTypeFromExtension(extension);
    }

    // 辅助方法：根据扩展名获取MIME类型
    public String getMimeTypeFromExtension(String extension) {
        return switch (extension.toLowerCase(Locale.ROOT)) {
            case "jpg", "jpeg" -> "image/jpeg";
            case "png" -> "image/png";
            case "gif" -> "image/gif";
            case "bmp" -> "image/bmp";
            case "webp" -> "image/webp";
            case "svg" -> "image/svg+xml";
            default -> "application/octet-stream";
        };
    }

    /**
     * OCR识别插件
     *
     * @param body 请求参数
     * @return OcrRecognizeRsp OCR识别响应体
     */
    @Override
    public OcrRecognizeRsp ocrRecognize(ResolveDocumentReq body) {
        // urls校验
        checkUrlsSize(body.getUrls());

        // 对图片url逐个进行文字识别
        OcrRecognizeRsp ocrRecognizeRsp = new OcrRecognizeRsp();
        List<OcrResultInfo> ocrResultList =
                body.getUrls().stream().map(this::ocrRecognizeHandler).collect(Collectors.toList());
        log.info("ocr recognize succeed.");
        return ocrRecognizeRsp.setData(ocrResultList);
    }

    /**
     * 文档解析插件
     *
     * @param body 请求参数
     * @return ResolveDocumentRsp 解析结果响应体
     */
    @Override
    public ResolveDocumentRsp resolveDocument(ResolveDocumentReq body) {
        // urls数量校验
        checkUrlsSize(body.getUrls());

        // 对文件url逐个进行解析
        ResolveDocumentRsp resolveDocument = new ResolveDocumentRsp();
        List<ResolveDocumentRspData> data = body.getUrls()
                .stream()
                .map(url -> resolveDocumentHandler(url, body.isOcrEnabled()))
                .collect(Collectors.toList());
        log.info("resolve file completed.");
        return resolveDocument.setData(data);
    }

    @Override
    public ResolveAudioFileRsp resolveAudioFile(ResolveAudioFileReq body) {
        // urls校验
        checkUrlsSize(body.getUrls());

        // 对音频文件逐个进行识别
        ResolveAudioFileRsp resolveAudioFileRsp = new ResolveAudioFileRsp();
        List<ResolveAudioFileInfo> data = new ArrayList<>();
        for (String url : body.getUrls()) {
            // 构造提交音频文件识别任务请求体
            SubmitLASRJobReq.TranscriberConfig transcriber = new SubmitLASRJobReq.TranscriberConfig();
            transcriber.setAudioFormat(Constant.AUTO_MODE.toLowerCase(Locale.ROOT));
            transcriber.setProperty(CHINESE_8K_GENERAL);
            transcriber.setAddPunc(body.isAddPunc() ? "yes" : "no");
            transcriber.setDigitNorm(body.isDigitNorm() ? "yes" : "no");
            SubmitLASRJobReq submitLASRJobReqBody =
                    SubmitLASRJobReq.builder().dataUrl(url).config(transcriber).build();

            // 调用sis服务提交提交音频文件识别任务，获取任务id
            String jobId;
            try {
                jobId = sisClient.submitLASRJob("", opProjectId, submitLASRJobReqBody).getJobId();
            } catch (Exception e) {
                log.error("failed to submit asr job by sis.", e);
                throw new AgentStudioException(StudioError.RESOLVE_FILE_FAILED);
            }

            // 根据任务id获取识别结果
            ResolveAudioFileInfo resolveAudioFileInfo = resolveAudioFileHandler(jobId);
            data.add(resolveAudioFileInfo);
        }
        return resolveAudioFileRsp.setData(data);
    }

    /**
     * 获取音频识别异步任务的结果
     *
     * @param jobId 任务id
     * @return 识别结果
     */
    private ResolveAudioFileInfo resolveAudioFileHandler(String jobId) {
        // 用于在runnable中获取ScheduledFuture的引用来取消任务
        AtomicReference<ScheduledFuture<?>> scheduledFutureRef = new AtomicReference<>();

        // 阻塞主线程，在任务完成（解析成功/失败）时执行countDown()
        CountDownLatch countDownLatch = new CountDownLatch(1);
        ResolveAudioFileInfo resolveAudioFile = new ResolveAudioFileInfo();
        Runnable runnable = () -> {
            try {
                // 调用sis接口获取音频文件识别结果
                GetLASRJobResultRsp jobResult = sisClient.getLASRJobResult("", opProjectId, jobId);

                // 解析失败
                if (Constant.TaskStatus.ERROR.equalsIgnoreCase(jobResult.getStatus())) {
                    resolveAudioFile.setStatus(Constant.TaskStatus.ERROR.toLowerCase(Locale.ROOT));
                    resolveAudioFile.setErrorMessage(jobResult.getErrorMsg());
                    cancelTask(scheduledFutureRef.get());
                    countDownLatch.countDown();
                }

                // 解析成功，设置解析结果
                if (Constant.TaskStatus.FINISHED.equals(jobResult.getStatus())) {
                    List<GetLASRJobResultRsp.Segment> segments = jobResult.getSegments();
                    List<AudioResult> results = segments.stream().map(GetLASRJobResultRsp.Segment::getResult).toList();
                    resolveAudioFile.setStatus(Constant.TaskStatus.SUCCESS.toLowerCase(Locale.ROOT));
                    resolveAudioFile.setSegments(results);
                    cancelTask(scheduledFutureRef.get());
                    countDownLatch.countDown();
                }
            } catch (Exception e) {
                log.error("Resolve file failed.", e);
                resolveAudioFile.setStatus(Constant.TaskStatus.ERROR.toLowerCase(Locale.ROOT));
                resolveAudioFile.setErrorMessage("exception occurred while calling asr interface.");
                cancelTask(scheduledFutureRef.get());
                countDownLatch.countDown();
            }
        };
        ScheduledFuture<?> scheduledFuture = taskScheduler.scheduleAtFixedRate(runnable, Duration.ofMillis(500));
        scheduledFutureRef.set(scheduledFuture);

        try {
            // 获取解析结果
            boolean await = countDownLatch.await(toolRequestTimeout, TimeUnit.SECONDS);
            if (await) {
                return resolveAudioFile;
            } else {
                log.error("resolve audio file by asr interface timeout.");
                throw new AgentStudioException(StudioError.RESOLVE_FILE_FAILED);
            }
        } catch (InterruptedException e) {
            cancelTask(scheduledFutureRef.get());
            log.error("interrupted while resolving audio file.", e);
            throw new AgentStudioException(StudioError.RESOLVE_FILE_FAILED);
        }
    }

    /**
     * url数量校验
     *
     * @param urls url数组
     */
    private void checkUrlsSize(List<String> urls) {
        if (urls == null || urls.size() > maxResolveFileNumber) {
            log.error("Urls is null or exceed the max url number.");
            throw new AgentStudioException(StudioError.VALIDATE_RESOLVE_URLS_FAILED);
        }
    }

    /**
     * OCR识别单个文件
     *
     * @param url 文件url
     * @return OcrResultInfo 识别结果
     */
    private OcrResultInfo ocrRecognizeHandler(String url) {
        // 获取图片的Base64编码
        String base64Image;
        try (InputStream inputStream = obsService.getByUrl(url)) {
            byte[] byteArray = CommonUtils.toByteArray(inputStream);
            base64Image = Base64.getEncoder().encodeToString(byteArray);
        } catch (Exception e) {
            log.error("Failed to encoding image to base64.", e);
            throw new AgentStudioException(StudioError.IMAGE_TO_BASE64_FAILED);
        }

        // 调用OCR接口进行文字识别
        SmartDocumentRecognizerReq body = SmartDocumentRecognizerReq.builder()
            .data(base64Image)
            .language("zh")
            .eraseSeal(true)
            .singleOrientationMode(true)
            .build();

        SmartDocumentRecognizerRsp response;
        try {
            response = ocrClient.smartDocumentRecognizer("", opProjectId, body);
        } catch (Exception e) {
            String errorMsg = String.format("Failed to process image:%s with ocr.", url);
            log.error(errorMsg, e);
            throw new AgentStudioException(StudioError.OCR_RECOGNIZE_FAILED);
        }
        return buildOcrResultInfo(response);
    }

    /**
     * 构造OCR插件响应result
     *
     * @param response OCR服务响应体
     * @return OcrResultInfo OCR插件响应result
     */
    private OcrResultInfo buildOcrResultInfo(SmartDocumentRecognizerRsp response) {
        SmartDocumentRecognizerRsp.OcrInfo ocrResult = response.getResult().get(0).getOcrResult();
        OcrResultInfo ocrResultInfo = new OcrResultInfo();

        // 识别文字块数量为0时直接返回
        if (ocrResult.getWordsBlockCount() == 0) {
            return ocrResultInfo;
        }

        // 构造ocrResultInfo
        ocrResultInfo.setWordsBlockCount(ocrResult.getWordsBlockCount());
        List<OcrResultInfoWordsBlockList> wordsBlocks = buildOcrWordsBlocks(ocrResult);
        return ocrResultInfo.setWordsBlockList(wordsBlocks);
    }

    /**
     * 构造OCR识别文字块
     *
     * @param ocrResult OCR服务识别结果
     * @return List<OcrResultInfoWordsBlockList> 识别文字块集合
     */
    private List<OcrResultInfoWordsBlockList> buildOcrWordsBlocks(SmartDocumentRecognizerRsp.OcrInfo ocrResult) {
        List<SmartDocumentRecognizerRsp.OcrInfo.WordsBlock> wordsBlockList = ocrResult.getWordsBlockList();
        List<OcrResultInfoWordsBlockList> wordsBlocks = new ArrayList<>();
        for (SmartDocumentRecognizerRsp.OcrInfo.WordsBlock blockItem : wordsBlockList) {
            OcrResultInfoWordsBlockList wordsBlock = new OcrResultInfoWordsBlockList();
            wordsBlock.setWords(blockItem.getWords());
            wordsBlock.setConfidence(blockItem.getConfidence());
            wordsBlocks.add(wordsBlock);
        }
        return wordsBlocks;
    }

    /**
     * 单文件文档解析
     *
     * @param url 文件url
     * @param ocrEnabled 是否打开ocr
     * @return String 解析结果
     */
    private ResolveDocumentRspData resolveDocumentHandler(String url, boolean ocrEnabled) {
        Resource file;
        try (InputStream inputStream = obsService.getByUrl(url)) {
            // url转化为Resource进行传输
            file = new ByteArrayResource(CommonUtils.toByteArray(inputStream)) {
                @Override
                public String getFilename() {
                    return getSuffixByUri(url).getName();
                }
            };
        } catch (Exception e) {
            log.error("Get inputStream from obs by url failed.", e);
            throw new AgentStudioException(StudioError.GET_BY_URL_FAILED);
        }

        // 调用uniFactory接口上传文件,生成文件解析任务id
        UniFactoryUploadFileReq uniFactoryUploadFileReq = UniFactoryUploadFileReq.builder()
                .file(file)
                .ocr(ocrEnabled)
                .ocrEnabled(ocrEnabled)
                .imageEnabled(true)
                .imageConf(Constant.TEXT_STR)
                .splitMode(Constant.AUTO_MODE)
                .build();
        String taskId = uploadFile(uniFactoryUploadFileReq).getTaskId();
        return buildResolveResult(taskId);
    }

    /**
     * 上传文件，返回文档解析任务id
     *
     * @param req 上传文件请求体
     * @return UniFactoryUploadFileRsp 上传文件响应体
     */
    private UniFactoryUploadFileRsp uploadFile(UniFactoryUploadFileReq req) {
        try {
            // 调用uniFactory接口上传文件
            return uniFactoryClient.uploadFile(getLakeSearchAuthToken(), opProjectId, DEFAULT_APP_ID, req.getFile(),
                req.getOcr(), req.getOcrEnabled(), req.getImageEnabled(), req.getImageConf(), req.getSplitMode(),
                req.isCatalogEnabled());
        } catch (Exception e) {
            log.error("Upload file by uniFactory failed.", e);
            throw new AgentStudioException(StudioError.UPLOAD_FILE_FAILED);
        }
    }

    /**
     * 构造解析结果
     *
     * @param taskId 文档解析任务id
     * @return String 解析结果
     */
    private ResolveDocumentRspData buildResolveResult(String taskId) {
        // 用于在runnable中获取ScheduledFuture的引用来取消任务
        AtomicReference<ScheduledFuture<?>> scheduledFutureRef = new AtomicReference<>();

        // 在任务完成时执行countDown()
        CountDownLatch countDownLatch = new CountDownLatch(1);
        ResolveDocumentRspData resolveDocumentRspData = new ResolveDocumentRspData();
        Runnable runnable = () -> {
            try {
                // 调用uniFactory接口获取解析结果
                UniFactoryShowTaskRsp resolveData =
                    uniFactoryClient.showTaskResult(getLakeSearchAuthToken(), opProjectId, DEFAULT_APP_ID, taskId);

                // 解析失败
                if (Constant.TaskStatus.ERROR.equals(resolveData.getTaskStatus())) {
                    resolveDocumentRspData.setStatus(Constant.TaskStatus.ERROR.toLowerCase(Locale.ROOT));
                    resolveDocumentRspData.setErrorMessage(resolveData.getTaskDesc());
                    cancelTask(scheduledFutureRef.get());
                    countDownLatch.countDown();
                }

                // 解析成功，构造result
                if (Constant.TaskStatus.SUCCESS.equals(resolveData.getTaskStatus())) {
                    processPageResults(resolveData.getResult().getPages(), resolveDocumentRspData);
                    cancelTask(scheduledFutureRef.get());
                    countDownLatch.countDown();
                }
            } catch (Exception e) {
                log.error("Resolve file failed.", e);
                resolveDocumentRspData.setStatus(Constant.TaskStatus.ERROR.toLowerCase(Locale.ROOT));
                resolveDocumentRspData.setErrorMessage("exception occurred while calling uniFactory interface.");
                cancelTask(scheduledFutureRef.get());
                countDownLatch.countDown();
            }
        };
        ScheduledFuture<?> scheduledFuture = taskScheduler.scheduleAtFixedRate(runnable, Duration.ofMillis(500));
        scheduledFutureRef.set(scheduledFuture);

        try {
            // 返回解析结果
            boolean await = countDownLatch.await(toolRequestTimeout, TimeUnit.SECONDS);
            if (await) {
                return resolveDocumentRspData;
            } else {
                log.error("resolve audio file by uniFactory interface timeout.");
                throw new AgentStudioException(StudioError.RESOLVE_FILE_FAILED);
            }
        } catch (InterruptedException e) {
            cancelTask(scheduledFutureRef.get());
            log.error("Resolve file failed.", e);
            throw new AgentStudioException(StudioError.RESOLVE_FILE_FAILED);
        }
    }

    // 处理解析结果
    private void processPageResults(List<UniFactoryShowTaskRsp.PageResult> pageResults, ResolveDocumentRspData data) {
        List<ResolvePageInfo> pages = pageResults.stream().map(page -> {
            ResolvePageInfo pageInfo = new ResolvePageInfo();
            pageInfo.setPageNum(page.getPageNum());
            List<String> content = page.getComponents().stream().map(this::processComponent).toList();
            pageInfo.setContent(content);
            return pageInfo;
        }).toList();
        data.setStatus(Constant.TaskStatus.SUCCESS.toLowerCase(Locale.ROOT));
        data.setPages(pages);
    }

    // 处理标题
    private String processComponent(UniFactoryShowTaskRsp.Component component) {
        if (StringUtils.isBlank(component.getTitle())) {
            return component.getText();
        }
        return component.getTitle() + "\n" + component.getText();
    }

    // 取消任务
    private void cancelTask(ScheduledFuture<?> future) {
        if (future != null) {
            future.cancel(true);
        }
    }

    private String getLakeSearchAuthToken() {
        if (Constant.ENV_SIMPLE.equals(envType)) {
            return "";
        }
        if (isHcs) {
            return authValue;
        }
        return "";
    }

    private String getExtensionValue(Map<String, Object> extensions, String key) {
        if (extensions == null || extensions.isEmpty()) {
            return "";
        }
        return extensions.get(key).toString();
    }

    /**
     * 从fileUrl中获取文件配置
     *
     * @param fileUrl
     * @return FileConfig
     */
    private FileConfig getSuffixByUri(String fileUrl) {
        URI uri;
        try {
            uri = new URI(fileUrl);
        } catch (URISyntaxException e) {
            log.error("Resolve file failed.", e);
            throw new AgentStudioException(StudioError.RESOLVE_FILE_FAILED);
        }

        // 解析url获取文件后缀名
        String path = uri.getPath();
        if (StringUtils.isEmpty(path)) {
            log.error("Resolve file failed.");
            throw new AgentStudioException(StudioError.RESOLVE_FILE_FAILED);
        }

        FileConfig fileConfig = new FileConfig();
        fileConfig.setName(FilenameUtils.getName(path));
        fileConfig.setType(FilenameUtils.getExtension(path));
        return fileConfig;
    }
}
