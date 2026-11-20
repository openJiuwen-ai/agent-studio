/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.mapper;

import org.junit.jupiter.api.Test;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;
import org.xml.sax.ErrorHandler;
import org.xml.sax.SAXParseException;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * issue #1734 回归守卫：SkillMapper.xml 的 searchBySkillIds 是通用批量查询（9 处共用：
 * 资源存在性 validResourceExist / 引用关系 / agent skill 列表 / 导入导出 / IR 解析 / SkillAdapter /
 * 运行时资产导出归属校验），承载"资源存在/能否查到详情"语义，不是"广场是否可见"语义。
 * 曾经末尾硬编码 {@code AND t_skill.published_asset = '1'}，把"未上架 Skill"误判为"不存在"，
 * 致 validResourceExist 误报 RESOURCE_NOT_EXISTS（删除前引用确认弹框报"资源不存在"，但删除接口仍成功）。
 *
 * <p>本测试解析 classpath 真实 SkillMapper.xml，断言 searchBySkillIds 的 select 块不再含 published_asset 过滤，
 * 防止该过滤被重新加回。广场可见性过滤的合法位置是 {@code search}（带可选 publishedAsset 参数）。
 *
 * <p>实现说明：用 DOM 取 select 元素的 {@code getTextContent()}（仅含 TEXT/CDATA 节点，不含 XML 注释），
 * 而非 raw 字符串扫描——源文件中防回归注释也含 published_asset 字样，raw 扫描会误判。
 */
class SkillMapperXmlRegressionTest {

    private Document loadMapperXml() throws Exception {
        try (InputStream in = getClass().getClassLoader().getResourceAsStream("mapper/SkillMapper.xml")) {
            assertThat(in).as("mapper/SkillMapper.xml 须在 classpath").isNotNull();
            DocumentBuilderFactory f = DocumentBuilderFactory.newInstance();
            f.setNamespaceAware(false);
            DocumentBuilder db = f.newDocumentBuilder();
            db.setErrorHandler(new FailErrorHandler());
            Document doc = db.parse(in);
            doc.getDocumentElement().normalize();
            return doc;
        }
    }

    /** 定位指定 id 的 select 元素的文本内容（不含 XML 注释）。 */
    private String selectText(Document doc, String id) {
        NodeList selects = doc.getElementsByTagName("select");
        for (int i = 0; i < selects.getLength(); i++) {
            Element el = (Element) selects.item(i);
            if (id.equals(el.getAttribute("id"))) {
                return el.getTextContent();
            }
        }
        return null;
    }

    @Test
    void searchBySkillIds_doesNotFilterPublishedAsset() throws Exception {
        String text = selectText(loadMapperXml(), "searchBySkillIds");
        assertThat(text).as("searchBySkillIds select 须存在").isNotNull();
        // 查询结构完整：仍按 skill_id IN 批量查（未误删查询主体）
        assertThat(text).contains("skill_id IN");
        // 回归守卫（issue #1734）：通用批量查询不得再带 published_asset 过滤
        assertThat(text).as("searchBySkillIds 通用批量查询不得过滤 published_asset（issue #1734）")
            .doesNotContain("published_asset");
    }

    @Test
    void plazaListSearchQuery_stillOwnsPublishedAssetFilter() throws Exception {
        // 对照：广场列表查询 search 的 published_asset 过滤是合法的（带可选 publishedAsset 参数），不得被误删
        String search = selectText(loadMapperXml(), "search");
        assertThat(search).as("search select 须存在").isNotNull();
        assertThat(search).contains("published_asset");
    }

    private static final class FailErrorHandler implements ErrorHandler {
        @Override public void warning(SAXParseException e) { throw new RuntimeException(e); }
        @Override public void error(SAXParseException e) { throw new RuntimeException(e); }
        @Override public void fatalError(SAXParseException e) { throw new RuntimeException(e); }
    }
}
