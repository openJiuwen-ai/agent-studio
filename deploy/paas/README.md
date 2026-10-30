# deploy/paas —— 文件化部署参数工具包(通用)

给"无法直接注入环境变量、但可以放置/替换文件"的部署环境(典型:PaaS 平台以参数文件方式下发配置)使用的轻量工具。**不修改任何构建/镜像/编排文件**,是纯外挂的三件套:

| 文件 | 作用 |
|---|---|
| `paas-env.properties` | 环境变量样例(按服务分节;值三形态并存——环境相关参数用 `${参数名}` 平台占位符、通用默认用常量、JDBC URL/端点等用常量骨架内嵌占位符) |
| `paas_env.sh` | 加载器:source 后把文件内容导出为环境变量 |
| `README.md` | 本说明 |

## 用法(三步)

```bash
# ① 准备参数文件:复制样例,由平台(或手工)把 ${参数名} 占位符替换为实际取值
#    (常量行无需替换,加载即生效;混合行须其中占位符全部替换后整行才生效)
cp deploy/paas/paas-env.properties /path/to/params.env
vi /path/to/params.env       # 将 ${XXX} 替换为实际值;平台做文件替换则直接落到部署包

# ② 启动服务前 source 加载器(两种定位方式)
. deploy/paas/paas_env.sh                              # 默认读同目录 paas-env.properties
PAAS_ENV_FILE=/path/to/params.env . deploy/paas/paas_env.sh   # 显式指定参数文件

# ③ 在同一 shell 中启动服务,进程自动继承环境变量
java -jar studio-manager.jar --spring.profiles.active=manager ...
# Python 服务(runtime/builder)同理:在同一 shell 启动即可
```

## 加载器行为(四条防护)

1. **文件缺失静默退出**——不影响非文件化部署与本地开发
2. **含未替换占位符的行整行跳过**——值仍含 `${xxx}` 时不注入字面量;混合行(常量骨架内嵌占位符)同样整行跳过,常量骨架不单独生效,避免注入残缺值
3. **非法变量名跳过**——防参数文件被污染后注入任意 shell 代码
4. **幂等**——重复 source 结果一致(文件值始终覆盖)

## 键名形态(重要)

| 服务 | 形态 | 例子 |
|---|---|---|
| studio-manager(Java) | 小写下划线 | `spring_datasource_url`、`redis_host`(与 application-manager.yml 占位符桥同名直通) |
| runtime/builder(Python) | 大写下划线 | `REDIS_HOST`、`DATASOURCE_OBS_SERVER`(Python 侧直接读取) |

同一参数(如 Redis)在两类服务下**各有一份键**,值须保持一致。

**完整权威键表 = `deploy/docker-compose.yml` 各服务的 `environment` 段**——本工具包等价于"手动完成 compose 的 environment 注入",compose 部署本身不需要本工具(`.env` + compose 自动完成同样的事)。

## 边界说明

- 本工具只负责"文件 → 环境变量"这一跳;变量如何被服务消费走各服务**既有**配置链(Java 侧 yml 占位符桥、Python 侧直读),不引入任何新机制
- 参数文件中的值在 `source` 后驻留于 shell 环境,注意 shell 会话的保密性(建议在启动脚本内 source 并随即启动进程)
