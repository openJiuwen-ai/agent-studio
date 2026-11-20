/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.agentbase.service.clean.pipeline.subtask;

import com.openjiuwen.studio.agent.agentbase.mapper.CommonCleanMapper;
import com.openjiuwen.studio.agent.foundation.base.exception.AgentBaseException;

import org.apache.ibatis.builder.xml.XMLMapperBuilder;
import org.apache.ibatis.mapping.Environment;
import org.apache.ibatis.session.Configuration;
import org.apache.ibatis.session.SqlSessionFactoryBuilder;
import org.h2.jdbcx.JdbcDataSource;
import org.junit.jupiter.api.Test;
import org.mybatis.spring.SqlSessionTemplate;
import org.mybatis.spring.transaction.SpringManagedTransactionFactory;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.EnableTransactionManagement;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

/**
 * TenantCleanKnowledgeTableSubtask 事务回滚集成测试（H2 + Spring 事务代理）。
 */
class TenantCleanKnowledgeTableSubtaskTransactionTest {

    private static JdbcDataSource newDataSource() {
        JdbcDataSource dataSource = new JdbcDataSource();
        dataSource.setURL("jdbc:h2:mem:" + UUID.randomUUID() + ";DB_CLOSE_DELAY=-1;LOCK_TIMEOUT=5000");
        dataSource.setUser("sa");
        dataSource.setPassword("");
        return dataSource;
    }

    private static CommonCleanMapper buildMapper(JdbcDataSource dataSource) {
        Configuration configuration = new Configuration(
            new Environment("test", new SpringManagedTransactionFactory(), dataSource));
        try (var xml = TenantCleanKnowledgeTableSubtaskTransactionTest.class
            .getResourceAsStream("/mapper/CommonCleanMapper.xml")) {
            assertNotNull(xml, "mapper/CommonCleanMapper.xml 必须在测试 classpath 中");
            new XMLMapperBuilder(xml, configuration, "mapper/CommonCleanMapper.xml",
                configuration.getSqlFragments()).parse();
        } catch (Exception e) {
            throw new IllegalStateException("加载 CommonCleanMapper.xml 失败", e);
        }
        return new SqlSessionTemplate(new SqlSessionFactoryBuilder().build(configuration))
            .getMapper(CommonCleanMapper.class);
    }

    private static AnnotationConfigApplicationContext newContext(JdbcDataSource dataSource,
        CommonCleanMapper mapper) {
        AnnotationConfigApplicationContext context = new AnnotationConfigApplicationContext();
        context.register(Transactions.class);
        context.registerBean(PlatformTransactionManager.class, () -> new DataSourceTransactionManager(dataSource));
        context.registerBean("commonCleanMapper", CommonCleanMapper.class, () -> mapper);
        context.registerBean("tenantCleanKnowledgeTableSubtask", TenantCleanKnowledgeTableSubtask.class,
            TenantCleanKnowledgeTableSubtask::new);
        context.refresh();
        return context;
    }

    @Test
    void executeCleanup_rollsBackAllDeletes_whenOneTableFails() throws Exception {
        JdbcDataSource dataSource = newDataSource();
        JdbcTemplate jdbc = new JdbcTemplate(dataSource);
        // 只创建前两张表；第三张表 t_knowledge_base_obs_config 故意不创建，使删除在第 3 张表时失败
        jdbc.execute("CREATE TABLE t_knowledge_test_record (id INT PRIMARY KEY, domain_id VARCHAR(64))");
        jdbc.execute("CREATE TABLE t_knowledge_base_obs_execute_record (id INT PRIMARY KEY, domain_id VARCHAR(64))");
        jdbc.update("INSERT INTO t_knowledge_test_record (id, domain_id) VALUES (1, 'd1'), (2, 'd1')");
        jdbc.update("INSERT INTO t_knowledge_base_obs_execute_record (id, domain_id) VALUES (1, 'd1')");

        CommonCleanMapper mapper = buildMapper(dataSource);
        try (var context = newContext(dataSource, mapper)) {
            TenantCleanKnowledgeTableSubtask subtask = context.getBean(TenantCleanKnowledgeTableSubtask.class);
            assertThrows(AgentBaseException.class, () -> subtask.executeCleanup("d1"));
        }

        // 事务回滚：前两张表已执行的 DELETE 必须被回滚，数据仍在
        assertEquals(2, jdbc.queryForObject(
            "SELECT COUNT(*) FROM t_knowledge_test_record WHERE domain_id = 'd1'", Integer.class));
        assertEquals(1, jdbc.queryForObject(
            "SELECT COUNT(*) FROM t_knowledge_base_obs_execute_record WHERE domain_id = 'd1'", Integer.class));
    }

    @Test
    void executeCleanup_commitsAllDeletes_whenAllTablesSucceed() throws Exception {
        JdbcDataSource dataSource = newDataSource();
        JdbcTemplate jdbc = new JdbcTemplate(dataSource);
        String[] tables = new TenantCleanKnowledgeTableSubtask().parseKnowledgeTables();
        for (String table : tables) {
            jdbc.execute("CREATE TABLE " + table + " (id INT PRIMARY KEY, domain_id VARCHAR(64))");
            jdbc.update("INSERT INTO " + table + " (id, domain_id) VALUES (1, 'd1')");
        }

        CommonCleanMapper mapper = buildMapper(dataSource);
        try (var context = newContext(dataSource, mapper)) {
            TenantCleanKnowledgeTableSubtask subtask = context.getBean(TenantCleanKnowledgeTableSubtask.class);
            subtask.executeCleanup("d1");
        }

        // 正常提交：所有表数据均已删除
        for (String table : tables) {
            assertEquals(0, jdbc.queryForObject(
                "SELECT COUNT(*) FROM " + table + " WHERE domain_id = 'd1'", Integer.class));
        }
    }

    @org.springframework.context.annotation.Configuration(proxyBeanMethods = false)
    @EnableTransactionManagement
    static class Transactions {
    }
}
