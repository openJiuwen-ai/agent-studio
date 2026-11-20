/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.mapper;

import org.junit.jupiter.api.Test;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;
import org.xml.sax.ErrorHandler;
import org.xml.sax.InputSource;
import org.xml.sax.SAXParseException;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import java.io.InputStream;
import java.io.StringReader;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * issue #1734 回归守卫：SkillMapper.xml 的 searchBySkillIds 是通用批量查询（9 处共用：
 * 资源存在性 validResourceExist / 引用关系 / agent skill 列表 / 导入导出 / IR 解析 / SkillAdapter /
 * 运行时资产导出归属校验），承载"资源存在/能否查到详情"语义。
 *
 * <p>原 bug：末尾硬编码 {@code AND t_skill.published_asset = '1'}，把"未上架 Skill"误判为"不存在"，
 * 致 validResourceExist 误报 RESOURCE_NOT_EXISTS（删除前引用确认报资源不存在，但删除走另一查询仍成功）。
 *
 * <p>巡检问题3（domain 隔离）：移除硬编码过滤后该查询无归属隔离，跨 domain 未上架草稿存在性/元数据泄露。
 * 修复为 {@code WHERE (domain_id = #{domainId} OR published_asset = '1')}——本 domain 全部（含未上架草稿）
 * + 跨 domain 仅已上架（广场可见语义，堵跨 domain 未上架草稿泄露）。粒度与 getSkillPackageContent /
 * deleteStudioSkill / searchBySkillIdAndDomainId 对齐（同 domain 内跨 workspace/project 预览属于既有契约）。
 * 本测试断言该隔离条件存在，防回退到无隔离或硬编码过滤。
 *
 * <p>巡检问题2（DTD 外部加载）：JAXP 默认加载外部 DTD（mybatis.org），离线 CI 会 UnknownHostException。
 * 关闭 load-external-dtd + 设空 EntityResolver，使解析不访问网络。
 *
 * <p>实现说明：用 DOM 取 select 元素的 {@code getTextContent()}（仅含 TEXT/CDATA 节点，不含 XML 注释），
 * 而非 raw 字符串扫描——源文件中注释也含 published_asset 字样，raw 扫描会误判。
 */
class SkillMapperXmlRegressionTest {

    private static final Logger log = LoggerFactory.getLogger(SkillMapperXmlRegressionTest.class);

    private Document loadMapperXml() throws Exception {
        try (InputStream in = getClass().getClassLoader().getResourceAsStream("mapper/SkillMapper.xml")) {
            assertThat(in).as("mapper/SkillMapper.xml 须在 classpath").isNotNull();
            DocumentBuilderFactory f = DocumentBuilderFactory.newInstance();
            f.setNamespaceAware(false);
            // 巡检问题2：关闭外部 DTD 加载，避免离线 CI 访问 mybatis.org 抛 UnknownHostException
            f.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
            DocumentBuilder db = f.newDocumentBuilder();
            // 双保险：空 EntityResolver，解析时不发起任何外部请求
            db.setEntityResolver((publicId, systemId) -> new InputSource(new StringReader("")));
            db.setErrorHandler(new LenientErrorHandler());
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
    void searchBySkillIds_domainIsolation_failClosedOnEmptyDomain() throws Exception {
        String text = selectText(loadMapperXml(), "searchBySkillIds");
        assertThat(text).as("searchBySkillIds select 须存在").isNotNull();
        // 查询结构完整：仍按 skill_id IN 批量查（未误删查询主体）
        assertThat(text).contains("skill_id IN");
        // 隔离条件（issue #1734 巡检问题3）：domainId 非空分支含 (domain_id=? OR published_asset='1')
        //   ——本 domain 全部（含未上架草稿）+ 跨 domain 仅已上架（广场可见语义，与 getSkillPackageContent 对齐）
        assertThat(text).contains("domain_id");
        assertThat(text).contains("OR");
        // 巡检问题1（fail-closed）：choose/when/otherwise 双分支——getTextContent 只留文本节点（标签被去），
        //   故验证两个分支的文本都在：when 的 "domain_id = #{domainId} ... OR ... published_asset='1'"
        //   + otherwise 的兜底 "published_asset='1'"（domainId 空时仅已上架可见，未上架草稿不跨 domain 泄露）。
        //   出现 2 次 published_asset = '1' 即证明 choose 双分支结构存在（when 内 OR + otherwise 兜底），
        //   避免退化为无 otherwise 的单 <if>（domainId 空时无过滤全量泄露）。
        int publishedAssetCount = countOccurrences(text, "published_asset = '1'");
        assertThat(publishedAssetCount)
            .as("searchBySkillIds 须 choose 双分支：when(domainId非空,OR内) + otherwise(domainId空兜底) 各含 published_asset='1'（issue #1734 巡检问题1 fail-closed）")
            .isGreaterThanOrEqualTo(2);
    }

    private static int countOccurrences(String text, String sub) {
        int count = 0, idx = 0;
        while ((idx = text.indexOf(sub, idx)) != -1) {
            count++;
            idx += sub.length();
        }
        return count;
    }

    @Test
    void plazaListSearchQuery_stillOwnsPublishedAssetFilter() throws Exception {
        // 对照：广场列表查询 search 的 published_asset 过滤是合法的（带可选 publishedAsset 参数），不得被误删
        String search = selectText(loadMapperXml(), "search");
        assertThat(search).as("search select 须存在").isNotNull();
        assertThat(search).contains("published_asset");
    }

    /**
     * 巡检问题2：error/fatalError 仍抛（真正的解析错误必须让测试失败），
     * 但 warning 只记录日志不抛——避免离线/网络抖动产生的 warning 误杀测试。
     */
    private static final class LenientErrorHandler implements ErrorHandler {
        @Override public void warning(SAXParseException e) {
            log.warn("SkillMapperXmlRegressionTest parse warning: {}", e.getMessage());
        }
        @Override public void error(SAXParseException e) { throw new RuntimeException(e); }
        @Override public void fatalError(SAXParseException e) { throw new RuntimeException(e); }
    }
}
