/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.config;

import com.openjiuwen.studio.agent.manager.filter.WorkspaceInterceptor;
import com.openjiuwen.studio.agent.manager.observability.ConversationContextInterceptor;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.ViewControllerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * 功能描述
 *
 */
@Configuration
public class WebConfig implements WebMvcConfigurer {
    // 显式注入Mapper
    @Autowired
    private WorkspaceInterceptor workspaceInterceptor;

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        registry.addResourceHandler("/favicon.ico").addResourceLocations("classpath:/static/favicon.ico");
    }

    @Override
    public void addViewControllers(ViewControllerRegistry registry) {
        registry.addViewController("/modelartsstudio-agent/").setViewName("forward:/modelartsstudio-agent/index.html");
        registry.addViewController("/modelartsstudio-agent").setViewName("forward:/modelartsstudio-agent/index.html");
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        // COM-05 §12.2：conversation 拦截器先于 WorkspaceInterceptor，
        // 使 Workspace 日志能看到已安装的 conversation-id
        registry.addInterceptor(new ConversationContextInterceptor())
            .addPathPatterns("/v1/**")
            .addPathPatterns("/v2/**");
        // 注册拦截器，并指定拦截的路径
        registry.addInterceptor(workspaceInterceptor)
            .addPathPatterns("/v1/{project_id}/**")
            .addPathPatterns("/v2/{project_id}/**");
    }
}
