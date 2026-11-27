/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.workflow.jiuwen.adapt;

import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.manager.dto.Message;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import com.openjiuwen.studio.agent.manager.enums.MessageRole;
import com.openjiuwen.studio.agent.manager.utils.IRUtils;

import org.apache.commons.lang3.StringUtils;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * 大模型节点转换IR
 *
 */
public class LLMNodeAdapter extends AbstractIRNodeAdapter {
    /**
     * 开启历史会话
     */
    private static final String ENABLE_HISTORY = "enable_history";

    /**
     * prompt模板内容
     */
    private static final String TEMPLATE_CONTENT = "template_content";

    /**
     * 九问固定值部署模式字段
     */
    private static final String DEPLOY_MODE = "deployMode";

    /**
     * 九问固定值部署模式-workflow
     */
    private static final String WORK_FLOW = "workflow";

    /**
     * 响应格式
     */
    private static final String RESPONSE_FORMAT = "response_format";

    /**
     * 返回类型，支持json markdown和原始回复
     */
    private static final String FORMAT_INSTRUCTION = "format_instruction";

    /**
     * markdown格式返回
     */
    private static final String MARKDOWN_INSTRUCTION = "markdownInstruction";

    /**
     * json格式返回
     */
    private static final String JSON_INSTRUCTION = "jsonInstruction";

    /**
     * 历史会话大小
     */
    private static final String HISTORY_SIZE = "history_size";

    /**
     * 系统人设
     */
    private static final String SYSTEM_PROMPT = "system_prompt";

    /**
     * 大模型节点流式输出开关
     */
    private static final String STREAM = "stream";

    /**
     * 多模态理解模型图片字段
     */
    private static final String VISION = "vision";

    /**
     * 允许提示词中未声明入参的 {{...}} 按字面量保留
     */
    private static final String ALLOW_LITERAL_BRACES = "allow_literal_braces";

    @Override
    public Map<String, Object> adaptConfig(WorkflowNodeVO workflowNodeVo) {
        Map<String, Object> configs = new HashMap<>();
        Map<String, Object> nodeConfigs = workflowNodeVo.getConfigs();

        // 九问需要的固定值
        configs.put(DEPLOY_MODE, WORK_FLOW);

        configs.put(IRUtils.adaptKey(ENABLE_HISTORY), nodeConfigs.get(ENABLE_HISTORY));
        adaptTemplate(configs, nodeConfigs);
        if (nodeConfigs.get(STREAM) != null) {
            configs.put(STREAM, nodeConfigs.get(STREAM));
        }
        // 默认 false：与历史行为一致，未声明 {{...}} 仍会报错
        Object allowLiteralBraces = nodeConfigs.getOrDefault(ALLOW_LITERAL_BRACES, false);
        configs.put(IRUtils.adaptKey(ALLOW_LITERAL_BRACES),
                Boolean.parseBoolean(String.valueOf(allowLiteralBraces)));

        // 适配多模态理解模型支持图片
        if (nodeConfigs.get(VISION) != null) {
            configs.put(VISION, nodeConfigs.get(VISION));
        }

        // 适配输出格式
        adaptRespFormat(configs, nodeConfigs);

        // 适配九问模型
        adaptModel(configs, nodeConfigs);
        configs.put(IRUtils.adaptKey(HISTORY_SIZE), nodeConfigs.get(HISTORY_SIZE));

        // 节点是否启用记忆的配置
        Object enableMemory = nodeConfigs.getOrDefault(Constants.Workflow.ENABLE_MEMORY, false);
        boolean enableMemoryBool = Boolean.parseBoolean(enableMemory.toString());
        configs.put(IRUtils.adaptKey(MEMORY), Map.of("enable", enableMemoryBool));

        return configs;
    }

    /**
     * 适配响应格式
     *
     * @param jiuwenConfigs 九问配置
     * @param eiConfigs ei配置
     */
    private void adaptRespFormat(Map<String, Object> jiuwenConfigs, Map<String, Object> eiConfigs) {
        Map<String, String> respFormatMap = new HashMap<>();
        jiuwenConfigs.put(IRUtils.adaptKey(RESPONSE_FORMAT), respFormatMap);

        // 设置type
        String format = eiConfigs.getOrDefault(RESPONSE_FORMAT, "text").toString();
        respFormatMap.put("type", format);

        // 设置instruction
        String instruction = eiConfigs.getOrDefault(FORMAT_INSTRUCTION, "").toString();
        if ("markdown".equalsIgnoreCase(format)) {
            respFormatMap.put(MARKDOWN_INSTRUCTION, instruction);
        } else if ("json".equalsIgnoreCase(format)) {
            respFormatMap.put(JSON_INSTRUCTION, instruction);
        }
    }

    @Override
    public String getNodeType() {
        return NodeType.LLM.getIrType();
    }

    /**
     * 适配prompt模板
     *
     * @param jiuwenConfigs 九问configs
     * @param nodeConfigs 节点配置
     */
    private void adaptTemplate(Map<String, Object> jiuwenConfigs, Map<String, Object> nodeConfigs) {
        List<Message> messageList = new ArrayList<>();

        // 系统人设新增
        Object systemPrompt = nodeConfigs.get(SYSTEM_PROMPT);
        if (systemPrompt != null && StringUtils.isNotEmpty(systemPrompt.toString())) {
            Message systemMessage = new Message();
            systemMessage.setRole(MessageRole.SYSTEM.name().toLowerCase(Locale.ROOT));
            systemMessage.setContent(systemPrompt.toString());
            messageList.add(systemMessage);
        }
        // 用户请求模板
        Object template = nodeConfigs.get(TEMPLATE_CONTENT);
        String templateContent = template == null ? "" : template.toString();
        Message message = new Message();
        message.setRole(MessageRole.USER.name().toLowerCase(Locale.ROOT));
        message.setContent(templateContent);
        messageList.add(message);
        jiuwenConfigs.put(IRUtils.adaptKey(TEMPLATE_CONTENT), messageList);
    }
}
