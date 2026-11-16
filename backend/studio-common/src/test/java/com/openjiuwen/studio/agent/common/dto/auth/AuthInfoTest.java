/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */

package com.openjiuwen.studio.agent.common.dto.auth;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

class AuthInfoTest {

    @Test
    void testAllGettersSetters() {
        List<AuthKeyInfo> authKeys = List.of(new AuthKeyInfo().setTargetName("t1"));
        Map<String, String> iamCredentials = new HashMap<>();
        iamCredentials.put("key1", "val1");
        HisIamInfo hisIamInfo = new HisIamInfo();
        HisSgov hisSgov = new HisSgov();
        PluginIAMAuthInfo customIam = new PluginIAMAuthInfo().setIamUrl("http://iam");
        OauthInfo oauth = new OauthInfo();
        AuthInfo obj = new AuthInfo()
                .setScope(AuthInfo.ScopeEnum.USER)
                .setDomain(AuthInfo.DomainEnum.HEADERS)
                .setAuthKeys(authKeys)
                .setIamCredentials(iamCredentials)
                .setHisIamInfo(hisIamInfo)
                .setHisSgov(hisSgov)
                .setCustomIamCredentials(customIam)
                .setCustomOauth(oauth);
        assertEquals(AuthInfo.ScopeEnum.USER, obj.getScope());
        assertEquals(AuthInfo.DomainEnum.HEADERS, obj.getDomain());
        assertEquals(authKeys, obj.getAuthKeys());
        assertEquals(iamCredentials, obj.getIamCredentials());
        assertEquals(hisIamInfo, obj.getHisIamInfo());
        assertEquals(hisSgov, obj.getHisSgov());
        assertEquals(customIam, obj.getCustomIamCredentials());
        assertEquals(oauth, obj.getCustomOauth());
    }

    @Test
    void testEquals_SameObject() {
        AuthInfo obj = new AuthInfo().setScope(AuthInfo.ScopeEnum.USER);
        assertEquals(obj, obj);
    }

    @Test
    void testEquals_EqualObject() {
        AuthInfo obj1 = new AuthInfo()
                .setScope(AuthInfo.ScopeEnum.IAM)
                .setDomain(AuthInfo.DomainEnum.QUERY);
        AuthInfo obj2 = new AuthInfo()
                .setScope(AuthInfo.ScopeEnum.IAM)
                .setDomain(AuthInfo.DomainEnum.QUERY);
        assertEquals(obj1, obj2);
    }

    @Test
    void testEquals_Null() {
        AuthInfo obj = new AuthInfo().setScope(AuthInfo.ScopeEnum.USER);
        assertNotEquals(null, obj);
    }

    @Test
    void testEquals_DifferentClass() {
        AuthInfo obj = new AuthInfo().setScope(AuthInfo.ScopeEnum.USER);
        assertNotEquals("string", obj);
    }

    @Test
    void testEquals_DifferentValues() {
        AuthInfo obj1 = new AuthInfo().setScope(AuthInfo.ScopeEnum.USER);
        AuthInfo obj2 = new AuthInfo().setScope(AuthInfo.ScopeEnum.SERVICE);
        assertNotEquals(obj1, obj2);
    }

    @Test
    void testHashCode_Consistency() {
        AuthInfo obj1 = new AuthInfo()
                .setScope(AuthInfo.ScopeEnum.IAM)
                .setDomain(AuthInfo.DomainEnum.HEADERS);
        AuthInfo obj2 = new AuthInfo()
                .setScope(AuthInfo.ScopeEnum.IAM)
                .setDomain(AuthInfo.DomainEnum.HEADERS);
        assertEquals(obj1.hashCode(), obj2.hashCode());
    }

    @Test
    void testToString_NotNull() {
        AuthInfo obj = new AuthInfo().setScope(AuthInfo.ScopeEnum.USER);
        assertNotNull(obj.toString());
    }

    @Test
    void testScopeEnum_Values() {
        AuthInfo.ScopeEnum[] values = AuthInfo.ScopeEnum.values();
        assertEquals(8, values.length);
    }

    @Test
    void testScopeEnum_FromValue() {
        assertEquals(AuthInfo.ScopeEnum.USER, AuthInfo.ScopeEnum.fromValue("USER"));
        assertEquals(AuthInfo.ScopeEnum.SERVICE, AuthInfo.ScopeEnum.fromValue("SERVICE"));
        assertEquals(AuthInfo.ScopeEnum.DYNAMIC, AuthInfo.ScopeEnum.fromValue("DYNAMIC"));
        assertEquals(AuthInfo.ScopeEnum.IAM, AuthInfo.ScopeEnum.fromValue("IAM"));
        assertEquals(AuthInfo.ScopeEnum.HIS_IAM, AuthInfo.ScopeEnum.fromValue("HIS_IAM"));
        assertEquals(AuthInfo.ScopeEnum.SGOV, AuthInfo.ScopeEnum.fromValue("SGOV"));
        assertEquals(AuthInfo.ScopeEnum.CUSTOM_IAM, AuthInfo.ScopeEnum.fromValue("CUSTOM_IAM"));
        assertEquals(AuthInfo.ScopeEnum.OAUTH, AuthInfo.ScopeEnum.fromValue("OAUTH"));
    }

    @Test
    void testScopeEnum_FromValue_Invalid() {
        assertNull(AuthInfo.ScopeEnum.fromValue("INVALID"));
    }

    @Test
    void testDomainEnum_Values() {
        AuthInfo.DomainEnum[] values = AuthInfo.DomainEnum.values();
        assertEquals(2, values.length);
    }

    @Test
    void testDomainEnum_FromValue() {
        assertEquals(AuthInfo.DomainEnum.HEADERS, AuthInfo.DomainEnum.fromValue("HEADERS"));
        assertEquals(AuthInfo.DomainEnum.QUERY, AuthInfo.DomainEnum.fromValue("QUERY"));
    }

    @Test
    void testDomainEnum_FromValue_Invalid() {
        assertNull(AuthInfo.DomainEnum.fromValue("INVALID"));
    }
}
