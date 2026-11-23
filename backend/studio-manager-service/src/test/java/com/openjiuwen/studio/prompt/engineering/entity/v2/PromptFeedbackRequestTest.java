/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.entity.v2;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PromptFeedbackRequestTest {
    private final ObjectMapper mapper = new ObjectMapper();

    @Test
    void omittedInsertionPositionRemainsAbsent() throws Exception {
        PromptFeedbackRequest request = mapper.readValue(
            "{\"prompt\":\"Answer clearly\",\"feedback\":\"Use short sentences\"}",
            PromptFeedbackRequest.class);

        assertNull(request.getInsert_pos_index());
        JsonNode forwarded = mapper.readTree(mapper.writeValueAsString(request));
        assertTrue(forwarded.path("insert_pos_index").isNull());
    }

    @Test
    void explicitNullDoesNotSelectInsertion() throws Exception {
        PromptFeedbackRequest request = mapper.readValue(
            "{\"prompt\":\"Answer clearly\",\"feedback\":\"Be brief\",\"insert_pos_index\":null}",
            PromptFeedbackRequest.class);

        assertNull(request.getInsert_pos_index());
    }

    @Test
    void builderPreservesAnUnspecifiedPosition() {
        PromptFeedbackRequest request = PromptFeedbackRequest.builder()
            .prompt("Answer clearly")
            .feedback("Be brief")
            .build();

        assertNull(request.getInsert_pos_index());
    }

    @ParameterizedTest
    @ValueSource(ints = {0, 4})
    void explicitInsertionPositionsSurviveForwarding(int position) throws Exception {
        PromptFeedbackRequest request = mapper.readValue(
            "{\"prompt\":\"Answer clearly\",\"feedback\":\"Add detail\",\"insert_pos_index\":"
                + position + "}", PromptFeedbackRequest.class);

        JsonNode forwarded = mapper.readTree(mapper.writeValueAsString(request));
        assertEquals(position, forwarded.path("insert_pos_index").intValue());
    }
}
