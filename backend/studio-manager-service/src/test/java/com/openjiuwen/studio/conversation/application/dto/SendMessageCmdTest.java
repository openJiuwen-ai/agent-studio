package com.openjiuwen.studio.conversation.application.dto;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.stream.StreamSupport;

import static org.junit.jupiter.api.Assertions.*;

class SendMessageCmdTest {

    @Test
    void testData_SetsAndGetsAllFields() {
        SendMessageCmd cmd = new SendMessageCmd();
        cmd.setQuery("你好");
        cmd.setModelDeploymentId("deploy-001");

        assertNotNull(cmd);
        assertEquals("你好", cmd.getQuery());
        assertEquals("deploy-001", cmd.getModelDeploymentId());
    }

    @Test
    void testSerialization_UsesJsonPropertySnakeCase() throws JsonProcessingException {
        SendMessageCmd cmd = new SendMessageCmd();
        cmd.setQuery("你好");
        cmd.setModelDeploymentId("deploy-001");

        ObjectMapper mapper = new ObjectMapper();
        String json = mapper.writeValueAsString(cmd);
        JsonNode tree = mapper.readTree(json);

        // 对外契约：JSON 键是下划线，不是驼峰
        assertTrue(tree.has("model_deployment_id"));
        assertFalse(tree.has("modelDeploymentId"));
    }

    @Test
    void testDeserialization_AcceptsSnakeCaseJson() throws JsonProcessingException {
        ObjectMapper mapper = new ObjectMapper();
        SendMessageCmd back = mapper.readValue(
                "{\"query\":\"你好\",\"model_deployment_id\":\"deploy-001\"}", SendMessageCmd.class);

        assertEquals("你好", back.getQuery());
        assertEquals("deploy-001", back.getModelDeploymentId());
    }

    @Test
    void serialization_推荐技能使用下划线字段且保留顺序() throws Exception {
        SendMessageCmd cmd = new SendMessageCmd();
        cmd.setQuery("整理并润色");
        cmd.setModelDeploymentId("m1");
        cmd.setRecommendedSkillIds(List.of("s2", "s1"));

        JsonNode json = new ObjectMapper().readTree(new ObjectMapper().writeValueAsString(cmd));

        assertEquals(List.of("s2", "s1"),
            StreamSupport.stream(json.get("recommended_skill_ids").spliterator(), false)
                .map(JsonNode::asText).toList());
        assertFalse(json.has("recommendedSkillIds"));
    }

    @Test
    void deserialization_推荐技能保序且缺省或空值归一为空列表() throws Exception {
        ObjectMapper mapper = new ObjectMapper();

        SendMessageCmd ordered = mapper.readValue(
            "{\"recommended_skill_ids\":[\"s2\",\"s1\",\"s2\"]}", SendMessageCmd.class);
        SendMessageCmd omitted = mapper.readValue("{}", SendMessageCmd.class);
        SendMessageCmd explicitNull = mapper.readValue("{\"recommended_skill_ids\":null}", SendMessageCmd.class);

        assertEquals(List.of("s2", "s1", "s2"), ordered.getRecommendedSkillIds());
        assertEquals(List.of(), omitted.getRecommendedSkillIds());
        assertEquals(List.of(), explicitNull.getRecommendedSkillIds());
    }
}
