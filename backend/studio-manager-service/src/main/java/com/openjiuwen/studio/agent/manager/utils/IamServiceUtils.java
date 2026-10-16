/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.utils;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONObject;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.common.utils.OkHttpClientUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.iam.GenerateIamTokenRequest;
import com.openjiuwen.studio.agent.manager.dto.iam.GetIamUserResponse;
import com.openjiuwen.studio.agent.manager.dto.iam.IamAuth;
import com.openjiuwen.studio.agent.manager.dto.iam.IamDomain;
import com.openjiuwen.studio.agent.manager.dto.iam.IamIdentity;
import com.openjiuwen.studio.agent.manager.dto.iam.IamPassword;
import com.openjiuwen.studio.agent.manager.dto.iam.IamProject;
import com.openjiuwen.studio.agent.manager.dto.iam.IamScope;
import com.openjiuwen.studio.agent.manager.dto.iam.IamUser;
import com.openjiuwen.studio.agent.manager.dto.iam.IamUserGroupPermissionRsp;
import com.openjiuwen.studio.agent.manager.dto.iam.IamUserGroupRsp;
import com.openjiuwen.studio.agent.manager.rce.models.IamUserInfoResp;
import com.openjiuwen.studio.agent.manager.rce.service.ClientService;
import com.openjiuwen.studio.agent.manager.service.mcp.properties.IamProperties;

import lombok.extern.slf4j.Slf4j;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Scope;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.ConcurrentHashMap;

import javax.annotation.Resource;

/**
 * iam类
 *
 */
@Slf4j
@Service
@Scope("prototype")
public class IamServiceUtils {

    private final Map<String, IamTokenCache> domainTokenCache = new ConcurrentHashMap<>();

    @Autowired
    private OkHttpClientUtils okHttpClientUtils;

    public static final String IAM_LIST_USER_URI = "/v3/users";

    private static final String TOKEN_HEADER = "X-Subject-Token";

    private static final String GET_TOKEN_URL = "/v3/auth/tokens";

    private static final String GET_USER_GROUPS = "/v3/users/%s/groups";

    private static final String GET_USER_GROUPS_PERMISSION
        = "/v3/OS-INHERIT/domains/%s/groups/%s/roles/inherited_to_projects";

    private static final String METHOD_NAME = "password";

    private static final long TOKEN_EXPIRE_MILLIS = 60L * 1000;

    @Value("${iam.url:}")
    private String iamUrl;

    @Resource
    private IamProperties iamProperties;

    @Resource
    private ClientService clientService;


    /**
     * 获取op账号的token
     *
     */
    public String getOpAccountAuthToken() {
        log.info("use iam to get iam token");
        return generateAuthToken(iamProperties.getUser(), iamProperties.getPassword(), iamProperties.getAccount(),
            iamProperties.getProjectName());
    }

    /**
     * 获取token
     *
     * @param cloudService 目标服务名称，内部依赖查询CMDB/DCM等服务获取服务状态。调用DCM需要获取COA token，调用CMDB需要获取
     * @return domain级别的token
     */
    public String queryDomainTokenFromCache(String cloudService) {

        String cacheKey = RequestContextUtils.getRequestUserDomainId() + "_" + RequestContextUtils.getRequestUserId();
        IamTokenCache cached = domainTokenCache.get(cacheKey);

        if (cached != null && !cached.isExpired()) {
            return cached.getValue();
        }

        String newToken = queryDomainToken(RequestContextUtils.getRequestAuthToken(), RequestContextUtils.getRequestUserDomainName());

        if (!StringUtils.isBlank(newToken)) {
            domainTokenCache.put(cacheKey,
                new IamTokenCache(newToken, System.currentTimeMillis() + TOKEN_EXPIRE_MILLIS));
        }
        return newToken;
    }

    /**
     * 因为IAM是Global级别的服务，所以访问IAM需要使用domain级别的token
     * 通过project级别的Token换取domain级别的token
     *
     * @param token token
     * @param domainName domainName
     * @return domain级别的token
     */
    public String queryDomainToken(String token, String domainName) {
        String url = iamUrl + GET_TOKEN_URL;

        OkHttpClient client = okHttpClientUtils.getHttpClient();

        try (Response response = sendRequest(client, token, domainName, url)) {

            int statusCode = response.code();
            if (statusCode < 200 || statusCode >= 300) {
                log.error("Failed to query domain token, status={}", statusCode);
                return "";
            }

            String domainToken = response.header(TOKEN_HEADER);
            if (domainToken == null) {
                log.error("Response missing header {}", TOKEN_HEADER);
                return "";
            }

            log.debug("Domain token retrieved for domain [{}]", domainName);
            return domainToken;

        } catch (Exception e) {
            log.error("queryDomainToken error", e);
            return "";
        }
    }

    private Response sendRequest(OkHttpClient client, String token, String domainName, String url) throws IOException {
        // domainName 可能为空（例如 SSO 响应未返回域名称），兜底为 "0" 避免空指针
        String safeDomainName = StringUtils.defaultIfBlank(domainName, "0").replace("\"", "\\\"");
        String bodyJson = "{" + "\"auth\": {" + "\"identity\": {" + "\"methods\": [\"token\"],"
            + "\"token\": {\"id\": \"" + token + "\"}" + "}," + "\"scope\": {" + "\"domain\": {\"name\": \""
            + safeDomainName + "\"}" + "}" + "}" + "}";

        RequestBody body = RequestBody.create(bodyJson, MediaType.parse("application/json; charset=utf-8"));

        Request request = new Request.Builder().url(url)
            .post(body)
            .addHeader("Content-Type", "application/json")
            .build();

        return client.newCall(request).execute();
    }

    /**
     * 从iam查询用户
     *
     */
    public GetIamUserResponse queryIamUserList(String token) {
        if (StringUtils.isBlank(token)) {
            return new GetIamUserResponse();
        }

        String url = iamUrl + IAM_LIST_USER_URI;

        Request request = new Request.Builder().url(url).get().addHeader("X-Auth-Token", token).build();

        try (Response response = okHttpClientUtils.getHttpClient().newCall(request).execute()) {
            int statusCode = response.code();
            if (statusCode < 200 || statusCode >= 300) {
                String body = response.body() != null ? response.body().string() : "";
                log.error("the user does not have IAM query permissions, response={}", body);
                return new GetIamUserResponse();
            }

            if (response.body() == null) {
                log.error("Received IAM user query response with null body. StatusCode: {}, Token header: X-Auth-Token",
                        statusCode);
                return new GetIamUserResponse();
            }

            String body = response.body().string();
            if (StringUtils.isBlank(body)) {
                log.error("Received IAM user query response with blank or empty body. Body: '{}', StatusCode: {}",
                        body, statusCode);
                return new GetIamUserResponse();
            }
            return JSON.parseObject(body, GetIamUserResponse.class);
        } catch (Exception e) {
            log.error("queryIamUserList error, reason={}", e.getMessage(), e);
            throw new AgentStudioException(StudioError.INTERFACE_CALL_EXCEPTION);
        }
    }

    /**
     * 从iam查询用户所有组
     *
     */
    public IamUserGroupRsp queryIamUserGroupList(String token) {
        if (StringUtils.isBlank(token)) {
            return new IamUserGroupRsp();
        }

        String url = iamUrl + String.format(GET_USER_GROUPS, RequestContextUtils.getRequestUserId());
        OkHttpClient client = okHttpClientUtils.getHttpClient();

        Request request = new Request.Builder().url(url).get().addHeader("X-Auth-Token", token).build();

        try (Response response = client.newCall(request).execute()) {
            if (response.body() == null) {
                return new IamUserGroupRsp();
            }

            String body = response.body().string();

            if (StringUtils.isBlank(body)) {
                return new IamUserGroupRsp();
            }

            return JSON.parseObject(body, IamUserGroupRsp.class);

        } catch (Exception e) {
            log.error("queryIamUserGroupList error, reason={}", e.getMessage(), e);
            return new IamUserGroupRsp();
        }
    }

    /**
     * 从iam查询用户组对应权限
     *
     */
    public IamUserGroupPermissionRsp queryIamUserGroupPermissionList(String token, String groupId) {
        if (StringUtils.isBlank(token)) {
            return new IamUserGroupPermissionRsp();
        }

        String url = iamUrl + String.format(GET_USER_GROUPS_PERMISSION, RequestContextUtils.getRequestUserDomainId(),
            groupId);
        OkHttpClient client = okHttpClientUtils.getHttpClient();

        Request request = new Request.Builder().url(url).get().addHeader("X-Auth-Token", token).build();

        try (Response response = client.newCall(request).execute()) {
            if (response.body() == null) {
                return new IamUserGroupPermissionRsp();
            }

            String body = response.body().string();

            if (StringUtils.isBlank(body)) {
                return new IamUserGroupPermissionRsp();
            }

            return JSON.parseObject(body, IamUserGroupPermissionRsp.class);

        } catch (Exception e) {
            log.error("queryIamUserGroupPermissionList error, reason={}", e.getMessage(), e);
            return new IamUserGroupPermissionRsp();
        }
    }

    /**
     * 获取token
     *
     */
    public String generateAuthToken(String userName, String userPasswordEncrypted, String domainName,
        String projectName) {
        IamScope scope = IamScope.builder().project(IamProject.builder().name(projectName).build()).build();
        IamIdentity identity = toIamIdentity(userName, domainName, userPasswordEncrypted);
        GenerateIamTokenRequest generateIamTokenRequest = GenerateIamTokenRequest.builder()
            .auth(IamAuth.builder().identity(identity).scope(scope).build())
            .build();
        String iamGenTokenUrl = iamUrl + "/v3/auth/tokens";
        return this.sendPost(iamGenTokenUrl, new HashMap<>(), generateIamTokenRequest);
    }

    private IamIdentity toIamIdentity(String userName, String domainName, String encryptedUserPassword) {
        return IamIdentity.builder()
            .password(IamPassword.builder()
                .user(IamUser.builder()
                    .domain(IamDomain.builder().name(domainName).build())
                    .name(userName)
                    .password(CryptoUtils.decrypt(encryptedUserPassword))
                    .build())
                .build())
            .methods(Collections.singletonList(METHOD_NAME))
            .build();
    }

    /**
     * 发送请求
     *
     */
    public String sendPost(String url, Map<String, String> headers, Object request) {
        String body = JSONObject.toJSONString(request);
        RequestBody requestBody = RequestBody.create(body, MediaType.get("application/json"));

        Request.Builder requestBuilder = new Request.Builder().url(url)
            .post(requestBody)
            .addHeader("Content-Type", "application/json");

        if (headers != null) {
            for (Map.Entry<String, String> entry : headers.entrySet()) {
                requestBuilder.addHeader(entry.getKey(), entry.getValue());
            }
        }

        try (Response response = okHttpClientUtils.getHttpClient().newCall(requestBuilder.build()).execute()) {
            if (response.isSuccessful()) {
                return response.header("X-Subject-Token");
            } else {
                throw new AgentStudioException(StudioError.INTERFACE_CALL_EXCEPTION);
            }
        } catch (IOException e) {
            log.error("queryDomainToken error, the reason is {}", e.getMessage());
            throw new AgentStudioException(StudioError.INTERFACE_CALL_EXCEPTION);
        }
    }

    /**
     * 查询角色
     *
     */
    public boolean doAuthorization(String projectId, String roleId, String agencyId) {
        String token = RequestContextUtils.getRequestAuthToken();
        ResponseEntity<JSONObject> response = this.clientService.agencyAuthorization(token, projectId, roleId,
            agencyId);
        if (response.getStatusCode().is2xxSuccessful()) {
            return true;
        } else {
            log.error("iam roles authorization fail!");
            throw new AgentStudioException(StudioError.AGENCY_FAIL);
        }
    }

    /**
     * 查询角色
     *
     */
    public boolean hasAgencyAuthorization(String projectId, String roleId, String agencyId) {
        String token = RequestContextUtils.getRequestAuthToken();
        try {
            ResponseEntity<JSONObject> response = this.clientService.hasAgencyAuthorization(token, projectId, roleId,
                agencyId);
            return response.getStatusCode().is2xxSuccessful();
        } catch (Exception exception) {
            log.error("no authorization!");
            return false;
        }
    }

}
