/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.config;

import feign.Client;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.security.SecureRandom;
import java.security.cert.X509Certificate;

import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSocketFactory;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;

/**
 * Feign配置
 */
@Configuration
public class FeignIgnoreSSLConfig {

    @Bean
    public Client feignClient() {
        // 第三参 disableRequestBuffering=false：请求体先缓冲再发送（Feign 13 之前的默认行为）。
        // 若走流式（streaming mode），JDK HttpURLConnection 收到 401 时会触发内置认证协商，
        // 将响应体（getErrorStream）消费掉，导致 Feign 异常 contentUTF8() 为空，
        // builder 返回的错误详情（如 "Token is invalid."）无法透传给前端。buffered 模式下不受影响。
        return new Client.Default(sslSocketFactory(), (host, session) -> true, false);
    }

    private SSLSocketFactory sslSocketFactory() {
        try {
            SSLContext sslContext = SSLContext.getInstance("TLSv1.2");
            sslContext.init(null, new TrustManager[]{new X509TrustManager() {
                @Override
                public void checkClientTrusted(X509Certificate[] chain, String authType) {}
                @Override
                public void checkServerTrusted(X509Certificate[] chain, String authType) {}
                @Override
                public X509Certificate[] getAcceptedIssuers() {return new X509Certificate[0];}
            }}, new SecureRandom());
            return sslContext.getSocketFactory();
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
