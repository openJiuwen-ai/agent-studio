/* Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.mapper;

import com.openjiuwen.studio.agent.common.dto.TriggerConfig;
import org.apache.ibatis.builder.xml.XMLMapperBuilder;
import org.apache.ibatis.mapping.Environment;
import org.apache.ibatis.session.Configuration;
import org.apache.ibatis.session.SqlSession;
import org.apache.ibatis.session.SqlSessionFactoryBuilder;
import org.apache.ibatis.transaction.jdbc.JdbcTransactionFactory;
import org.h2.jdbcx.JdbcDataSource;
import org.junit.jupiter.api.Test;

import java.util.Date;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class AgentTriggerPersistenceTest {
    @Test
    void savesEditsAndDeletesTriggersWithoutChangingModelOrOtherTenants() throws Exception {
        JdbcDataSource dataSource = new JdbcDataSource();
        dataSource.setURL("jdbc:h2:mem:" + UUID.randomUUID() + ";DB_CLOSE_DELAY=-1");
        Configuration configuration = new Configuration(new Environment("test", new JdbcTransactionFactory(), dataSource));
        configuration.getTypeHandlerRegistry().register("com.openjiuwen.studio.agent.manager.mapper.handler");
        try (var resource = getClass().getResourceAsStream("/mapper/AgentMapper.xml")) {
            new XMLMapperBuilder(resource, configuration, "mapper/AgentMapper.xml", configuration.getSqlFragments()).parse();
        }
        try (SqlSession session = new SqlSessionFactoryBuilder().build(configuration).openSession()) {
            var connection = session.getConnection();
            try (var statement = connection.createStatement()) {
                statement.execute("CREATE TABLE t_agent (agent_id VARCHAR, project_id VARCHAR, workspace_id VARCHAR, "
                    + "deleted BOOLEAN, trigger_list VARCHAR, updated_on TIMESTAMP, model VARCHAR)");
                statement.execute("INSERT INTO t_agent VALUES ('agent', 'project', 'workspace', false, '[]', NULL, 'keep-model')");
            }
            AgentMapper mapper = session.getMapper(AgentMapper.class);
            TriggerConfig trigger = new TriggerConfig().setTriggerId("poll-1").setType("POLLING")
                .setPollUrl("https://example.com/feed").setPrompt("before");
            assertEquals(1, mapper.updateTriggerList("project", "workspace", "agent", List.of(trigger), new Date()));
            trigger.setPrompt("after");
            assertEquals(1, mapper.updateTriggerList("project", "workspace", "agent", List.of(trigger), new Date()));
            assertEquals(0, mapper.updateTriggerList("wrong-project", "workspace", "agent", List.of(), new Date()));
            assertEquals(0, mapper.updateTriggerList("project", "wrong-workspace", "agent", List.of(), new Date()));
            try (var statement = connection.createStatement(); var rows = statement.executeQuery("SELECT * FROM t_agent")) {
                assertTrue(rows.next());
                assertEquals("keep-model", rows.getString("model"));
                assertTrue(rows.getString("trigger_list").contains("after"));
                assertNotNull(rows.getTimestamp("updated_on"));
            }
            assertEquals(1, mapper.updateTriggerList("project", "workspace", "agent", List.of(), new Date()));
            try (var statement = connection.createStatement(); var rows = statement.executeQuery("SELECT * FROM t_agent")) {
                assertTrue(rows.next());
                assertEquals("[]", rows.getString("trigger_list"));
                assertEquals("keep-model", rows.getString("model"));
            }
        }
    }
}
