# Studio 三方数据库二次开发适配指导

本文教你在**不改 Studio 产品源码**的前提下，自己做出一个「外部扩展包」，把 `studio-manager` 接到三方关系库（以 **SQL Server** 为完整示例；达梦 / Oracle 等按同一步骤改方言规则即可）。

**边界说明**：

- **范围**：本指南只覆盖 Java 侧 `studio-manager`（平台管理面元数据存储）。Python 侧 `agent_builder` / `studio-builder` 的 `STORE_DB_*` **不在本期适配范围**（影响面小，可后续按需单独立项）。  
- 这是**部署侧外部扩展**，扩展包与方言规则需自行维护、按第 9 节验收；上游产品升级后可能要重测/微调改写规则。  
- 本文 SQL Server 示例可按步骤落地；**达梦 / Oracle 没有整份可直接粘贴的完整改写代码**，只保证流程相同（改识别、`rewrite()`、profile、DDL）。达梦 DM8 示例见 **附录 A**（摘自内部《Studio 数据库类型切换指导》）。  

- **机制 ≠ 零工作量**：主工作量通常在 **DDL 全量翻译**（产品 100+ 张表；第 6.2 节对照表是起点，不是全集）。目标库若 MySQL 兼容度高，Interceptor 改写面可能很小，但 DDL 仍要打磨。

---

## 0. 做完长什么样

最终你本地会有一个扩展目录（名字自定，下文用 `studio-db-ext`）：

```text
studio-db-ext/
  src/com/openjiuwen/studio/ext/
    ExtJdbcUrlDatabaseIdProvider.java
    VendorSqlRewriteInterceptor.java
    ExtDbAutoConfiguration.java
  src/META-INF/spring/
    org.springframework.boot.autoconfigure.AutoConfiguration.imports
  mapper/                           # 可选：databaseId=sqlserver 的外部 Mapper XML
    AgentMapperSqlServer.xml        # 例：FROM_UNIXTIME → DATEADD
    McpServerRatingMapperSqlServer.xml       # 必做：评分 upsert → MERGE
    PeEvaluationTaskMapperSqlServer.xml      # 必做：评估结果批量 upsert → MERGE
  classes/                          # javac 输出（打 jar 前把 mapper 拷到 classes/ext-mapper/）
  ext/
    studio-db-ext.jar               # 打好的扩展包（运行时进 loader.path）
  lib/                              # 仅运行时 JDBC 驱动（进 loader.path）
    mssql-jdbc-x.y.z.jre11.jar
  lib-compile/                      # 仅 javac 用，禁止放进 loader.path
    mybatis-3.5.x.jar
    spring-context-*.jar …
    spring-beans / spring-core / spring-jcl …
  config/
    application-sqlserver.yml
  sql/
    ddl_sqlserver.sql               # 你翻译后的建表脚本
    ddl_knowledge_sqlserver.sql
    dml_empty.sql
  bin/
    start-with-ext.sh
```

运行时把该目录挂进 manager 容器（如 `/opt/ext`），用包装脚本启动，使 **扩展 jar + `lib/` 里的 JDBC 驱动**进入应用类路径。`lib-compile/` 只在本机编译时用，不要挂进 `loader.path`，以免与产品自带的 Spring/MyBatis 版本冲突。

---

## 1. 原理（先看 1 分钟）

产品默认按 MySQL 语法跑。换三方库时，通过产品已开放的能力注入下面几件事：

| 做什么 | 用什么开放能力 |
|---|---|
| 告诉 MyBatis「当前是 sqlserver/dm/…」 | 自定义 `DatabaseIdProvider`（`@Primary` Bean） |
| 把 SQL 里的 MySQL 写法改成目标库写法 | MyBatis `Interceptor`（运行时改写） |
| 个别语句用目标库专用 SQL | 外部 Mapper XML（同 namespace/id，语句带 `databaseId=sqlserver`；`mapper-locations` 里外部路径写在内置前，见步骤 3.6） |
| 加载你的扩展 jar 和 JDBC 驱动 | `PropertiesLauncher` + `-Dloader.path=...`（不要用 `java -jar`） |
| 换连接串、方言、DDL 路径 | 环境变量 / 外部 `application-*.yml` |

业务 REST 不用改；改的是**部署与扩展包**。

> Interceptor 适合改 **已变成 `?` 之后**仍可识别的碎片：LIMIT / 布尔 / 反引号 / `UUID()` / `NOW()` 等。  
> **`ON DUPLICATE KEY UPDATE`、`FROM_UNIXTIME` 等整段重写必须用外部 Mapper**（步骤 3.6）。  
> 原因：`StatementHandler.prepare` 时 `BoundSql` 里已是 `?`，ParameterMapping 已固定；若在 Interceptor 里再写回 `#{serverId}` 之类，会当字面量发出且参数个数对不上，必然失败。  
> 裸 MySQL `SELECT ... FOR UPDATE` 也不要指望 Interceptor 自动改；定时任务锁走 Quartz `MSSQLDelegate`。

---

## 2. 准备环境

1. JDK 17（与产品 manager 一致）  
2. 目标库已安装，能建库（示例库名 `agentbuilder`；产品默认部署里常见 `agent-builder`，**名字自定，只要与 JDBC URL 一致**）  
3. 已有可运行的 `studio-manager` 镜像/进程（仍连着原库也可以，稍后切换）  
4. 下载目标库 JDBC 驱动，放到 `studio-db-ext/lib/`（**仅驱动**；此目录会进运行时 `loader.path`）  
5. 为编译准备依赖 jar，放到 **`studio-db-ext/lib-compile/`**（与 `lib/` 分开）：
   - `mybatis-3.5.x.jar`（Interceptor API）
   - 编译 `@Configuration`：`spring-context` / `spring-beans` / `spring-core` / `spring-jcl`（版本接近产品即可）

> 驱动与编译依赖 jar **由你自行从厂商/Maven 中央仓库获取**，本文不附带二进制。  
> **不要**把 `lib-compile/` 里的 Spring/MyBatis 拷进 `lib/` 或写进 `loader.path`：扩展 class 已打进 `studio-db-ext.jar`，运行时只需驱动；再注入编译期副本可能覆盖产品 classpath 上的同名库。

---

## 3. 写扩展代码

包名可用 `com.openjiuwen.studio.ext`（示例），也可改成你们公司包名，但 AutoConfiguration 注册名要一致。

### 步骤 3.1 建目录

```bash
mkdir -p studio-db-ext/src/com/openjiuwen/studio/ext
mkdir -p studio-db-ext/src/META-INF/spring
mkdir -p studio-db-ext/{classes,ext,lib,lib-compile,config,sql,bin,mapper}
```

### 步骤 3.2 方言识别：`ExtJdbcUrlDatabaseIdProvider.java`

创建文件 `studio-db-ext/src/com/openjiuwen/studio/ext/ExtJdbcUrlDatabaseIdProvider.java`：

```java
package com.openjiuwen.studio.ext;

import org.apache.ibatis.mapping.DatabaseIdProvider;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.Properties;

public class ExtJdbcUrlDatabaseIdProvider implements DatabaseIdProvider {
    private Properties properties;

    @Override
    public void setProperties(Properties p) {
        this.properties = p;
    }

    @Override
    public String getDatabaseId(DataSource dataSource) throws SQLException {
        try (Connection conn = dataSource.getConnection()) {
            String url = conn.getMetaData().getURL();
            System.out.println("[ExtJdbc] JDBC URL = " + url);
            if (url != null) {
                String u = url.toLowerCase();
                if (u.contains("jdbc:dm:") || u.contains(":dm://")) return "dm";
                if (u.contains("oracle") || u.contains(":thin:@")) return "oracle";
                if (u.contains("sqlserver") || u.contains("jdbc:sqlserver:")) {
                    System.out.println("[ExtJdbc] detected SQL Server -> sqlserver");
                    return "sqlserver";
                }
                if (u.contains("postgresql")) return "postgres";
                // 与产品内置 JdbcUrlDatabaseIdProvider 一致：
                // jdbc:opengauss 表示 Studio 官方支持的 openGauss「MySQL 兼容模式」(DBCOMPATIBILITY='M')，
                // 应返回 mysql，以走 MySQL DDL/Mapper 分支；不要映射成 postgres。
                // 仅当你们明确使用 PostgreSQL 兼容库/协议（URL 通常含 postgresql）时才返回 postgres。
                if (u.contains("mysql") || u.contains("mariadb") || u.contains("opengauss")) return "mysql";
            }
            String product = conn.getMetaData().getDatabaseProductName();
            if (product != null) {
                String p = product.toLowerCase();
                if (p.contains("dm") || p.contains("dameng")) return "dm";
                if (p.contains("oracle")) return "oracle";
                if (p.contains("microsoft") || p.contains("sql server")) return "sqlserver";
                // openGauss 驱动的 DatabaseProductName 常报告为 PostgreSQL，不能只靠产品名判断；
                // 仍以 JDBC URL 是否含 opengauss 为准（见上方）。
            }
            return null;
        }
    }
}
```

达梦 / Oracle：保证 URL 能命中上面的分支即可。

### 步骤 3.3 SQL 改写：`VendorSqlRewriteInterceptor.java`

创建 `VendorSqlRewriteInterceptor.java`（SQL Server 完整可跑版本；其他库改 `rewrite()` 即可）。

> **SQL Server 分页注意（2012+，含 Azure SQL Edge）**：`OFFSET/FETCH` **必须**跟在 `ORDER BY` 后面。产品里大量存在性查询是裸 `LIMIT 1`（无 `ORDER BY`），不能一律改成 `OFFSET 0 FETCH`。规则：  
> - 已有 `ORDER BY` → `OFFSET … FETCH …`  
> - 仅 `LIMIT n`、无排序 → 改成 `SELECT TOP (n) …`（插在第一个 `SELECT`/`SELECT DISTINCT` 后）  
> - `LIMIT … OFFSET …` 或 `LIMIT offset,count` 且无排序 → 先补 `ORDER BY (SELECT NULL)` 再 `OFFSET/FETCH`（任意行语义，与 MySQL 无序 LIMIT 接近）  
>
> **时间函数 / 时区策略**：产品默认 `spring.jackson.time-zone: GMT+8`。MySQL `NOW()` 一般跟**会话/库时区**的墙上时间走。文档示例把 `NOW()` 改成 **`SYSDATETIME()`**（SQL Server 实例本地时间），请把目标库时区（或容器 `TZ`）配成与应用一致的 **GMT+8**，避免创建/更新时间静默偏移。若你坚持库内存 UTC，可改用 `SYSUTCDATETIME()`，但须同步把 Jackson/业务展示也按 UTC 理解，并改外部 Mapper 里的时间函数。`FROM_UNIXTIME`/`DATEADD` 针对的是 **Unix 纪元秒**（UTC 起点），与「`NOW` 用本地还是 UTC」是另一件事，不要混改。

```java
package com.openjiuwen.studio.ext;

import org.apache.ibatis.executor.statement.StatementHandler;
import org.apache.ibatis.mapping.BoundSql;
import org.apache.ibatis.mapping.ParameterMapping;
import org.apache.ibatis.plugin.Interceptor;
import org.apache.ibatis.plugin.Intercepts;
import org.apache.ibatis.plugin.Invocation;
import org.apache.ibatis.plugin.Plugin;
import org.apache.ibatis.plugin.Signature;
import org.apache.ibatis.reflection.MetaObject;
import org.apache.ibatis.reflection.SystemMetaObject;

import java.sql.Connection;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Properties;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Intercepts({
    @Signature(type = StatementHandler.class, method = "prepare",
        args = {Connection.class, Integer.class})
})
public class VendorSqlRewriteInterceptor implements Interceptor {

    private static final Pattern LIMIT_OFFSET =
        Pattern.compile("(?i)\\blimit\\s+(\\d+|\\?)\\s+offset\\s+(\\d+|\\?)");
    private static final Pattern LIMIT_COMMA =
        Pattern.compile("(?i)\\blimit\\s+(\\d+|\\?)\\s*,\\s*(\\d+|\\?)");
    private static final Pattern LIMIT_ONLY =
        Pattern.compile("(?i)\\blimit\\s+(\\d+|\\?)");
    private static final Pattern ORDER_BY =
        Pattern.compile("(?i)\\border\\s+by\\b");
    private static final Pattern SELECT_HEAD =
        Pattern.compile("(?i)\\bselect\\s+(distinct\\s+)?");
    private static final Pattern FETCH_NEXT_ZERO =
        Pattern.compile("(?i)\\boffset\\s+(\\d+|\\?)\\s+rows\\s+fetch\\s+next\\s+0\\s+rows\\s+only");
    private static final Pattern FETCH_NEXT_PARAM =
        Pattern.compile("(?i)\\bfetch\\s+next\\s+\\?\\s+rows\\s+only\\s*$");

    @Override
    public Object intercept(Invocation invocation) throws Throwable {
        StatementHandler handler = (StatementHandler) invocation.getTarget();
        BoundSql boundSql = handler.getBoundSql();
        String sql = boundSql.getSql();
        if (sql == null) {
            return invocation.proceed();
        }
        String originalSql = sql;
        String lower = sql.toLowerCase();
        if (needsRewrite(sql, lower)) {
            String rewritten = rewrite(sql);
            if (!rewritten.equals(sql)) {
                SystemMetaObject.forObject(boundSql).setValue("sql", rewritten);
                // limit ? offset ? → OFFSET ? FETCH ? 时两个 ? 文本相同，必须交换 ParameterMapping
                swapLimitOffsetParameterOrder(originalSql, boundSql);
                sql = rewritten;
                lower = sql.toLowerCase();
                System.out.println("[VendorSqlRewrite] rewrote dialect fragments");
            }
        }
        if (lower.contains("fetch next")) {
            clampZeroFetch(boundSql);
        }
        return invocation.proceed();
    }

    // 不要在 Interceptor 里处理 ON DUPLICATE KEY UPDATE：
    // prepare 时 BoundSql 已是 ? + ParameterMapping，整段换成带 #{...} 的 MERGE 无法重新绑定。
    // 评分 upsert 用步骤 3.6 外部 Mapper（databaseId=sqlserver 的 MERGE）。
    private static boolean needsRewrite(String sql, String lower) {
        return lower.contains("limit")
            || lower.contains(" false") || lower.contains(" true")
            || lower.contains("=false") || lower.contains("=true")
            || lower.contains(" is true") || lower.contains(" is false")
            || sql.indexOf('`') >= 0
            || lower.contains("uuid(") || lower.contains("now(");
    }

    /** SQL Server 完整规则；达梦/Oracle 请按厂商语法改此方法 */
    static String rewrite(String sql) {
        String s = sql;
        s = s.replaceAll("`([^`]+)`", "[$1]");                 // 反引号 -> []
        s = s.replaceAll("(?i)\\bUUID\\s*\\(\\s*\\)", "NEWID()");
        // 与产品 jackson GMT+8 对齐：用实例本地时间（请将 SQL Server/容器时区设为 GMT+8）。若选 UTC 策略则改为 SYSUTCDATETIME()。
        s = s.replaceAll("(?i)\\bNOW\\s*\\(\\s*\\)", "SYSDATETIME()");
        s = s.replaceAll("(?i)\\bis\\s+not\\s+true\\b", "<> 1");
        s = s.replaceAll("(?i)\\bis\\s+not\\s+false\\b", "<> 0");
        s = s.replaceAll("(?i)\\bis\\s+true\\b", "= 1");
        s = s.replaceAll("(?i)\\bis\\s+false\\b", "= 0");
        s = s.replaceAll("(?i)=\\s*true\\b", "= 1");
        s = s.replaceAll("(?i)=\\s*false\\b", "= 0");

        // OFFSET/FETCH 需 ORDER BY（SQL Server 2012+）。无排序时：LIMIT n → TOP；带 offset 则补 ORDER BY (SELECT NULL)。
        // 参数化 limit ? offset ? → OFFSET ? FETCH ? 后还须 swapLimitOffsetParameterOrder。
        Matcher m = LIMIT_OFFSET.matcher(s);
        if (m.find()) {
            String tail = hasOrderBy(s)
                ? "OFFSET $2 ROWS FETCH NEXT $1 ROWS ONLY"
                : "ORDER BY (SELECT NULL) OFFSET $2 ROWS FETCH NEXT $1 ROWS ONLY";
            return m.replaceAll(tail);
        }
        // MySQL LIMIT offset,count → 参数顺序本就是 (offset,count)，与 OFFSET/FETCH 一致，不必换映射
        m = LIMIT_COMMA.matcher(s);
        if (m.find()) {
            String tail = hasOrderBy(s)
                ? "OFFSET $1 ROWS FETCH NEXT $2 ROWS ONLY"
                : "ORDER BY (SELECT NULL) OFFSET $1 ROWS FETCH NEXT $2 ROWS ONLY";
            return m.replaceAll(tail);
        }
        m = LIMIT_ONLY.matcher(s);
        if (m.find()) {
            if (hasOrderBy(s)) {
                s = m.replaceAll("OFFSET 0 ROWS FETCH NEXT $1 ROWS ONLY");
            } else {
                String n = m.group(1);
                s = injectTop(m.replaceFirst(""), n);
            }
        }
        if (FETCH_NEXT_ZERO.matcher(s).find()) {
            s = FETCH_NEXT_ZERO.matcher(s)
                .replaceAll("OFFSET $1 ROWS FETCH NEXT 1 ROWS ONLY");
            s = forceEmptyBeforeOffset(s);
        }
        return s;
    }

    static boolean hasOrderBy(String sql) {
        return ORDER_BY.matcher(sql).find();
    }

    /** 在第一个 SELECT / SELECT DISTINCT 后插入 TOP (n)；适用于无 ORDER BY 的裸 LIMIT。 */
    static String injectTop(String sql, String n) {
        Matcher sel = SELECT_HEAD.matcher(sql);
        if (!sel.find()) {
            return sql;
        }
        String distinct = sel.group(1) == null ? "" : sel.group(1);
        return sql.substring(0, sel.start())
            + "SELECT " + distinct + "TOP (" + n + ") "
            + sql.substring(sel.end());
    }

    /**
     * 将 {@code limit ? offset ?} 改写成 {@code OFFSET ? FETCH ?} 后，
     * BoundSql 里 ? 仍按原顺序绑定 (limit, offset)，必须交换为 (offset, limit)。
     * 对应产品如 AgentMapper.queryAgentList 的 {@code limit #{limit} offset #{offset}}。
     */
    static void swapLimitOffsetParameterOrder(String originalSql, BoundSql boundSql) {
        if (originalSql == null || boundSql == null) return;
        Matcher m = LIMIT_OFFSET.matcher(originalSql);
        if (!m.find()) return;
        if (!"?".equals(m.group(1)) || !"?".equals(m.group(2))) return;
        int qBefore = 0;
        for (int i = 0; i < m.start(); i++) {
            if (originalSql.charAt(i) == '?') qBefore++;
        }
        List<ParameterMapping> mappings = boundSql.getParameterMappings();
        if (mappings == null || mappings.size() <= qBefore + 1) return;
        List<ParameterMapping> mutable = new ArrayList<>(mappings);
        Collections.swap(mutable, qBefore, qBefore + 1);
        SystemMetaObject.forObject(boundSql).setValue("parameterMappings", mutable);
    }

    static boolean clampZeroFetch(BoundSql boundSql) {
        String sql = boundSql.getSql();
        if (sql == null) return false;
        Matcher lit = FETCH_NEXT_ZERO.matcher(sql);
        if (lit.find()) {
            String patched = forceEmptyBeforeOffset(sql);
            patched = FETCH_NEXT_ZERO.matcher(patched)
                .replaceAll("OFFSET $1 ROWS FETCH NEXT 1 ROWS ONLY");
            SystemMetaObject.forObject(boundSql).setValue("sql", patched);
            return true;
        }
        String trimmed = sql.trim().replaceAll(";\\s*$", "");
        if (!FETCH_NEXT_PARAM.matcher(trimmed).find()) return false;
        List<ParameterMapping> mappings = boundSql.getParameterMappings();
        if (mappings == null || mappings.isEmpty()) return false;
        ParameterMapping fetchPm = mappings.get(mappings.size() - 1);
        Object val = readParam(boundSql, fetchPm.getProperty());
        if (!(val instanceof Number) || ((Number) val).longValue() != 0L) return false;
        SystemMetaObject.forObject(boundSql).setValue("sql", forceEmptyBeforeOffset(sql));
        writeParam(boundSql, fetchPm.getProperty(), 1);
        return true;
    }

    /**
     * FETCH 0 时强制空结果。不要用「AND 1=0」硬插：无 WHERE 时会非法，且 replaceFirst(ORDER BY)
     * 可能命中子查询。优先把已有 WHERE 改成 WHERE 1=0 AND …；否则在 OFFSET 前最近一个 ORDER BY
     * （或 OFFSET 本身）前插入 WHERE 1=0。
     */
    private static String forceEmptyBeforeOffset(String sql) {
        Matcher where = Pattern.compile("(?i)\\bwhere\\b").matcher(sql);
        if (where.find()) {
            return where.replaceFirst("WHERE 1 = 0 AND");
        }
        Matcher offset = Pattern.compile("(?i)\\soffset\\s+").matcher(sql);
        if (offset.find()) {
            int offsetAt = offset.start();
            String before = sql.substring(0, offsetAt);
            String after = sql.substring(offsetAt);
            Matcher ob = Pattern.compile("(?i)\\border\\s+by\\b").matcher(before);
            int lastOb = -1;
            while (ob.find()) {
                lastOb = ob.start();
            }
            if (lastOb >= 0) {
                return before.substring(0, lastOb) + " WHERE 1 = 0 " + before.substring(lastOb) + after;
            }
            return before + " WHERE 1 = 0 " + after;
        }
        return sql + " WHERE 1 = 0";
    }

    private static Object readParam(BoundSql boundSql, String prop) {
        try {
            if (boundSql.hasAdditionalParameter(prop)) {
                return boundSql.getAdditionalParameter(prop);
            }
            Object po = boundSql.getParameterObject();
            if (po == null) return null;
            MetaObject meta = SystemMetaObject.forObject(po);
            if (meta.hasGetter(prop)) return meta.getValue(prop);
            if (meta.hasGetter("pageSize")) return meta.getValue("pageSize");
        } catch (Exception ignored) { }
        return null;
    }

    private static void writeParam(BoundSql boundSql, String prop, Object value) {
        try {
            if (boundSql.hasAdditionalParameter(prop)) {
                boundSql.setAdditionalParameter(prop, value);
            }
            Object po = boundSql.getParameterObject();
            if (po == null) return;
            MetaObject meta = SystemMetaObject.forObject(po);
            if (meta.hasSetter(prop)) meta.setValue(prop, value);
            else if (meta.hasSetter("pageSize")) meta.setValue("pageSize", value);
        } catch (Exception ignored) { }
    }

    @Override
    public Object plugin(Object target) {
        return Plugin.wrap(target, this);
    }

    @Override
    public void setProperties(Properties properties) { }
}
```

### 步骤 3.4 注册 Bean：`ExtDbAutoConfiguration.java`

```java
package com.openjiuwen.studio.ext;

import org.apache.ibatis.mapping.DatabaseIdProvider;
import org.apache.ibatis.plugin.Interceptor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

@Configuration
public class ExtDbAutoConfiguration {

    @Bean
    @Primary
    public DatabaseIdProvider extDatabaseIdProvider() {
        return new ExtJdbcUrlDatabaseIdProvider();
    }

    @Bean
    public Interceptor vendorSqlRewriteInterceptor() {
        return new VendorSqlRewriteInterceptor();
    }
}
```

### 步骤 3.5 Spring Boot 自动装配清单

创建 `studio-db-ext/src/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`，内容**只有一行**：

```text
com.openjiuwen.studio.ext.ExtDbAutoConfiguration
```

### 步骤 3.6 外部 Mapper（处理 Interceptor 不好改的整段 SQL）

Interceptor 改不了或不适合改的语句（典型：`FROM_UNIXTIME`、整段 upsert），用**同 namespace、同 id、带 `databaseId="sqlserver"`** 的外部语句。MyBatis 按语句的 **`databaseId` 属性**选型，不是靠「路径靠前覆盖 SQL 文本」。

1. 在 `studio-db-ext/mapper/` 新建例如 `AgentMapperSqlServer.xml`（核心是把 `FROM_UNIXTIME(updated_at/1000)` 写成 `DATEADD(...)`）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
  "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="com.openjiuwen.studio.agent.manager.mapper.AgentMapper">
  <!-- 与产品内置语句同 id；仅当 DatabaseIdProvider 返回 sqlserver 时选用 -->
  <select id="selectByProjectIdAndSearchKey" databaseId="sqlserver"
          resultType="com.openjiuwen.studio.agent.manager.dto.AgentApplicationInfo">
    SELECT * FROM (
      SELECT agent_id AS id, name, icon, description, type, workspace_id,
             updated_on AS updated_at, prologue
      FROM t_agent
      WHERE project_id = #{projectId,jdbcType=VARCHAR} AND deleted = 0
      UNION ALL
      SELECT id, name, avatar AS icon, description, workflow_type AS type, workspace_id,
             DATEADD(SECOND, CAST(updated_at / 1000 AS INT),
                     CAST('1970-01-01' AS datetime2)) AS updated_at,
             NULL AS prologue
      FROM t_agent_workflow
      WHERE project_id = #{projectId,jdbcType=VARCHAR}
        AND (deleted IS NULL OR deleted = 0)
    ) t
    ORDER BY updated_at DESC
    OFFSET 0 ROWS FETCH NEXT 100 ROWS ONLY
  </select>
</mapper>
```

> 上面是**形态示例**；完整条件分支请对照产品内置同名语句补齐，或先跑通主链路再按日志缺啥补啥。

2. **`ON DUPLICATE KEY UPDATE`（必做，仓内已知全部）**：Interceptor **不要**整段改写成带 `#{...}` 的 MERGE。当前产品 mapper 里 ODKU 有且仅有两处，都要外部 `databaseId="sqlserver"` 语句：

| Mapper 语句 | 场景 |
|---|---|
| `McpServerRatingMapper.insertRating` | MCP 评分 upsert（动态分支：非 postgres 即 ODKU） |
| `PeEvaluationTaskMapper.batchInsertEvalResult` | 提示词工程：评估结果批量 upsert |

**(a) 评分** — `mapper/McpServerRatingMapperSqlServer.xml`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
  "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="com.openjiuwen.studio.agent.manager.mapper.McpServerRatingMapper">
  <update id="insertRating" databaseId="sqlserver">
    MERGE INTO ws_mcp_server_rating AS target
    USING (SELECT #{serverId} AS server_id,
                  #{tenantId} AS tenant_id,
                  #{score} AS score) AS source
    ON (target.server_id = source.server_id AND target.tenant_id = source.tenant_id)
    WHEN MATCHED THEN
      UPDATE SET score = source.score,
                 updated_date = SYSDATETIME()
    WHEN NOT MATCHED THEN
      INSERT (server_id, tenant_id, score, created_date, updated_date)
      VALUES (source.server_id, source.tenant_id, source.score,
              SYSDATETIME(), SYSDATETIME());
  </update>
</mapper>
```

**(b) 评估结果批量** — `mapper/PeEvaluationTaskMapperSqlServer.xml`（形态示例；字段/typeHandler 请对照产品内置补齐）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
  "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="com.openjiuwen.studio.prompt.engineering.mapper.PeEvaluationTaskMapper">
  <insert id="batchInsertEvalResult" databaseId="sqlserver">
    MERGE INTO t_pe_evaluation_result AS target
    USING (
      SELECT * FROM (VALUES
      <foreach collection="results" item="item" separator=",">
        (#{item.id,jdbcType=VARCHAR},
         #{item.evaluationTaskId,jdbcType=VARCHAR},
         #{item.promptId,jdbcType=VARCHAR},
         #{item.testNum,jdbcType=INTEGER},
         #{item.generateResult,jdbcType=VARCHAR},
         #{item.evalResult,typeHandler=com.openjiuwen.studio.prompt.engineering.mapper.handler.EvalResultHandler},
         #{item.evalFailedReason,jdbcType=VARCHAR},
         #{item.workspaceId,jdbcType=VARCHAR})
      </foreach>
      ) AS v(id, evaluation_task_id, prompt_id, test_num,
             generate_result, eval_result, eval_failed_reason, workspace_id)
    ) AS source
    ON (target.id = source.id)
    WHEN MATCHED THEN
      UPDATE SET generate_result = source.generate_result,
                 eval_result = source.eval_result,
                 eval_failed_reason = source.eval_failed_reason
    WHEN NOT MATCHED THEN
      INSERT (id, evaluation_task_id, prompt_id, test_num,
              generate_result, eval_result, eval_failed_reason, workspace_id)
      VALUES (source.id, source.evaluation_task_id, source.prompt_id, source.test_num,
              source.generate_result, source.eval_result, source.eval_failed_reason,
              source.workspace_id);
  </insert>
</mapper>
```

> SQL Server 的 `MERGE` 建议以分号结尾。升级产品后请再搜一遍 `(?i)on duplicate key update`，若新增语句须同样补外部 Mapper。

3. **`mapper-locations` 与加载语义**（易误解，请按此理解）：

   - **选型依据**：同 namespace/id 时，由语句上的 `databaseId` 与当前 `DatabaseIdProvider` 返回值匹配决定用哪份；内置无 `databaseId` 的默认句靠动态 `_databaseId`，**不会**因为你「多写了一个外部文件路径」就自动被覆盖。
   - **为何外部路径仍要写在内置前面**：MyBatis 会先注册匹配当前 `databaseId` 的语句，再尝试注册无 `databaseId` 的默认句；若默认句已先注册，再注册同 id 的 `databaseId=sqlserver` 语句会触发 StrictMap **already contains key**（duplicate statement id）。把 `classpath:ext-mapper/*.xml` 放在 `classpath*:mapper/...` **之前**，是为了让带 `databaseId` 的语句先注册，随后内置默认句会被跳过——**不是**「路径顺序 = SQL 覆盖优先级」。
   - **关于 `classpath*:mapper/*.xml` 与 `**/*.xml`**：二者会匹配到同一批内置资源；已加载资源靠 `isResourceLoaded` 跳过，**不能**指望这两行之间的顺序去重或提高外部 Mapper 优先级。产品默认就有这两行，外部 profile 保留即可，关键是**额外加上**且**写在最前**的 `ext-mapper` 条目。

---

## 4. 编译打 jar

在 `studio-db-ext` 目录执行（按你本机 jar 文件名改 classpath）：

```bash
cd studio-db-ext

# 编译（依赖取自 lib-compile/，不要用 lib/）
# Linux / macOS：classpath 用冒号 :
javac --release 17 \
  -cp "lib-compile/mybatis-3.5.17.jar:lib-compile/spring-context-6.2.8.jar:lib-compile/spring-beans-6.2.8.jar:lib-compile/spring-core-6.2.8.jar:lib-compile/spring-jcl-6.2.8.jar" \
  -d classes \
  src/com/openjiuwen/studio/ext/*.java

# Windows（cmd）把上面 -cp 里的冒号改成分号，例如：
# -cp "lib-compile\mybatis-3.5.17.jar;lib-compile\spring-context-6.2.8.jar;..."

# 拷贝 AutoConfiguration 清单进 classes
mkdir -p classes/META-INF/spring
cp src/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports \
   classes/META-INF/spring/

# 拷贝外部 Mapper（目录名须与第 5 节 mapper-locations 一致）
mkdir -p classes/ext-mapper
cp mapper/*.xml classes/ext-mapper/ 2>/dev/null || true

# 打包
jar cf ext/studio-db-ext.jar -C classes .

# 自检
jar tf ext/studio-db-ext.jar | head
```

确认 jar 内同时有：

- `com/openjiuwen/studio/ext/*.class`
- `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`
- （若做了 3.6）`ext-mapper/*.xml`

---

## 5. 写配置 profile

创建 `studio-db-ext/config/application-sqlserver.yml`：

```yaml
spring:
  main:
    allow-bean-definition-overriding: true
  sql:
    init:
      mode: never          # 建议先手工/脚本建表，再启动
      continue-on-error: true
  jpa:
    database-platform: org.hibernate.dialect.SQLServerDialect
    properties:
      hibernate:
        dialect: org.hibernate.dialect.SQLServerDialect
  quartz:
    properties:
      org:
        quartz:
          jobStore:
            driverDelegateClass: org.quartz.impl.jdbcjobstore.MSSQLDelegate

# ext-mapper 须在内置 mapper 之前（先注册 databaseId 专用语句，避免 StrictMap 同 id 冲突；见步骤 3.6）
mybatis:
  mapper-locations:
    - classpath:ext-mapper/*.xml
    - classpath*:mapper/*.xml
    - classpath*:mapper/**/*.xml

pagehelper:
  helper-dialect: sqlserver
  reasonable: true
```

达梦 / Oracle：把 `hibernate.dialect`、`pagehelper.helper-dialect`、Quartz `driverDelegateClass` 换成厂商文档推荐值；外部 Mapper 的 `databaseId` 与 `ExtJdbcUrlDatabaseIdProvider` 返回值保持一致。

---

## 6. 准备 DDL

### 6.1 从哪里来

产品自带的是 **MySQL 版**建表脚本，通常在 manager 安装包 / 镜像资源里：

| 文件（产品内路径） | 内容 |
|---|---|
| `sql/ddl.sql`（classpath） | manager 业务表 + 常见含 QRTZ |
| `sql/knowledge-base/ddl.sql` | 知识库表 |

获取方式（任选）：

1. 向交付方索取上述两份 MySQL DDL  
2. 从已部署的 `studio-manager` 镜像/安装目录中导出对应资源（打在 jar 内时为 `classpath:sql/...`）

拿到后：

1. 按 6.2 翻译成目标库语法  
2. 放到 `studio-db-ext/sql/`（如 `ddl_sqlserver.sql`、`ddl_knowledge_sqlserver.sql`）

> 库名：产品默认部署常见 `agent-builder`；本文示例用 `agentbuilder`。**两者都可，只要建库名与 `spring_datasource_url` 里的库名一致。**
### 6.2 SQL Server 常见替换（对照改）

> 下表**不是全集**。产品 DDL（含知识库）里还有一批 MySQL 写法，翻译器/手工翻译时要一并处理；以你导出的全量脚本实测为准。

| MySQL | SQL Server |
|---|---|
| `` `name` `` | `[name]` 或去掉引号 |
| `AUTO_INCREMENT` | `IDENTITY(1,1)` |
| `TINYINT(1)` | `BIT` 或 `TINYINT` |
| 整型显示宽度（如 `INT(11)`） | 去掉宽度（`INT`） |
| `DATETIME` / `TIMESTAMP` | `DATETIME2` |
| `TEXT` / `MEDIUMTEXT` / `LONGTEXT` / `*BLOB` | `NVARCHAR(MAX)` / `VARBINARY(MAX)` 等 |
| `ENUM(...)` | 改 `VARCHAR` + 约束，或目标库等价类型 |
| `unsigned` | 去掉或改用更大有符号类型 |
| `ENGINE=InnoDB` / `ROW_FORMAT` / 表级 `CHARSET` / `COLLATE=utf8mb4_*` | 删除 |
| 列级 `CHARACTER SET ... COLLATE ...` | 删除（表选项文档常写了，**列级也要剥**） |
| `ON UPDATE CURRENT_TIMESTAMP` | 删除或改触发器 |
| 内联 `UNIQUE KEY` / `KEY ...` / `USING BTREE` | 抽成 `CREATE UNIQUE INDEX` / `CREATE INDEX`（无名索引需自动命名，含 QRTZ） |
| `CREATE TABLE IF NOT EXISTS` | 用 `IF OBJECT_ID(...) IS NULL CREATE TABLE` 或预执行工具 |
| 个别表缺 `IF NOT EXISTS`（如历史映射类表） | 翻译时补幂等包裹，避免重复执行报错 |
| 一条 `ALTER` 多个 `ADD COLUMN` | 拆成多条 `ALTER`（部分目标库不支持同句多 ADD） |
| `ADD COLUMN ... AFTER col` | 去掉 `AFTER`（列定位子句） |
| 重复迁移 `ADD COLUMN`（列已在建表里） | 目标侧用幂等写法（如存在则跳过）；产品靠 `continue-on-error` 容忍，预建库不要依赖吞错 |
| 保留字作裸列名（如 `value`） | 加引号/方括号（`` `value` `` → `[value]`） |

### 6.3 翻译示例（单表对照）

产品 MySQL 原文（节选形态）大致如下：

```sql
CREATE TABLE IF NOT EXISTS `t_common_license_record` (
    `id` varchar(36) NOT NULL,
    `sku_code` varchar(64) NOT NULL,
    `created_date` timestamp NOT NULL,
    PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=Dynamic;
```

按 6.2 翻成 SQL Server 后，写入你的 `sql/ddl_sqlserver.sql`，形态如下：

```sql
IF OBJECT_ID(N'dbo.t_common_license_record', N'U') IS NULL
BEGIN
CREATE TABLE dbo.t_common_license_record (
    id varchar(36) NOT NULL,
    sku_code varchar(64) NOT NULL,
    created_date datetime2 NOT NULL,
    PRIMARY KEY (id)
);
END;
```

对照这一张表实际做了什么：

- 去掉反引号 `` ` ``；需要时可用 `[]`
- `timestamp` → `datetime2`
- 删除 `ENGINE` / `CHARSET` / `COLLATE` / `ROW_FORMAT` / `USING BTREE`
- `CREATE TABLE IF NOT EXISTS` → `IF OBJECT_ID(...) IS NULL` 再 `CREATE TABLE`

> 完整 `ddl_sqlserver.sql` / `ddl_knowledge_sqlserver.sql` 需对产品全部表按同样规则翻译，本文只给形态示例，不附带整份成品脚本。有自增列时另见对照表：`AUTO_INCREMENT` → `IDENTITY(1,1)`（如 `t_sessions`）。第一次全量翻译建议预留打磨时间（经验上约 1～2 天，视目标库与自动化程度而定）。

### 6.4 执行顺序建议

```text
1) 创建数据库 agentbuilder
2) 执行 ddl_sqlserver.sql（manager 表 + QRTZ）
3) 执行 ddl_knowledge_sqlserver.sql
4) dml 可先空文件
5) 抽查：表数量、t_sessions 是否 IDENTITY、QRTZ 表是否齐全
```

把空 DML 写成 `sql/dml_empty.sql`（可以只有一行注释）。

> **重要**：启动参数建议 `spring_sql_init_mode=never`，避免启动时半失败半成功。

---

## 7. 启动包装脚本

创建 `studio-db-ext/bin/start-with-ext.sh`（路径按镜像实际调整）：

```bash
#!/bin/bash
set -euo pipefail

APP_PATH=${APP_PATH:-/opt/cloud/studio-manager}
EXT_DIR=${EXT_DIR:-/opt/ext}
ACTIVE_PROFILES="${ACTIVE_PROFILES:-manager,sqlserver}"
APP_JAR="${APP_PATH}/app/studio-manager.jar"
# 只挂扩展 jar + JDBC 驱动目录。不要把 lib-compile/ 加进来。
LOADER_PATH="${EXT_DIR}/ext,${EXT_DIR}/lib"

echo "INFO: loader.path=${LOADER_PATH}"
echo "INFO: profiles=${ACTIVE_PROFILES}"
ls -la "${EXT_DIR}/ext" "${EXT_DIR}/lib" || true
# 若误把 mybatis/spring 放进 lib/，启动前应挪到 lib-compile/ 或删掉运行时副本

exec java -Xms512m -Xmx2048m \
  -Dfile.encoding=UTF-8 \
  -Dloader.path="${LOADER_PATH}" \
  -cp "${APP_JAR}" \
  org.springframework.boot.loader.launch.PropertiesLauncher \
  --spring.config.additional-location="${APP_PATH}/config/,optional:${EXT_DIR}/config/" \
  --spring.profiles.active="${ACTIVE_PROFILES}" \
  --logging.config="${APP_PATH}/config/log4j2.xml"
```

```bash
chmod +x studio-db-ext/bin/start-with-ext.sh
```

**禁止**再用裸 `java -jar studio-manager.jar`，否则扩展包进不了类路径。

> **`loader.path` 内容**：`${EXT_DIR}/ext`（扩展包）+ `${EXT_DIR}/lib`（**仅** JDBC 驱动）。`lib-compile/` 即使挂载进容器也不要写进 `LOADER_PATH`。

> **环境变量大小写**：部分部署会同时导出 `SPRING_DATASOURCE_URL`（大写）和 `spring_datasource_url`（小写）。Spring 对二者都认；若只改小写、大写仍指向旧 MySQL/MariaDB，进程可能「驱动已是目标库、URL 仍钉在旧库」。overlay / `.env` / 启动脚本里**两套都覆盖**（URL、username、password、driver 同理）。

---

## 8. 接到运行中的 manager

### 方式 A：Docker Compose overlay（推荐）

在原 compose 旁增加 overlay 文件，例如 `docker-compose.db-ext.yml`：

```yaml
services:
  studio-manager:
    volumes:
      - /绝对路径/studio-db-ext:/opt/ext:ro
    entrypoint: ["/bin/bash", "/opt/ext/bin/start-with-ext.sh"]
    environment:
      EXT_DIR: /opt/ext
      ACTIVE_PROFILES: manager,sqlserver
      # 小写（文档默认写法）。生产请启用加密，并用最小权限业务账号（不要用 sa）。
      spring_datasource_url: jdbc:sqlserver://<db-host>:1433;databaseName=agentbuilder;encrypt=true;trustServerCertificate=false
      spring_datasource_username: <app-db-user>
      spring_datasource_password: "<your-password>"
      spring_datasource_driver_class_name: com.microsoft.sqlserver.jdbc.SQLServerDriver
      # 大写：若原 .env / local-dev.env 已导出 SPRING_DATASOURCE_*，必须一并覆盖，否则仍可能连旧库
      SPRING_DATASOURCE_URL: jdbc:sqlserver://<db-host>:1433;databaseName=agentbuilder;encrypt=true;trustServerCertificate=false
      SPRING_DATASOURCE_USERNAME: <app-db-user>
      SPRING_DATASOURCE_PASSWORD: "<your-password>"
      SPRING_DATASOURCE_DRIVER_CLASS_NAME: com.microsoft.sqlserver.jdbc.SQLServerDriver
      spring_sql_init_mode: never
      spring_sql_manager_ddl: file:/opt/ext/sql/ddl_sqlserver.sql
      spring_sql_knowledge_ddl: file:/opt/ext/sql/ddl_knowledge_sqlserver.sql
      spring_sql_manager_dml: file:/opt/ext/sql/dml_empty.sql
      spring_sql_knowledge_dml: file:/opt/ext/sql/dml_empty.sql
      org_quartz_jobStore_driverDelegateClass: org.quartz.impl.jdbcjobstore.MSSQLDelegate
      SPRING_MAIN_ALLOW_BEAN_DEFINITION_OVERRIDING: "true"
```

然后：

```bash
docker compose -f docker-compose.yml -f docker-compose.db-ext.yml \
  up -d --no-deps --pull never --force-recreate studio-manager
```

> **连接安全**：上面默认 `encrypt=true;trustServerCertificate=false`，并使用**非 sa** 的业务账号。仅本地/无 TLS 的测试环境才可临时改为 `encrypt=false;trustServerCertificate=true`，且口令不要写进可提交的仓库；生产须校验服务器证书并授予最小库权限。

### 方式 B：已有进程

1. 把 `studio-db-ext` 放到机器固定目录  
2. 用 `start-with-ext.sh` 替换原启动命令  
3. 注入同上环境变量  

---

## 9. 验收（按顺序勾）

把 `<host>`、`<token>`、`<workspace_id>` 换成你的环境。

### 数据准备（空库必做，与方言无关）

全新目标库只有表、没有业务数据时，列表/导出可能「看起来失败」，容易误判成适配问题：

1. **Workspace**：至少一条可用工作空间；`status` 须为产品枚举合法值（常见为 `ENABLE`，写 `ACTIVE` 会被校验拒绝——以 mapper/校验代码为准）。  
2. **成员关系**：对应 `workspace_member`（或产品等价表），保证当前用户能访问该空间。  
3. **列表用种子数据**：若干 agent / workflow 等，便于验 9.3 / 9.4。  
4. **导出**：被导出资源的 `dsl_path`（或等价字段）须指向存储里真实存在的文件；种子写成 `NULL` 会导致读文件 500，与 SQL 方言无关。

从已有 MySQL 环境迁数据、或手工 INSERT 均可；本指南不附种子脚本。

### 9.1 启动与方言

```bash
# 健康检查
curl -sk http://<host>:31111/health
# 期望：200

# 日志应出现
# [ExtJdbc] detected SQL Server -> sqlserver
# 以及 Hibernate SQLServerDialect / Quartz MSSQLDelegate（视配置）
docker logs <manager容器> 2>&1 | grep -E 'ExtJdbc|SQLServerDialect|MSSQLDelegate|Started'
```

### 9.2 登录 / Token（simple-auth 部署）

```bash
curl -sk 'http://<host>:31111/auth/token?user_id=testUser&project_id=0'
# 期望：{"auth_token":"testUser|0"}
TOKEN='testUser|0'
```

### 9.3 主链路列表（注意参数）

```bash
WS=<你的workspace_id>

# Agent / 工作流：用 limit/offset
curl -sk -H "X-Auth-Token: $TOKEN" \
  "http://<host>:31111/v1/0/agent-manager/agents?workspace_id=$WS&limit=1&offset=0"

curl -sk -H "X-Auth-Token: $TOKEN" \
  "http://<host>:31111/v1/0/agent-manager/workflows?workspace_id=$WS&limit=2&offset=0"

# 知识库：必须是带 project_id 的正确路径
curl -sk -H "X-Auth-Token: $TOKEN" \
  "http://<host>:31111/v2/0/agent-manager/knowledge-bases?workspace_id=$WS&limit=10&offset=0"

# 提示词任务
curl -sk -H "X-Auth-Token: $TOKEN" \
  "http://<host>:31111/v2/0/prompt/tasks?workspace_id=$WS&limit=10&offset=0"
```

期望均为 **HTTP 200**（列表可为空，但不能是方言 SQL 500）。

### 9.4 分页

同一列表 `limit=2&offset=0` 与 `limit=2&offset=2`，条数截断且两页 ID 不重叠。

### 9.5 导入导出

1. 创建或选定一个 `workflow_id`  
2. `POST .../workflows/export` 得到 jsonl  
3. `POST .../workflows/import?import_workflows=<该workflow_id>&import_tools=` 上传文件  
4. 期望 `succeed_len >= 1`  

> `import_workflows` 填 **ID**，不要填 `true`。

### 9.6 会话表 IDENTITY（可选但建议）

用 JDBC 对 `t_sessions` 做插入并 `getGeneratedKeys`，确认能取到自增主键。

### 9.7 MCP 评分 upsert（`ON DUPLICATE` → MERGE）

产品 ODKU 目前两处：评分 `insertRating`（本小节）与评估 `batchInsertEvalResult`（跑评估任务时覆盖；外部 Mapper 见步骤 3.6）。库中先有一条可评分的 MCP server 记录后：

```bash
# 第一次：插入
curl -sk -X POST -H "X-Auth-Token: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"server_id":"<mcp_server_id>","score":"4"}' \
  "http://<host>:31111/v1/0/mcp/server/rating?workspace_id=$WS"
# 期望：HTTP 200

# 第二次：更新同一 (server_id, tenant) ，仍应成功且库中只有 1 行
curl -sk -X POST -H "X-Auth-Token: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"server_id":"<mcp_server_id>","score":"9"}' \
  "http://<host>:31111/v1/0/mcp/server/rating?workspace_id=$WS"
# 期望：HTTP 200；查 ws_mcp_server_rating 该 server 仅 1 行且 score=9
```

若报 `ON DUPLICATE` 语法错误：说明仍在走内置默认 `insertRating`（其 `_databaseId != 'postgres'` 分支）——检查 jar 内是否有带 **`databaseId="sqlserver"`** 的 `ext-mapper/McpServerRatingMapperSqlServer.xml`、`DatabaseIdProvider` 是否返回 `sqlserver`、以及 `mapper-locations` 是否包含且将 `ext-mapper` 写在内置路径之前（否则可能启动期 duplicate，或根本未加载外部语句）。

### 9.8 回滚

去掉 overlay / 恢复原环境变量与原 `entrypoint`，确认仍能连回原库并 `health=200`。

### 9.9 建议顺带确认（非阻塞）

| 项 | 做法 |
|---|---|
| Quartz 方言 | 日志出现 `MSSQLDelegate`；`QRTZ_SCHEDULER_STATE` 有签到行 |
| 列表参数 | 分页用 `limit`/`offset`；不要用 `page_size` 当截断依据 |
| 工作流 DELETE | 若失败且日志含 `UUID()`，确认已改写为 `NEWID()` |

---

## 10. 出问题怎么办（按日志对）

| 现象 | 处理 |
|---|---|
| 启动了但扩展没生效 | 是否仍用 `java -jar`？改为 PropertiesLauncher；检查 `loader.path`、jar 内 AutoConfiguration 清单 |
| 启动后 Spring/MyBatis 类冲突或怪异 NoSuchMethodError | 检查 `lib/` 是否混入了编译用 `mybatis`/`spring-*`；只保留 JDBC 驱动，编译依赖留在 `lib-compile/` |
| 驱动已是目标库但 URL 仍是 mariadb/mysql | 同时覆盖 `SPRING_DATASOURCE_URL` 与 `spring_datasource_url`（及 username/password/driver 大小写两套） |
| 列表空 / 导出读文件 500 | 先查 §9「数据准备」：workspace 状态、种子数据、`dsl_path` 是否指向真实文件 |
| `Invalid column name 'false'` | Interceptor 未加载或未改写布尔；查日志是否有 `[VendorSqlRewrite]` |
| `` Incorrect syntax near '`' `` | 补反引号改写 |
| `UUID()` 相关失败 | 确认 `UUID()`→目标库函数已写入 `rewrite()` |
| `FETCH NEXT 0` | 确认 `clampZeroFetch` 生效 |
| `Incorrect syntax near 'OFFSET'`（无 ORDER BY） | 裸 `LIMIT n` 须走 `TOP (n)`，带 offset 须补 `ORDER BY`；勿一律改成 `OFFSET 0 FETCH` |
| 分页 limit/offset 行数错乱或像互换 | 参数化 `limit ? offset ?` 改写后是否调用了 `swapLimitOffsetParameterOrder` |
| 401 且 TOKEN 为空 | `TOKEN='testUser|0'` 必须加引号，否则 `|` 被 shell 当成管道 |
| `FROM_UNIXTIME` / 日期函数报错 | Interceptor 一般不改；补带 `databaseId` 的外部 Mapper（步骤 3.6）并用 `DATEADD`；确认 `ext-mapper` 已进 `mapper-locations` 且在内置前 |
| `ON DUPLICATE KEY UPDATE` 语法错 | 补齐两处外部 MERGE：`insertRating` 与 `batchInsertEvalResult`；确认 Provider 返回 `sqlserver` |
| 创建/更新时间差约 8 小时 | 检查库/容器时区是否与 `jackson` 的 GMT+8 一致；`NOW`→`SYSDATETIME` 策略下勿混用 `SYSUTCDATETIME` |
| `FOR UPDATE` 语法错 | 不要指望 Interceptor 自动改写裸 MySQL `FOR UPDATE`；定时任务依赖 Quartz `MSSQLDelegate`；业务 SQL 改用 `WITH (UPDLOCK)` 等目标库写法（外部 Mapper） |
| duplicate statement id / already contains key | 同 id 的 `databaseId` 专用语句须先于无 `databaseId` 的内置默认句注册：把 `ext-mapper` 写在 `mapper-locations` 最前 |
| 导入一直 0 成功 | `import_*=` 改成真实资源 ID |
| 知识库 400 项目 ID | 换正确带 `{project_id}` 的 URL |
| 表缺失但进程起来了 | `continue-on-error` 吞错；改用预建表 + `init_mode=never` |
| 带插件导出缺版本 | 同步工具/版本元数据表，不是方言问题 |
| Windows 编译找不到类 | `-cp` 分隔符用 `;`，不要用 Linux 的 `:` |

每出现一次 SQL 500：从 manager 日志复制完整 SQL → 在 Interceptor 增加一条改写规则 **或** 增加外部 Mapper → 重新编译打包 → 重启。

---

## 11. 换到达梦 / Oracle（同一套流程）

只改下列几处，其余步骤不变（**没有**像 SQL Server 那样整份可粘贴的完整 `rewrite()` / DDL）：

1. **`ExtJdbcUrlDatabaseIdProvider`**：确保 URL 返回 `dm` / `oracle`  
2. **`VendorSqlRewriteInterceptor.rewrite()`**：  
   - LIMIT → 达梦可保留或按文档；Oracle 常用 `FETCH FIRST` / `OFFSET…FETCH`；SQL Server 须区分有无 `ORDER BY`（`TOP` vs `OFFSET/FETCH`，见步骤 3.3）  
   - 引号、`UUID()`/`SYS_GUID()`、布尔等碎片按厂商改（仍不要在 Interceptor 里用 `#{...}` 整段替换 upsert）  
   - 若目标库开启较高 MySQL 兼容模式，改写面可能较小；**DDL 翻译仍是重头**（见 6.2）  
3. **外部 Mapper**：`databaseId` 与上一步返回值一致；含 upsert / `FROM_UNIXTIME` 等整段方言语句  
4. **profile**：驱动类、Hibernate dialect、PageHelper、Quartz delegate、DDL 翻译规则  
   - **PageHelper**：无现成 `dm` 枚举时，达梦若支持 `LIMIT`，可先试 `helper-dialect: mysql`  
   - **Quartz**：达梦常用默认 `StdJDBCDelegate`；SQL Server 才需要 `MSSQLDelegate`  
   - **Hibernate**：达梦可用 community `DamengDialect` 或在 profile 显式指定  

验收 Checklist 与第 9 节相同。`agent_builder`（Python）仍不在本指南范围（见文首边界说明）。

达梦 DM8 示例见 **附录 A**（兼容模式参数、建库、连接、DDL 转换与验证重点；仍须自备驱动与全量 DDL）。

---

## 12. 交付物清单

做完后你应能交出：

1. `ext/studio-db-ext.jar`（含 class、AutoConfiguration；若有则含 `ext-mapper/*.xml`）  
2. `lib/<jdbc-driver>.jar`（**仅驱动**；不要附带 mybatis/spring 编译副本）  
3. `config/application-<vendor>.yml`（含 `mybatis.mapper-locations`）  
4. `sql/ddl_*.sql`（已在目标库执行成功）  
5. `bin/start-with-ext.sh` + compose/环境变量说明（`loader.path` = ext + lib）  
6. 第 9 节验收截图或请求日志（health / 列表 200 / 导入导出 / 评分 upsert）  

`lib-compile/` 为本地编译便利目录，**不必**随运行包交付到生产。

---

## 附录 A：达梦 DM8 示例（非兼容方言）

以下仅作为“非兼容方言”的落地示例；其他方言可参照同样的方法论，把 DDL、方言 id、驱动和方言组件替换为目标库对应的内容。

### A.1 兼容模式

DM8 的 `COMPATIBLE_MODE` 取值：

| 值 | 含义 |
|---|---|
| 0 | 不兼容（默认） |
| 1 | SQL92 |
| 2 | Oracle |
| 3 | MS SQL Server |
| 4 | MySQL |
| 5 | DM6 |
| 6 | Teradata |
| 7 | PostgreSQL（部分版本） |
| 8 | DB2（部分版本） |

开启 MySQL 兼容使用 **`COMPATIBLE_MODE=4`**。该参数是静态参数，修改 `dm.ini` 或执行 `SP_SET_PARA_VALUE(2, 'COMPATIBLE_MODE', 4)` 后需要重启数据库。建议在建库阶段就确定。

### A.2 建库参数

```text
COMPATIBLE_MODE=4     # MySQL 兼容
LENGTH_IN_CHAR=1      # VARCHAR 按字符计长，避免中文按字节截断
CHARSET=UTF-8         # 具体取值以达梦 dminit 文档为准
```

`LENGTH_IN_CHAR` 影响 `VARCHAR(n)` 的长度语义：MySQL 按字符，达梦默认按字节。manager 的 DDL 里有大量 `varchar(255)` 存中文名称，若按字节计会截断；DM4 的“超长字符串截断而不报错”会静默丢数据。

### A.3 连接与配置

```properties
spring_datasource_url=jdbc:dm://10.0.0.10:5236
spring_datasource_username=AGENT_BUILDER
spring_datasource_password=******
spring_datasource_driver_class_name=dm.jdbc.driver.DmDriver

spring_sql_manager_ddl=file:/opt/studio/sql/ddl_dm.sql
spring_sql_knowledge_ddl=file:/opt/studio/sql/knowledge-base/ddl_dm.sql
spring_sql_init_mode=never

org_quartz_jobStore_driverDelegateClass=org.quartz.impl.jdbcjobstore.StdJDBCDelegate
pagehelper.helper-dialect=mysql
spring.jpa.properties.hibernate.dialect=org.hibernate.dialect.MySQLDialect
```

说明：

- 不激活 `postgres` profile；DM URL 让 `JdbcUrlDatabaseIdProvider` 返回 null，Mapper 走 MySQL 分支。
- `spring_sql_init_mode=never` 时，`dml.sql` 也不会自动执行，需要手工灌一次种子数据。
- 达梦驱动 jar（如 `DmJdbcDriver18.jar`，以厂商交付为准）需挂载并通过 `-cp` 加载。
- Hibernate 6.6.8 没有内置 DM 方言；优先用达梦官方 Hibernate 6.x 方言 jar，否则用 `MySQLDialect` 配合 DM4。
- PageHelper 6.1.0 会把 `jdbc:dm://` 识别为 `dm`（Oracle 方言分页）；使用 MySQL 兼容模式时建议强制 `pagehelper.helper-dialect=mysql`。

### A.4 DDL 转换重点

对 `sql/ddl.sql` 和 `sql/knowledge-base/ddl.sql`：

| MySQL 语法 | 处理方式 |
|---|---|
| `ENGINE=InnoDB` | 删除 |
| `DEFAULT CHARSET` / `COLLATE=utf8mb4_*` | 删除 |
| `ROW_FORMAT=Dynamic` | 删除 |
| `USING BTREE` | 删除，索引改为达梦语法 |
| `AUTO_INCREMENT` | `IDENTITY(1,1)` |
| `TINYINT(1)` | `BIT` / `TINYINT` |
| `DATETIME` | `TIMESTAMP` |
| `MEDIUMTEXT` / `LONGTEXT` / `TEXT` | `CLOB` / `TEXT` |
| `JSON` | `CLOB` / `TEXT`（manager 未使用 JSON 函数） |
| 内联 `COMMENT '...'` | `COMMENT ON COLUMN ...`，或验证 DM4 是否接受内联 |
| `UNSIGNED` | 去掉或放大类型 |
| `ENUM(...)` | `VARCHAR + CHECK` |
| `UNIQUE KEY` / `KEY ... USING BTREE` | `CREATE UNIQUE INDEX` / `CREATE INDEX` |
| `ON UPDATE CURRENT_TIMESTAMP` | DM4 若不支持，去掉并用触发器补 |

粗略规模：manager 约 100 张表 + 知识库 15 张 + QRTZ 11 张。建议脚本完成 80%~90% 的机械替换，再人工复核索引、自增、注释、默认值和字段长度。

### A.5 达梦验证重点

- `LIMIT n`、`LIMIT offset,count`；
- `ON DUPLICATE KEY UPDATE` + `VALUES(col)`；
- 反引号标识符；
- `FROM_UNIXTIME`、`UUID()`、`NOW()`；
- 多参数 `CONCAT`、布尔字面量、`LIKE ... ESCAPE '/'`；
- JPA `t_sessions` 自增 + `getGeneratedKeys`；
- Quartz `SELECT ... FOR UPDATE`；
- CLOB 写入 base64 种子数据；
- `ON UPDATE CURRENT_TIMESTAMP` 是否生效。

上述任一项不通过，按正文步骤 3.3（`rewrite`）/ 3.6（外部 Mapper）与第 6 节 DDL 处理。

---

## 附录 B：开放配置项速查

| 配置项 | 作用 |
|---|---|
| `spring_datasource_url` | JDBC URL（若环境存在 `SPRING_DATASOURCE_URL`，**大小写两套都改**） |
| `spring_datasource_username` / `password` | 账号密码（同上，注意 `SPRING_DATASOURCE_USERNAME` / `PASSWORD`） |
| `spring_datasource_driver_class_name` | 驱动类（同上，注意 `SPRING_DATASOURCE_DRIVER_CLASS_NAME`） |
| `spring_sql_manager_ddl` / `knowledge_ddl` | DDL 文件 |
| `spring_sql_manager_dml` / `knowledge_dml` | DML 文件 |
| `spring_sql_init_mode` | `always` / `never` |
| `org_quartz_jobStore_driverDelegateClass` | Quartz 方言 |
| `pagehelper.helper-dialect` | 分页方言 |
| `spring.jpa.properties.hibernate.dialect` | JPA 方言 |
| `spring.profiles.active` | 如 `manager,sqlserver` 或 `manager,dm` |
| `spring.config.additional-location` | 外部 config 目录 |
| `-Dloader.path` | `ext/`（扩展 jar）+ `lib/`（仅 JDBC 驱动）；勿含 `lib-compile/` |
| `mybatis.mapper-locations` | 含 `classpath:ext-mapper/*.xml`（写在内置 `classpath*:mapper/...` 之前，先注册 `databaseId` 专用语句） |
