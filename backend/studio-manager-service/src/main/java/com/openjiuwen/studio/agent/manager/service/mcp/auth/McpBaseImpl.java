/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.mcp.auth;

import com.alibaba.fastjson2.JSON;
import com.openjiuwen.studio.agent.common.dto.auth.AuthKeyInfo;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.UrlCheckUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.common.dto.auth.OauthInfo;
import com.openjiuwen.studio.agent.manager.dto.plugin.ResourceParam;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.McpServiceEntity;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.service.mcp.model.dao.McpServiceDao;
import com.openjiuwen.studio.agent.manager.utils.CommonUtil;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.apache.hc.core5.net.URIBuilder;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.util.CollectionUtils;

import java.net.URISyntaxException;
import java.util.*;
import java.util.regex.Pattern;

@Slf4j
@Component
public class McpBaseImpl implements IMcpBase {

    private static final String GRANT_TYPE = "client_credentials";

    private static final Pattern OAUTH_URL_PATTERN = Pattern.compile(".*oauth.*", Pattern.CASE_INSENSITIVE);

    private static final Pattern SECRET_IS_NEED_SKIP = Pattern.compile("^.{1}\\*{4}.{1}$", Pattern.CASE_INSENSITIVE);

    @Autowired
    private McpOauthAdapter mcpOauthAdapter;

    @Autowired
    private EncryptionAdapter encryptionAdapter;

    @Autowired
    private UrlCheckUtils urlCheckUtils;

    @Resource
    private McpServiceDao serviceDao;

    @Autowired
    private MappingMapper mappingMapper;


    /**
     * OAUTH认证 换取token
     * @param authInfo 鉴权信息
     * @param headers 请求头
     */
    @Override
    public String exchangeTokenByAuth(AuthInfo authInfo, Map<String, String> headers, String mcpUrl) {
        log.info("Mcp start to exchange token by oauth!");

        // oauth 鉴权
        if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.OAUTH.equals(authInfo.getScope())) {
            validOauthUrl(authInfo.getCustomOauth().getEndpointUrl());
            mcpOauthAdapter.requestHeaderHandler(authInfo.getCustomOauth(), headers);
        }

        // apikey 鉴权解密
        if (!Objects.isNull(authInfo) && !CollectionUtils.isEmpty(authInfo.getAuthKeys())) {
            if (AuthInfo.DomainEnum.HEADERS.equals(authInfo.getDomain())) {
                // domain为HEADERS时，添加到headers中
                for (AuthKeyInfo authKeyInfo : authInfo.getAuthKeys()) {
                    if (StringUtils.isBlank(authKeyInfo.getAuthKey()) || CommonConstant.ANONYMIZED_TEXT.equals(
                            authKeyInfo.getAuthKey())) {
                        continue ;
                    }
                    headers.put(authKeyInfo.getTargetName(), encryptionAdapter.decrypt(authKeyInfo.getAuthKey()));
                }
            } else if (AuthInfo.DomainEnum.QUERY.equals(authInfo.getDomain())) {
                // domain为QUERY时，添加到URL的query参数中
                for (AuthKeyInfo authKeyInfo : authInfo.getAuthKeys()) {
                    if (StringUtils.isBlank(authKeyInfo.getAuthKey()) || CommonConstant.ANONYMIZED_TEXT.equals(
                            authKeyInfo.getAuthKey())) {
                        continue ;
                    }
                    String decryptedValue = encryptionAdapter.decrypt(authKeyInfo.getAuthKey());
                    
                    // 解析URL并添加query参数
                    try {
                        URIBuilder uriBuilder = new URIBuilder(mcpUrl);
                        uriBuilder.addParameter(authKeyInfo.getTargetName(), decryptedValue);

                        // 将修改后的URL重新赋值给mcpUrl
                        return uriBuilder.build().toString();
                    } catch (URISyntaxException e) {
                        log.error("Failed to build URI with query parameters: {}", e.getMessage(), e);
                    }
                }
            }
        }

        return mcpUrl;
    }

    /**
     * 查询数据时，隐私信息以******展示出来
     * @param authInfo 鉴权信息
     * @return authInfo
     */
    @Override
    // 对于鉴权信息，需要把authKey值设置为null，0625修改为"******"与其他服务统一
    public AuthInfo anonymizeAuthInfo(AuthInfo authInfo) {
        if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.OAUTH.equals(authInfo.getScope())) {
            authInfo.getCustomOauth().setClientSecret(maskKey(authInfo.getCustomOauth().getClientSecret()));
        }

        if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.SERVICE.equals(authInfo.getScope())) {
            authInfo.getAuthKeys().forEach(authKeyInfo -> authKeyInfo.setAuthKey(maskKey(authKeyInfo.getAuthKey())));
        }

        return authInfo;
    }

    /**
     * 加密鉴权信息中的隐私信息
     * @param authInfo 鉴权信息
     * @return authInfo
     */
    @Override
    public AuthInfo encryptedAuthInfo(AuthInfo authInfo) {
        if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.SERVICE.equals(authInfo.getScope())) {
            for (AuthKeyInfo authKeyInfo : authInfo.getAuthKeys()) {
                if (StringUtils.isBlank(authKeyInfo.getAuthKey()) || CommonConstant.ANONYMIZED_TEXT.equals(
                        authKeyInfo.getAuthKey())) {
                    return null;
                }
                authKeyInfo.setAuthKey(encryptionAdapter.encrypt(authKeyInfo.getAuthKey(), RequestContextUtils.getRequestUserDomainId()));
            }
        }

        if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.OAUTH.equals(authInfo.getScope())) {
            OauthInfo oauth = authInfo.getCustomOauth();
            if (oauth != null && StringUtils.isNotBlank(oauth.getClientSecret())) {
                oauth.setClientSecret(encryptionAdapter.encrypt(oauth.getClientSecret(), RequestContextUtils.getRequestUserDomainId()));
            }
        }
        return authInfo;
    }

    @Override
    public AuthInfo decryptedAuthInfo(AuthInfo authInfo) {
        if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.SERVICE.equals(authInfo.getScope())) {
            for (AuthKeyInfo authKeyInfo : authInfo.getAuthKeys()) {
                if (StringUtils.isBlank(authKeyInfo.getAuthKey()) || CommonConstant.ANONYMIZED_TEXT.equals(
                        authKeyInfo.getAuthKey())) {
                    return null;
                }
                authKeyInfo.setAuthKey(encryptionAdapter.decrypt(authKeyInfo.getAuthKey(), RequestContextUtils.getRequestUserDomainId()));
            }
        }

        if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.OAUTH.equals(authInfo.getScope())) {
            OauthInfo oauth = authInfo.getCustomOauth();
            if (oauth != null && StringUtils.isNotBlank(oauth.getClientSecret())) {
                oauth.setClientSecret(encryptionAdapter.decrypt(oauth.getClientSecret(), RequestContextUtils.getRequestUserDomainId()));
            }
        }
        return authInfo;
    }

    private String maskKey(String key) {
        if (StringUtils.isBlank(key)) {
            return CommonConstant.ANONYMIZED_TEXT;
        }

        String decryptedKey;
        try {
            // 使用适配器解密，并用 try-catch
            decryptedKey = encryptionAdapter.decrypt(key);
        } catch (AgentStudioException e) {
            // 捕获跨租户、无权限等解密失败的异常（如 KMS.0307 403 Forbidden），保护列表不崩溃
            log.warn("Failed to decrypt MCP auth key for masking. Key might be cross-domain or deleted.");
            return CommonConstant.ANONYMIZED_TEXT;
        } catch (Exception e) {
            log.warn("Unexpected error when decrypting MCP auth key for masking.", e);
            return CommonConstant.ANONYMIZED_TEXT;
        }

        if (StringUtils.isBlank(decryptedKey)) {
            return CommonConstant.ANONYMIZED_TEXT;
        }

        // 判断明文(decryptedKey)的长度，而不是密文(key)的长度
        if (decryptedKey.length() == 1) {
            return decryptedKey.charAt(0) + CommonConstant.ANONYMIZED_TEXT.substring(1);
        }

        return decryptedKey.charAt(0) + CommonConstant.ANONYMIZED_TEXT.substring(1,
                CommonConstant.ANONYMIZED_TEXT.length() - 1) + decryptedKey.charAt(decryptedKey.length() - 1);
    }

    /**
     * 校验鉴权
     * @param authInfo 鉴权信息
     */
    @Override
    public void validAuthInfo(AuthInfo authInfo) {
        // oauth 鉴权
        if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.OAUTH.equals(authInfo.getScope())) {
            OauthInfo oauth = authInfo.getCustomOauth();
            String endpointUrl = oauth.getEndpointUrl();

            // url黑白名单校验
            urlCheckUtils.checkUrl(null, endpointUrl);
            if (endpointUrl.isEmpty() || oauth.getClientId().isEmpty() || oauth.getClientSecret().isEmpty()) {
                throw new AgentStudioException(StudioError.OAUTH_INFORMATION_OVER_LENGTH);
            }

            if (endpointUrl.length() > 255 || oauth.getClientId().length() > 255 || oauth.getClientSecret().length() > 255) {
                throw new AgentStudioException(StudioError.OAUTH_INFORMATION_OVER_LENGTH);
            }
        }

        // FEAT-093 动态鉴权：只配置出站头名（target_name），凭证值由工作流编排期绑定，禁止入库
        if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.DYNAMIC.equals(authInfo.getScope())) {
            validDynamicAuthInfo(authInfo);
            return;
        }

        // apikey 鉴权解密
        if (!Objects.isNull(authInfo) && !CollectionUtils.isEmpty(authInfo.getAuthKeys())) {
            for (AuthKeyInfo authKeyInfo : authInfo.getAuthKeys()) {
                String targetName = authKeyInfo.getTargetName();
                String authKey = authKeyInfo.getAuthKey();
                if (StringUtils.isBlank(targetName) || StringUtils.isBlank(authKey)) {
                    throw new AgentStudioException(StudioError.APIKEY_INFORMATION_OVER_LENGTH);
                }
                if (targetName.length() > 64 || authKey.length() > 20000) {
                    throw new AgentStudioException(StudioError.APIKEY_INFORMATION_OVER_LENGTH);
                }
            }
        }
    }

    /**
     * FEAT-093 动态鉴权配置校验：
     * - domain 仅支持 HEADERS（值注入仅在出站请求头层）
     * - auth_keys 1~5 条，target_name 必填、长度 1~64、不重复
     * - auth_key 必须为空（平台不存储凭证值）
     *
     * @param authInfo 鉴权信息
     */
    private void validDynamicAuthInfo(AuthInfo authInfo) {
        if (!AuthInfo.DomainEnum.HEADERS.equals(authInfo.getDomain())) {
            throw new AgentStudioException(StudioError.MCP_AUTH_DATA_INVALID,
                "dynamic auth only supports HEADERS domain");
        }
        if (CollectionUtils.isEmpty(authInfo.getAuthKeys())) {
            throw new AgentStudioException(StudioError.MCP_AUTH_DATA_INVALID,
                "dynamic auth requires at least one auth key entry");
        }
        Set<String> targetNames = new HashSet<>();
        for (AuthKeyInfo authKeyInfo : authInfo.getAuthKeys()) {
            String targetName = authKeyInfo.getTargetName();
            if (StringUtils.isBlank(targetName) || targetName.length() > 64) {
                throw new AgentStudioException(StudioError.MCP_AUTH_DATA_INVALID,
                    "dynamic auth target_name is required and its length must be 1-64");
            }
            if (StringUtils.isNotBlank(authKeyInfo.getAuthKey())) {
                throw new AgentStudioException(StudioError.MCP_AUTH_DATA_INVALID,
                    "dynamic auth must not persist credential value");
            }
            if (!targetNames.add(targetName.toLowerCase(Locale.ROOT))) {
                throw new AgentStudioException(StudioError.MCP_AUTH_DATA_INVALID,
                    "dynamic auth target_name is duplicated: " + targetName);
            }
        }
    }

    @Override
    public AuthInfo validIsNeedToUpdateAuthInfo(AuthInfo newAuth, AuthInfo oldAuth) {
        log.info("Start to valid is need to update auth info!");

        // oauth 鉴权
        if (!Objects.isNull(newAuth) && AuthInfo.ScopeEnum.OAUTH.equals(newAuth.getScope())) {
            OauthInfo oauth = newAuth.getCustomOauth();
            String clientSecret = encryptionAdapter.decrypt(oauth.getClientSecret());
            if (SECRET_IS_NEED_SKIP.matcher(clientSecret).matches()) {
                return null;
            }
        }

        // FEAT-093 动态鉴权：auth_key 恒为空，无需解密比对，始终按新配置更新
        if (!Objects.isNull(newAuth) && AuthInfo.ScopeEnum.DYNAMIC.equals(newAuth.getScope())) {
            return newAuth;
        }

        // apikey 鉴权解密
        if (!Objects.isNull(newAuth) && !CollectionUtils.isEmpty(newAuth.getAuthKeys())) {
            for (AuthKeyInfo authKeyInfo : newAuth.getAuthKeys()) {
                String authKey = encryptionAdapter.decrypt(authKeyInfo.getAuthKey());
                if (SECRET_IS_NEED_SKIP.matcher(authKey).matches()) {
                    return null;
                }
            }
        }

        return newAuth;
    }


    /**
     * 解析请求头，转为ResourceParameter
     * @param mcpService mcp
     * @return resourceParameter
     */
    @Override
    public String parseMcpInput2ResourceParameter(McpServiceEntity mcpService) {
        Map<String, String> headerInfo = new HashMap<>();
        // 将开始节点参数复制到ResourceParam
        List<ResourceParam> mcpParams = new ArrayList<>();
        headerInfo = CommonUtil.parseMcpConfigHeaderInfo(encryptionAdapter.decrypt(mcpService.getServerConfig()));

        if (!headerInfo.isEmpty()) {
            headerInfo.forEach((key, value) -> {
                ResourceParam mcpParam = ResourceParam.builder()
                        .defaultValue(value)
                        .name(key)
                        .type("string")
                        .description("")
                        .value(ResourceParam.ValueDTO.builder()
                                // 参数类型默认 literal
                                .type("literal")
                                .content(value)
                                .build())
                        // 参数可见性默认 true
                        .visibility(true)
                        .required(true)
                        .build();
                mcpParams.add(mcpParam);
            });
        }

        return JSON.toJSONString(mcpParams);
    }

    /**
     * 兼容老版本mcp 填充
     * @param agentMcp 映射
     */
    @Override
    public void fillExtendInfoOfMcpWhenRetrieveAgent(MappingEntity agentMcp) {
        log.info("Start to fill extend info of mcp when retrieve agent, mcp id: {}", agentMcp.getResourceId());

        if (!agentMcp.isValid()) {
            return;
        }

        if (StringUtils.isNotBlank(agentMcp.getExtendInfo())) {
            return;
        }

        String mcpId = agentMcp.getResourceId();
        McpServiceEntity mcpService = serviceDao.selectById(mcpId, CommonUtil.getTenantId(), CommonUtil.getDeptCode(), null);
        String parameter = parseMcpInput2ResourceParameter(mcpService);
        agentMcp.setExtendInfo(parameter);

        mappingMapper.updateResourceParameterByAppIDAndResourceId(agentMcp);
    }

    /**
     * url 校验
     * @param oauthUrl oauth地址
     */
    public void validOauthUrl(String oauthUrl) {
        if (StringUtils.isBlank(oauthUrl)) {
            log.info("oauth url is null");
            return;
        }

        if (!OAUTH_URL_PATTERN.matcher(oauthUrl).matches()) {
            log.error("oauth url is invalid: {}", oauthUrl);
            throw new AgentStudioException(StudioError.MCP_AUTH_DATA_INVALID);
        }
    }
}
