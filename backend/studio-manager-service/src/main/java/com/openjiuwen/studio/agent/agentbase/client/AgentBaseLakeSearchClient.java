/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.client;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONException;
import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.agentbase.common.enums.LakeSearchApi;
import com.openjiuwen.studio.agent.common.enums.RagAuthMode;
import com.openjiuwen.studio.agent.agentbase.model.ErrorInfo;
import com.openjiuwen.studio.agent.agentbase.model.ResultModel;
import com.openjiuwen.studio.agent.agentbase.service.knowledgerepo.KnowledgeConnectionRouterService;
import com.openjiuwen.studio.agent.agentbase.service.knowledgerepo.connection.LakeSearchConnection;
import com.openjiuwen.studio.agent.agentbase.service.knowledgerepo.knowledgesourceprovider.LakeSearchConnectionProvider;
import com.openjiuwen.studio.agent.agentbase.utils.HttpClientUtils;
import com.openjiuwen.studio.agent.agentbase.utils.HttpDeleteWithBody;
import com.openjiuwen.studio.agent.foundation.base.exception.AgentBaseException;
import com.openjiuwen.studio.agent.foundation.base.exception.ErrorCode;
import com.openjiuwen.studio.agent.foundation.base.utils.RandomUtil;

import org.apache.commons.lang3.StringUtils;
import org.apache.hc.client5.http.entity.mime.HttpMultipartMode;
import org.apache.hc.client5.http.entity.mime.InputStreamBody;
import org.apache.hc.client5.http.entity.mime.MultipartEntityBuilder;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.core5.http.ClassicHttpRequest;
import org.apache.hc.core5.http.ClassicHttpResponse;
import org.apache.hc.core5.http.ContentType;
import org.apache.hc.core5.http.HttpEntity;
import org.apache.hc.core5.http.HttpHeaders;
import org.apache.hc.core5.http.HttpStatus;
import org.apache.hc.core5.http.ParseException;
import org.apache.hc.core5.http.io.HttpClientResponseHandler;
import org.apache.hc.core5.http.io.entity.EntityUtils;
import org.apache.hc.core5.http.io.entity.StringEntity;
import org.apache.hc.core5.http.io.support.ClassicRequestBuilder;
import org.ietf.jgss.GSSContext;
import org.ietf.jgss.GSSManager;
import org.ietf.jgss.GSSName;
import org.ietf.jgss.Oid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.Resource;
import org.springframework.http.ResponseEntity;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.PrivilegedAction;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.regex.Pattern;

import javax.security.auth.Subject;
import javax.security.auth.login.AppConfigurationEntry;
import javax.security.auth.login.Configuration;
import javax.security.auth.login.LoginContext;
import javax.security.auth.login.LoginException;

/**
 * LakeSearch客户端，kerberos认证时使用,此种情况下，从数据库获取参数配置，但仍然沿用之前从配置项获取认证文件配置
 *
 * @since 2025-06-13
 */
@Component
public class AgentBaseLakeSearchClient {
    private static final Logger logger = LoggerFactory.getLogger(AgentBaseLakeSearchClient.class);

    private static final String UTF8 = "UTF-8";

    private static final Pattern PATTERN = Pattern.compile(".*");

    private static Subject subject;

    @Value("${knowledge.lakeSearch.auth-mode}")
    private String authMode;

    @Value("${knowledge.lakeSearch.keytab-file}")
    private String userKeytabFile;

    @Value("${knowledge.lakeSearch.krb5-file}")
    private String krb5File;

    private final LakeSearchConnectionProvider lakeSearchConnectionProvider;

    private final KnowledgeConnectionRouterService knowledgeConnectionRouterService;

    public AgentBaseLakeSearchClient(LakeSearchConnectionProvider lakeSearchConnectionProvider,
        KnowledgeConnectionRouterService knowledgeConnectionRouterService) {
        this.lakeSearchConnectionProvider = lakeSearchConnectionProvider;
        this.knowledgeConnectionRouterService = knowledgeConnectionRouterService;
    }

    /**
     * 初始化kerberos认证
     *
     * @throws Exception
     */
    @Scheduled(fixedDelayString = "${knowledge.lakeSearch.login-delay}")
    public void init() throws IOException, LoginException {
        if (RagAuthMode.KERBEROS.toString().equalsIgnoreCase(authMode)) {
            LakeSearchConnection lakeSearchConnection = null;
            try {
                String connectionId = knowledgeConnectionRouterService.findConnectionIdByKerberosAuthMode();
                lakeSearchConnection = lakeSearchConnectionProvider.getKnowledgeSourceConnection(connectionId);
            } catch (Exception exception) {
                logger.error("cannot get knowledge source connection info from db, ex is {}", exception);
            }
            if (lakeSearchConnection != null) {
                doKerberosLogin();
            }
        }
    }

    /**
     * lakeSearch使用kerberos认证，发送请求
     *
     * @param endpoint 请求endpoint
     * @param requestContent 请求体内容
     * @param lakeSearchApi 知识库操作
     * @param file 上传文件
     * @return ResultModel
     */
    public ResultModel sendAction(String endpoint, String requestContent, LakeSearchApi lakeSearchApi,
        MultipartFile file) {
        String connectionId = knowledgeConnectionRouterService.findConnectionIdByKerberosAuthMode();
        LakeSearchConnection lakeSearchConnection = lakeSearchConnectionProvider.getKnowledgeSourceConnection(
            connectionId);
        String hosts = lakeSearchConnection.getKerberosAuth().getHostNames();
        String ips = lakeSearchConnection.getKerberosAuth().getClusterIps();
        String protocol = lakeSearchConnection.getKerberosAuth().getProtocol();
        String port = lakeSearchConnection.getKerberosAuth().getPort();
        List<String> goodHosts = new ArrayList<>(Arrays.asList(hosts.split(",")));
        List<String> goodIps = new ArrayList<>(Arrays.asList(ips.split(",")));
        ResultModel result = null;
        int index = 0;
        while (!goodIps.isEmpty()) {
            try {
                index = RandomUtil.getRandom(goodIps.size());
                String url = protocol + "://" + goodIps.get(index) + ":" + port + endpoint;
                result = call(url, requestContent, lakeSearchApi, file, goodHosts.get(index));
                break;
            } catch (Exception e) {
                logger.error("Failed send request to {}.", goodIps.get(index), e);
                goodIps.remove(goodIps.get(index));
            }
        }
        return result;
    }

    private ResultModel call(String url, String requestContent, LakeSearchApi lakeSearchApi, MultipartFile file,
        String host) throws IOException, ParseException {
        ResultModel result = new ResultModel();
        CloseableHttpClient httpclient = HttpClientUtils.getHttpClient();

        // 构建 HTTP 请求（保持不变）
        ClassicHttpRequest request = switch (lakeSearchApi.getMethod()) {
            case GET -> ClassicRequestBuilder.get(url).build();
            case POST -> ClassicRequestBuilder.post(url).build();
            case DELETE -> {
                if (StringUtils.isNoneBlank(requestContent)) {
                    HttpDeleteWithBody deleteReq = new HttpDeleteWithBody(url);
                    deleteReq.setEntity(new StringEntity(requestContent, ContentType.APPLICATION_JSON));
                    yield deleteReq;
                } else {
                    yield ClassicRequestBuilder.delete(url).build();
                }
            }
            case PUT -> ClassicRequestBuilder.put(url).build();
        };

        // 设置 JSON 请求体
        if (StringUtils.isNoneBlank(requestContent)) {
            request.setEntity(new StringEntity(requestContent, ContentType.APPLICATION_JSON));
        }

        // 设置通用 Header
        request.setHeader(HttpHeaders.ACCEPT, "application/json");
        request.setHeader(HttpHeaders.CONTENT_ENCODING, StandardCharsets.UTF_8);
        request.setHeader(HttpHeaders.ACCEPT_ENCODING, "identity");
        request.setHeader(HttpHeaders.CONNECTION, "keep-alive");

        // 使用推荐的execute方法
        httpclient.execute(request, new HttpClientResponseHandler<Void>() {
            @Override
            public Void handleResponse(final ClassicHttpResponse response) throws IOException, ParseException {
                int status = response.getCode();
                if (status == HttpStatus.SC_UNAUTHORIZED && challenge(response)) {
                    request.setHeader("Authorization", generateGSSToken(host));
                    setEntityForUpload(lakeSearchApi, file, request);

                    httpclient.execute(request, new HttpClientResponseHandler<Void>() {
                        @Override
                        public Void handleResponse(final ClassicHttpResponse response2)
                            throws IOException, ParseException {
                            handleResponseResult(lakeSearchApi, result, response2);
                            return null;
                        }
                    });
                } else {
                    handleResponseResult(lakeSearchApi, result, response);
                }
                return null;
            }
        });

        return result;
    }

    private void handleResponseResult(LakeSearchApi lakeSearchApi, ResultModel result, ClassicHttpResponse response)
        throws IOException, ParseException {
        HttpEntity entity = response.getEntity();
        int statusCode = response.getCode();
        result.setStatusCode(statusCode);
        if (statusCode == HttpStatus.SC_OK || statusCode == HttpStatus.SC_NO_CONTENT
            || statusCode == HttpStatus.SC_CREATED) {
            if (LakeSearchApi.DOWNLOAD_FILE.equals(lakeSearchApi) || LakeSearchApi.DOWNLOAD_FAQ_FILE.equals(
                lakeSearchApi)) {
                result.setResponseEntity(ResponseEntity.ok(EntityUtils.toByteArray(entity)));
            } else {
                String content = (entity != null) ? EntityUtils.toString(entity, StandardCharsets.UTF_8) : "";
                result.setContent(content);
            }
            logger.info("{} request success, Status: {}.", lakeSearchApi, statusCode);
        } else {
            String entityString = entity != null ? EntityUtils.toString(entity, StandardCharsets.UTF_8) : "";
            logger.error("{} request failed. Status: {}, Details: {}.", lakeSearchApi, statusCode, entityString);
            try {
                JSONObject jsonObject = Optional.ofNullable(JSON.parseObject(entityString)).orElse(new JSONObject());
                result.setErrorDetail(ErrorInfo.builder()
                    .errorCode(jsonObject.getString("error_code"))
                    .errorMsg(jsonObject.getString("error_message"))
                    .build());
            } catch (JSONException exception) {
                logger.warn("Fail to parse EntityString to ErrorDetail.");
                result.setErrorDetail(
                    ErrorInfo.builder().errorCode(String.valueOf(statusCode)).errorMsg(entityString).build());
            }
        }
    }

    private void setEntityForUpload(LakeSearchApi lakeSearchApi, MultipartFile file, ClassicHttpRequest request)
        throws IOException {
        if (!LakeSearchApi.UPLOAD_FILE.equals(lakeSearchApi) && !LakeSearchApi.UPLOAD_FAQ_FILE.equals(lakeSearchApi)) {
            return;
        }
        String originalFilename = file.getOriginalFilename();
        if (StringUtils.isBlank(originalFilename)) {
            logger.error("Incorrect file format.");
            throw new AgentBaseException(ErrorCode.FAIL_TO_UPLOAD_KNOWLEDGE_REPO_FILE);
        }
        InputStream inputStream = null;
        try {
            inputStream = file.getInputStream();
            request.removeHeaders(HttpHeaders.CONTENT_TYPE);
            String safeFileName = new File(originalFilename).getName();
            HttpEntity multipart = MultipartEntityBuilder.create()
                .setMode(HttpMultipartMode.LEGACY)
                .setCharset(StandardCharsets.UTF_8)
                .setBoundary(UUID.randomUUID().toString())
                .addPart("file", new InputStreamBody(inputStream, ContentType.DEFAULT_BINARY, safeFileName))
                .build();
            request.setEntity(multipart);
        } catch (IOException exception) {
            logger.error("Fail to read InputStream from Resource [{}]", originalFilename, exception);
            if (inputStream != null) {
                inputStream.close();
            }
            throw new AgentBaseException(ErrorCode.FAIL_TO_UPLOAD_KNOWLEDGE_REPO_FILE);
        }
    }

    private void doKerberosLogin() throws IOException, LoginException {
        try {
            logger.info("Begin to login by kerberos authentication.");
            String principal = KeytabPrincipalReader.getPrincipalNames(userKeytabFile, PATTERN)[0];
            Map<String, String> options = new HashMap<>();
            options.put("useTicketCache", "false");
            options.put("useKeyTab", "true");
            options.put("keyTab", userKeytabFile);
            options.put("refreshKrb5Config", "true");
            options.put("principal", principal);
            options.put("storeKey", "true");
            options.put("doNotPrompt", "true");
            options.put("isInitiator", "true");
            options.put("debug", "true");
            System.setProperty("javax.security.auth.useSubjectCredsOnly", "false");
            System.setProperty("sun.security.spnego.disable.ntlm", "true");
            System.setProperty("java.security.krb5.conf", krb5File);
            Configuration config = new Configuration() {
                @Override
                public AppConfigurationEntry[] getAppConfigurationEntry(String name) {
                    return new AppConfigurationEntry[] {
                        new AppConfigurationEntry("com.sun.security.auth.module.Krb5LoginModule",
                            AppConfigurationEntry.LoginModuleControlFlag.REQUIRED, options)
                    };
                }
            };
            LoginContext loginContext = new LoginContext("Krb5Login", null, null, config);
            loginContext.login();
            subject = loginContext.getSubject();
            logger.info("Success to login by kerberos authentication.");
        } catch (IOException exception) {
            logger.error("Fail to get principal from userKeytabFile [{}], cause [{}]", userKeytabFile, exception);
            throw exception;
        } catch (LoginException exception) {
            logger.error("Fail to login with userKeytabFile [{}], krb5File [{}], cause [{}]", userKeytabFile, krb5File,
                exception);
            throw exception;
        }
    }

    private boolean challenge(ClassicHttpResponse response) {
        // 检测是否是Negotiate协议，如果服务端是该协议需要添加GSSToken并再次请求建立链接
        boolean supportsNegotiate = false;
        for (var header : response.getHeaders("WWW-Authenticate")) {
            if ("Negotiate".equalsIgnoreCase(header.getValue().trim())) {
                supportsNegotiate = true;
                break;
            }
        }
        return supportsNegotiate;
    }

    private String generateGSSToken(String host) {
        return Subject.doAs(subject, (PrivilegedAction<String>) () -> {
            try {
                Oid oid = new Oid("1.3.6.1.5.5.2");
                GSSManager manager = GSSManager.getInstance();
                // 创建服务名称
                GSSName serverName = manager.createName("HTTP@" + host, GSSName.NT_HOSTBASED_SERVICE);
                // 创建上下文
                GSSContext context = manager.createContext(serverName.canonicalize(oid), oid, null,
                    GSSContext.DEFAULT_LIFETIME);
                context.requestCredDeleg(true);
                context.requestMutualAuth(true);
                // 生成token
                byte[] token = context.initSecContext(new byte[0], 0, 0);
                if (token != null) {
                    return "Negotiate " + Base64.getEncoder().encodeToString(token);
                } else {
                    logger.error("GSS Token is null with userKeytabFile [{}], krb5File [{}], host [{}]", userKeytabFile,
                        krb5File, host);
                    throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION);
                }
            } catch (Exception e) {
                logger.error("Fail to generate GSS Token with userKeytabFile [{}], krb5File [{}], host [{}]",
                    userKeytabFile, krb5File, host, e);
                throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION);
            }
        });
    }
}
