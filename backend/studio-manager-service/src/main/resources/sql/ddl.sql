/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

-- common-service tables
CREATE TABLE IF NOT EXISTS `t_common_license_record`  (
    `id` varchar(36)   NOT NULL COMMENT '主键',
    `sku_code` varchar(64)   NOT NULL COMMENT 'sku编码',
    `attr_code` varchar(64)   NOT NULL COMMENT '属性编码',
    `resource_id` varchar(36)   NOT NULL COMMENT '资源ID',
    `oper_type` varchar(8)   NOT NULL COMMENT '操作动作：add、delete',
    `quantity` varchar(64)   NOT NULL COMMENT '数量',
    `created_by_user_id` varchar(32)   NULL DEFAULT NULL COMMENT '创建操作员ID',
    `created_date` timestamp NOT NULL COMMENT '创建时间',
    `last_updated_by_user_id` varchar(32)   NULL DEFAULT NULL COMMENT '最后修改操作员ID',
    `last_updated_date` timestamp NOT NULL COMMENT '最后修改时间',
    `domain_id` varchar(64)   NULL DEFAULT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    UNIQUE INDEX `t_common_license_record_id_uindex`(`id` ASC) USING BTREE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci  COMMENT = 'license用量记录表' ROW_FORMAT = Dynamic;

CREATE TABLE IF NOT EXISTS `t_common_license`  (
    `id` varchar(36)   NOT NULL COMMENT '主键',
    `resource_id` varchar(36)   NULL DEFAULT NULL COMMENT '关联资源ID',
    `sku_code` varchar(64)   NULL DEFAULT NULL COMMENT 'skuCode',
    `attr_code` varchar(64)   NULL DEFAULT NULL COMMENT '属性Code',
    `status` varchar(32)   NULL DEFAULT NULL COMMENT '状态：active|inactive|deleted|cleaned',
    `current_value` varchar(256)   NOT NULL COMMENT '当前值',
    `max_value` varchar(32)   NULL DEFAULT '-1' COMMENT '最大值',
    `type` varchar(8)   NULL DEFAULT '2' COMMENT '值类型：1（布尔型）2（计数型）',
    `created_by_user_id` varchar(32)   NULL DEFAULT NULL COMMENT '创建操作员ID',
    `created_date` timestamp NULL DEFAULT NULL COMMENT '创建时间',
    `last_updated_by_user_id` varchar(32)   NULL DEFAULT NULL COMMENT '最后修改操作员ID',
    `last_updated_date` timestamp NULL DEFAULT NULL COMMENT '最后修改时间',
    `domain_id` varchar(64)   NULL DEFAULT NULL COMMENT '租户ID',
    `main_key_id` varchar(255) NULL COMMENT '主秘钥.(AgentBuilder主密钥就是SCC的密钥，ID就是"scc-{scc_domain_id}"（SCC DomainID见scc.conf）。KMS主密钥的ID为"kms-{KMS ID})',
    `main_key_alias` varchar(255) NULL COMMENT '主秘钥别名',
    `version` int NULL COMMENT '从1开始，最新版本的latest应该为Y，其他版本的latest应该为N。',
    `active` tinyint(1) NULL COMMENT '是否有效，仅有有效状态的才能加解密，以支持回收旧密钥，已回收的标识为N。一般情况下通过紧急情况下进行变更修改。',
    `latest` tinyint(1) NULL COMMENT '标识<domain_id, main_key_id>下的最新版本，使用最新版本加密数据。<domain_id, main_key_id>应该只有1个记录为latest.',
    PRIMARY KEY (`id`) USING BTREE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci  COMMENT = 'license控制表' ROW_FORMAT = Dynamic;

CREATE TABLE IF NOT EXISTS `t_common_reource_inst`  (
    `resource_id` varchar(36)   NOT NULL COMMENT '资源唯一标识，36位字符串（uuid），必填',
    `parent_id` varchar(36)   NULL DEFAULT NULL COMMENT '关联的主资源标识，可选，为空当前为主资源，不为空当前为子资源',
    `sku_code` varchar(64)   NULL DEFAULT NULL COMMENT '资源关联的SKU编码',
    `domain_id` varchar(32)   NULL DEFAULT NULL COMMENT '资源关联的IAM主账号domain_id',
    `instance_id` varchar(32)   NULL DEFAULT NULL COMMENT '资源关联的实例标识',
    `subproduct_code` varchar(64)   NULL DEFAULT NULL COMMENT '资源关联的子产品编码',
    `status` varchar(32)   NULL DEFAULT NULL COMMENT '资源状态',
    `cbc_order_id` varchar(64)   NOT NULL COMMENT '订购资源归属的子产品标识',
    `subproduct_id` varchar(64)   NULL DEFAULT NULL COMMENT '云服务类型，CBC中配置的值，公有云值为：hws.service.type.appstage',
    `cloud_service_type` varchar(64)   NULL DEFAULT NULL COMMENT '区域标识，应用平台为全局服务，值为：global-cbc-1',
    `region_id` varchar(32)   NOT NULL COMMENT '下单时所在的region_id',
    `project_id` varchar(64)   NOT NULL COMMENT '下单时所在的project_id',
    `created_date` timestamp NULL DEFAULT NULL,
    `created_by_user_id` varchar(32)   NULL DEFAULT NULL,
    `last_updated_date` timestamp NULL DEFAULT NULL,
    `last_updated_by_user_id` varchar(32)   NULL DEFAULT NULL,
    PRIMARY KEY (`resource_id`) USING BTREE,
    UNIQUE INDEX `t_common_reource_inst_id_uindex`(`resource_id` ASC) USING BTREE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci  COMMENT = '订购实例表' ROW_FORMAT = Dynamic;

CREATE TABLE IF NOT EXISTS `t_common_tenant`  (
    `domain_id` varchar(64)   NOT NULL COMMENT 'IAM账号ID，租户ID',
    `domain_name` varchar(256)   NOT NULL COMMENT '账号名称',
    `description` varchar(256)   NULL DEFAULT NULL COMMENT '备注，描述信息',
    `created_date` datetime NOT NULL COMMENT '创建时间',
    `last_updated_date` datetime NOT NULL COMMENT '最后修改时间',
    `status` varchar(16)   NOT NULL COMMENT '租户状态，枚举值：激活（active）、未激活（inactive）',
    `tenant_type` varchar(2)   NULL DEFAULT NULL COMMENT '租户类型',
    `ext_info` varchar(256)   NULL DEFAULT NULL COMMENT '租户扩展信息',
    PRIMARY KEY (`domain_id`) USING BTREE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci  COMMENT = '租户管理表' ROW_FORMAT = Dynamic;

CREATE TABLE IF NOT EXISTS `t_common_kms_info`  (
    `id` varchar(255)  NOT NULL COMMENT 'id',
    `domain_id` varchar(64)  NOT NULL COMMENT 'IAM账号ID，租户ID',
    `cipher_text` varchar(1024)  NULL DEFAULT NULL,
    `status` varchar(10)  NULL DEFAULT NULL COMMENT '是否生效',
    `created_date` timestamp NULL DEFAULT NULL,
    `created_by_user_id` varchar(32)  NULL DEFAULT NULL,
    `last_updated_date` timestamp NULL DEFAULT NULL,
    `last_updated_by_user_id` varchar(32)  NULL DEFAULT NULL,
    `main_key_id` varchar(255) NULL COMMENT '主秘钥.(AgentBuilder主密钥就是SCC的密钥，ID就是"scc-{scc_domain_id}"（SCC DomainID见scc.conf）。KMS主密钥的ID为"kms-{KMS ID})',
    `main_key_alias` varchar(255) NULL COMMENT '主秘钥别名',
    `version` int NULL COMMENT '从1开始，最新版本的latest应该为Y，其他版本的latest应该为N。',
    `active` tinyint(1) NULL COMMENT '是否有效，仅有有效状态的才能加解密，以支持回收旧密钥，已回收的标识为N。一般情况下通过紧急情况下进行变更修改。',
    `latest` tinyint(1) NULL COMMENT '标识<domain_id, main_key_id>下的最新版本，使用最新版本加密数据。<domain_id, main_key_id>应该只有1个记录为latest.',
    PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT = 'KMS管理表' ROW_FORMAT=DYNAMIC ;

CREATE TABLE IF NOT EXISTS `t_common_kms_relation`  (
  `domain_id` varchar(64) NOT NULL COMMENT 'IAM账号ID，租户ID',
  `main_key_id` varchar(255) NULL DEFAULT NULL COMMENT '主秘钥.(AgentBuilder主密钥就是SCC的密钥，ID就是"scc-{scc_domain_id}"（SCC DomainID见scc.conf）。KMS主密钥的ID为"kms-{KMS ID})',
  `related_primary_key` varchar(255) NULL DEFAULT NULL COMMENT '工作空间主键ID、租户主键ID',
  `type` varchar(255) NULL DEFAULT NULL COMMENT 'workspace/tenant(可扩展枚举值)',
  `created_date` timestamp NULL DEFAULT NULL,
  `created_by_user_id` varchar(32) NULL DEFAULT NULL,
  `last_updated_date` timestamp NULL DEFAULT NULL,
  `last_updated_by_user_id` varchar(32) NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT = 'KMS关系表' ROW_FORMAT=DYNAMIC ;

CREATE TABLE IF NOT EXISTS `t_common_agreement`  (
    `id` varchar(255)  NOT NULL COMMENT '主键',
    `domain_id` varchar(255)  NOT NULL COMMENT 'IAM主账号DomainID',
    `version` varchar(32)  NOT NULL COMMENT '版本',
    `privacy_statement` varchar(255)  NOT NULL COMMENT '本次订购签订的服务声明版本号',
    `agree_flag` varchar(255) NULL DEFAULT NULL COMMENT '隐私是否同意授权。（1表示同意，0表示否）',
    `created_date` datetime NULL DEFAULT NULL,
    `created_by_user_id` varchar(255)  NULL DEFAULT NULL,
    `last_updated_date` datetime NULL DEFAULT NULL,
    `last_updated_by_user_id` varchar(255)  NULL DEFAULT NULL,
    PRIMARY KEY (`id`) USING BTREE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT = 'agreement管理表' ROW_FORMAT=DYNAMIC ;

-- manager tables
CREATE TABLE IF NOT EXISTS `t_agent` (
    `agent_id`                    VARCHAR(64)   NOT NULL COMMENT 'agent唯一标识',
    `project_id`                  VARCHAR(64)   CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '项目唯一标识',
    `name`                        VARCHAR(64)   NULL     COMMENT 'agent名称',
    `description`                 VARCHAR(1024) NULL     COMMENT '应用描述',
    `icon`                        MEDIUMTEXT    NULL     COMMENT 'agent图标',
    `icon_name`                   VARCHAR(64)   NULL     COMMENT 'icon图标名称',
    `model_deployment_id`         VARCHAR(128)  NULL     COMMENT '大模型的deployment_id，需要使用具备Agent能力的模型',
    `model_name`                  VARCHAR(128)  NULL     COMMENT '大模型名称',
    `model_config`                VARCHAR(256)  NULL     COMMENT '大模型参数配置',
    `instructions`                TEXT          NULL     COMMENT 'agent使用的系统指令',
    `trigger_list`                TEXT          NULL     COMMENT '触发器',
    `memory_variables`            TEXT          NULL     COMMENT 'agent的记忆变量',
    `prologue`                    VARCHAR(512)  NULL     COMMENT 'agent开场白',
    `suggest_queries`             VARCHAR(4096) NULL     COMMENT 'agent推荐问',
    `additional_questions_config` TEXT          NULL     COMMENT '追问配置',
    `voice_interaction`           TEXT          NULL     COMMENT '语音配置',
    `dsl_path`                    VARCHAR(256)  NULL     COMMENT 'dsl文件存放路径',
    `ir_path`                     VARCHAR(256)  NULL     COMMENT 'IR文件相对路径',
    `type`                        VARCHAR(32)   NULL     COMMENT 'agent类型',
    `sub_type`                    VARCHAR(50)   NULL     COMMENT 'agent 子类型',
    `status`                      VARCHAR(32)   NULL     COMMENT 'agent状态',
    `creator`                     VARCHAR(64)   NULL     COMMENT 'agent创建者',
    `creator_id`                  VARCHAR(64)   CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL COMMENT 'agent创建者id',
    `created_on`                  TIMESTAMP     NULL     DEFAULT CURRENT_TIMESTAMP                             COMMENT 'agent创建时间',
    `updated_on`                  TIMESTAMP     NULL     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'agent更新时间',
    `published_on`                TIMESTAMP     NULL     COMMENT 'agent发布时间',
    `model_type`                  VARCHAR(64)   NULL     COMMENT '模型类型',
    `knowledge_retrieve_policy`   MEDIUMTEXT    NULL     COMMENT '知识检索策略（json）',
    `workflow_switch_enabled`     TINYINT(1)    NOT NULL DEFAULT '0' COMMENT '工作流跳转',
    `scheduling_mode`             VARCHAR(32)   NOT NULL DEFAULT 'ReAct' COMMENT 'agent调度模式，ReAct、RAG',
    `model`                       VARCHAR(64)   NULL     COMMENT '模型资产名称',
    `content_review`              MEDIUMTEXT    NULL     COMMENT 'Agent 内容审核',
    `safety_barrier`              TINYINT(1)    NULL     COMMENT 'Agent 安全护栏',
    `workspace_id`                VARCHAR(64)   NULL     COMMENT '工作空间ID',
    `trace_id`                    VARCHAR(64)   NULL     COMMENT '溯源ID',
    `domain_id`                   VARCHAR(64)   NULL     COMMENT '租户ID',
    `agent_variables`             MEDIUMTEXT    NULL     COMMENT 'Agent自定义变量列表',
    `memory_config`               MEDIUMTEXT    NULL     COMMENT 'Agent记忆配置',
    `plan_qa_independent`         TINYINT(1)    NULL     COMMENT '规划与问答模型是否独立配置',
    `plan_model`                  VARCHAR(64)   NULL     COMMENT '规划模型资产名称',
    `plan_model_deployment_id`    VARCHAR(128)  NULL     COMMENT '规划模型的deployment_id',
    `plan_model_name`             VARCHAR(128)  NULL     COMMENT '规划模型名称',
    `plan_model_config`           VARCHAR(128)  NULL     COMMENT '规划模型参数配置',
    `plan_model_type`             VARCHAR(64)   NULL     COMMENT '规划模型类型',
    `deleted`                     TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '逻辑删除标记：0-未删除，1-已删除',
    `is_share`                    TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '是否已共享（0=否，1=是)',
    `reference`                   VARCHAR(64)   NULL     COMMENT '是否开启引用和归属',
    `input_variables`             MEDIUMTEXT    NULL     COMMENT '用户输入变量参数',
    PRIMARY KEY (`agent_id`),
    KEY `index_t_agent_agent_id` (`agent_id`),
    KEY `IDX_T_AGENT_PROJECT_AGENT` (`project_id`,`agent_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC  COMMENT='Agent表';

CREATE TABLE IF NOT EXISTS `t_agent_version` (
    `version_id`                  VARCHAR(64)   NOT NULL COMMENT 'agent版本唯一标识',
    `agent_id`                    VARCHAR(64)   NOT NULL COMMENT 'agent唯一标识',
    `project_id`                  VARCHAR(64)   CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '项目唯一标识',
    `name`                        VARCHAR(64)   NULL     COMMENT 'agent名称',
    `description`                 VARCHAR(1024) NULL     COMMENT '应用描述',
    `icon`                        MEDIUMTEXT    NULL     COMMENT 'agent图标',
    `icon_name`                   VARCHAR(64)   NULL     COMMENT 'icon图标名称',
    `tags`                        VARCHAR(512)  NULL     COMMENT '应用绑定标签列表',
    `instructions`                TEXT          NULL     COMMENT 'agent使用的系统指令',
    `trigger_list`                TEXT          NULL     COMMENT '触发器',
    `prologue`                    VARCHAR(512)  NULL     COMMENT 'agent开场白',
    `suggest_queries`             VARCHAR(4096) NULL     COMMENT 'agent推荐问',
    `additional_questions_config` TEXT          NULL     COMMENT '追问配置',
    `ir_path`                     VARCHAR(256)  NULL     COMMENT 'IR文件相对路径',
    `dsl_path`                    VARCHAR(256)  NULL     COMMENT 'DSL文件相对路径',
    `is_online`                   TINYINT(1)    NOT NULL DEFAULT '1' COMMENT '是否为上线状态',
    `creator`                     VARCHAR(64)   NULL     COMMENT 'agent创建者',
    `created_on`                  TIMESTAMP     NULL     COMMENT 'agent创建时间',
    `updated_on`                  TIMESTAMP     NULL     COMMENT 'agent更新时间',
    `published_on`                TIMESTAMP     NULL     COMMENT 'agent发布时间',
    `workspace_id`                VARCHAR(64)   NULL     COMMENT '工作空间ID',
    PRIMARY KEY (`version_id`),
    KEY `index_t_agent_version_version_id` (`version_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC  COMMENT='Agent版本表';

CREATE TABLE IF NOT EXISTS `t_agent_workflow` (
    `id`                  VARCHAR(64)   NOT NULL COMMENT 'workflow id',
    `name`                VARCHAR(64)   NOT NULL COMMENT '工作流名称',
    `code`                VARCHAR(64)   NULL COMMENT '英文名',
    `description`         VARCHAR(1024) NULL COMMENT '工作流描述信息',
    `avatar`              MEDIUMTEXT    NULL COMMENT '工作流图标',
    `icon_name`           VARCHAR(64)   NULL     COMMENT 'icon图标名称',
    `customize_node`      TINYINT(1)    NULL COMMENT '是否是自定义节点，1表示是自定义节点,0或空表示不是',
    `dsl_path`            VARCHAR(256)  NULL COMMENT 'Flow dsl相对路径',
    `ir_path`             VARCHAR(256)  NULL COMMENT 'IR相对路径',
    `status`              VARCHAR(32)   NULL COMMENT '工作流状态:(published, draft)',
    `trigger_list`        TEXT          NULL     COMMENT '触发器',
    `visibility`          VARCHAR(32)   NULL COMMENT '可见范围：user,project(默认),workspace,domain,global',
    `created_at`          BIGINT(13)    NULL COMMENT '工作流创建时间',
    `updated_at`          BIGINT(13)    NULL COMMENT '工作流更新时间',
    `published_at`        BIGINT(13)    NULL COMMENT '工作流发布时间',
    `created_by`          VARCHAR(64)   NULL COMMENT '工作流创建人',
    `creator_id`          VARCHAR(64)   CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL COMMENT '工作流创建人user id',
    `updated_by`          VARCHAR(64)   NULL COMMENT '工作流更新人',
    `updater_id`          VARCHAR(64)   NULL COMMENT '工作流更新人user id',
    `project_id`          VARCHAR(64)   CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '租户的project id',
    `workspace_id`        VARCHAR(64)   NULL COMMENT '工作空间ID',
    `domain_id`           VARCHAR(64)   NOT NULL COMMENT '租户的domain id',
    `deploy_wf_version`   BIGINT(13)    NULL COMMENT '部署的工作流版本',
    `ref_workflows`       TEXT          NULL COMMENT '引用的工作流列表',
    `last_version_id`     VARCHAR(64)   NULL COMMENT '最新版本id',
    `deleted`             TINYINT(1)    NULL COMMENT '工作流是否软删除',
    `test_status`         TINYINT(1)    NULL COMMENT '工作流是否试运行成功，0：失败；1：成功',
    `workflow_type`       VARCHAR(32)   NULL COMMENT '工作流类型(chat, task)',
    `trace_id`            VARCHAR(64)   NULL COMMENT '溯源ID',
    `is_share`            TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '是否已共享（0=否，1=是）',
    PRIMARY KEY (`id`),
    KEY `idx_t_agent_workflow_created_at` (`created_at`),
    KEY `idx_t_agent_workflow_updated_at` (`updated_at`),
    KEY `idx_t_agent_workflow_published_at` (`published_at`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC ;

CREATE TABLE IF NOT EXISTS `t_history_agent_workflow` (
    `history_id`          VARCHAR(64)   NOT NULL COMMENT '历史表主键 id',
    `id`                  VARCHAR(64)   NOT NULL COMMENT 'workflow id',
    `name`                VARCHAR(64)   NOT NULL COMMENT '工作流名称',
    `code`                VARCHAR(64)   NULL COMMENT '英文名',
    `description`         VARCHAR(1024) NULL COMMENT '工作流描述信息',
    `avatar`              MEDIUMTEXT    NULL COMMENT '工作流图标',
    `icon_name`           VARCHAR(64)   NULL COMMENT 'icon图标名称',
    `dsl_path`            VARCHAR(256)  NULL COMMENT 'Flow dsl相对路径',
    `ir_path`             VARCHAR(256)  NULL COMMENT 'IR相对路径',
    `status`              VARCHAR(32)   NULL COMMENT '工作流状态:(published, draft)',
    `trigger_list`        TEXT          NULL     COMMENT '触发器',
    `visibility`          VARCHAR(32)   NULL COMMENT '可见范围：user,project(默认),workspace,domain,global',
    `created_at`          BIGINT(13)    NULL COMMENT '工作流创建时间',
    `updated_at`          BIGINT(13)    NULL COMMENT '工作流更新时间',
    `published_at`        BIGINT(13)    NULL COMMENT '工作流发布时间',
    `created_by`          VARCHAR(64)   NULL COMMENT '工作流创建人',
    `creator_id`          VARCHAR(64)   NULL COMMENT '工作流创建人user id',
    `updated_by`          VARCHAR(64)   NULL COMMENT '工作流更新人',
    `updater_id`          VARCHAR(64)   NULL COMMENT '工作流更新人user id',
    `project_id`          VARCHAR(64)   NOT NULL COMMENT '租户的project id',
    `workspace_id`        VARCHAR(64)   NULL COMMENT '工作空间ID',
    `domain_id`           VARCHAR(64)   NOT NULL COMMENT '租户的domain id',
    `deploy_wf_version`   BIGINT(13)    NULL COMMENT '部署的工作流版本',
    `ref_workflows`       TEXT          NULL COMMENT '引用的工作流列表',
    `last_version_id`     VARCHAR(64)   NULL COMMENT '最新版本id',
    `deleted`             TINYINT(1)    NULL COMMENT '工作流是否软删除',
    `test_status`         TINYINT(1)    NULL COMMENT '工作流是否试运行成功，0：失败；1：成功',
    `customize_node`      TINYINT(1)    NULL COMMENT '是否是自定义节点，1表示是自定义节点,0或空表示不是',
    `workflow_type`       VARCHAR(32)   NULL COMMENT '工作流类型(chat, task)',
    `trace_id`            VARCHAR(64)   NULL COMMENT '溯源ID',
    `is_share`            TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '是否已共享（0=否，1=是）',
    PRIMARY KEY (`history_id`),
    KEY `idx_t_history_agent_workflow_updated_at` (`updated_at`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC ;

CREATE TABLE IF NOT EXISTS `t_app` (
    `app_id`          VARCHAR(64)  NOT NULL COMMENT '应用唯一标识',
    `project_id`      VARCHAR(64)  CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '租户唯一标识',
    `name`            VARCHAR(64)  NOT NULL COMMENT '应用名称',
    `description`     VARCHAR(1024) NULL     COMMENT '应用描述',
    `icon`            MEDIUMTEXT   NOT NULL COMMENT '应用图标',
    `icon_name`       VARCHAR(64)  NULL     COMMENT 'icon图标名称',
    `tags`            VARCHAR(512) NULL     COMMENT '应用绑定标签列表',
    `app_type`        VARCHAR(32)  NOT NULL COMMENT '应用类型',
    `resource_id`     VARCHAR(64)  NOT NULL COMMENT '应用来源标识',
    `resource_type`   VARCHAR(32)  NOT NULL COMMENT '应用来源类型',
    `creator`         VARCHAR(64)  NOT NULL COMMENT '应用创建者',
    `published_on`    TIMESTAMP    NOT NULL COMMENT '应用发布时间',
    `prologue`        TEXT         NULL COMMENT '工作流开场白',
    `suggest_queries` TEXT         NULL COMMENT '工作流推荐问',
    `workflow_type`   VARCHAR(16)  NULL COMMENT '工作流类型',
    `input_params`    MEDIUMTEXT   NULL COMMENT '工作流输入参数',
    `output_params`   MEDIUMTEXT   NULL COMMENT '工作流输出参数',
    `workspace_id`    VARCHAR(64)  NULL COMMENT '工作空间ID',
    `trace_id`        VARCHAR(64)  NULL COMMENT '溯源ID',
    `deleted`         TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除标记：0-未删除，1-已删除',
    `updated_on`      TIMESTAMP    NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`app_id`,`project_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC  COMMENT='应用表';

CREATE TABLE IF NOT EXISTS `t_tag` (
    `tag_id`     VARCHAR(64)  NOT NULL COMMENT '标签唯一标识',
    `name`       VARCHAR(128) NOT NULL COMMENT '标签名称',
    `name_en`    VARCHAR(128) NOT NULL COMMENT '标签英文名称',
    `created_on` DATETIME     NULL     DEFAULT CURRENT_TIMESTAMP                             COMMENT '标签创建时间',
    `updated_on` DATETIME     NULL     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '标签更新时间',
    PRIMARY KEY (`tag_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC  COMMENT='标签表';

CREATE TABLE IF NOT EXISTS `QRTZ_JOB_DETAILS`
(
    SCHED_NAME        VARCHAR(120) NOT NULL COMMENT '调度器名称',
    JOB_NAME          VARCHAR(200) NOT NULL COMMENT 'Job名称',
    JOB_GROUP         VARCHAR(200) NOT NULL COMMENT 'Job所属组',
    DESCRIPTION       VARCHAR(250) NULL COMMENT '详细描述信息',
    JOB_CLASS_NAME    VARCHAR(250) NOT NULL COMMENT 'Job对应的Java类名',
    IS_DURABLE        VARCHAR(1)   NOT NULL COMMENT 'Job是否持久化',
    IS_NONCONCURRENT  VARCHAR(1)   NOT NULL COMMENT 'Job是否并发',
    IS_UPDATE_DATA    VARCHAR(1)   NOT NULL COMMENT 'Job数据是否更新',
    REQUESTS_RECOVERY VARCHAR(1)   NOT NULL COMMENT 'Job是否需要恢复',
    JOB_DATA          BLOB         NULL COMMENT '存放持久化Job对象',
    PRIMARY KEY (SCHED_NAME, JOB_NAME, JOB_GROUP)
    ) ENGINE=InnoDB
    DEFAULT CHARSET = utf8mb4
    COLLATE = utf8mb4_general_ci
    ROW_FORMAT = DYNAMIC COMMENT ='存储每一个已配置的Job的详细信息';

CREATE TABLE IF NOT EXISTS `QRTZ_TRIGGERS`
(
    SCHED_NAME      VARCHAR(120) NOT NULL COMMENT '调度器名称',
    TRIGGER_NAME    VARCHAR(200) NOT NULL COMMENT '触发器名称',
    TRIGGER_GROUP   VARCHAR(200) NOT NULL COMMENT '触发器所属组',
    JOB_NAME        VARCHAR(200) NOT NULL COMMENT 'Job名称',
    JOB_GROUP       VARCHAR(200) NOT NULL COMMENT 'Job所属组',
    DESCRIPTION     VARCHAR(250) NULL COMMENT '详细描述信息',
    NEXT_FIRE_TIME  BIGINT(13)   NULL COMMENT '下一次触发时间，默认为-1，意味着不会自动触发',
    PREV_FIRE_TIME  BIGINT(13)   NULL COMMENT '上一次触发时间（毫秒）',
    PRIORITY        INTEGER      NULL COMMENT '优先级',
    TRIGGER_STATE   VARCHAR(16)  NOT NULL COMMENT '当前触发器状态',
    TRIGGER_TYPE    VARCHAR(8)   NOT NULL COMMENT '触发器类型，使用cron表达式',
    START_TIME      BIGINT(13)   NOT NULL COMMENT '开始时间',
    END_TIME        BIGINT(13)   NULL COMMENT '结束时间',
    CALENDAR_NAME   VARCHAR(200) NULL COMMENT '日程表名称',
    MISFIRE_INSTR   SMALLINT(2)  NULL COMMENT '补偿措施执行策略',
    JOB_DATA        BLOB         NULL COMMENT '存放持久化Job对象',
    PRIMARY KEY (SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP),
    FOREIGN KEY (SCHED_NAME, JOB_NAME, JOB_GROUP)
    REFERENCES QRTZ_JOB_DETAILS(SCHED_NAME, JOB_NAME, JOB_GROUP)
    ) ENGINE=InnoDB
    DEFAULT CHARSET = utf8mb4
    COLLATE = utf8mb4_general_ci
    ROW_FORMAT = DYNAMIC COMMENT ='存储已配置的触发器的信息';

CREATE TABLE IF NOT EXISTS `QRTZ_SIMPLE_TRIGGERS`
(
    SCHED_NAME      VARCHAR(120)    NOT NULL COMMENT '调度器名称',
    TRIGGER_NAME    VARCHAR(200)    NOT NULL COMMENT '触发器名称',
    TRIGGER_GROUP   VARCHAR(200)    NOT NULL COMMENT '触发器所属组',
    REPEAT_COUNT    BIGINT(7)       NOT NULL COMMENT '重复的次数统计',
    REPEAT_INTERVAL BIGINT(12)      NOT NULL COMMENT '重复的间隔时间',
    TIMES_TRIGGERED BIGINT(10)      NOT NULL COMMENT '已经触发的次数',
    PRIMARY KEY (SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP),
    FOREIGN KEY (SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP)
    REFERENCES QRTZ_TRIGGERS(SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP)
    ) ENGINE=InnoDB
    DEFAULT CHARSET = utf8mb4
    COLLATE = utf8mb4_general_ci
    ROW_FORMAT = DYNAMIC COMMENT ='存储简单的触发器，包括重复次数、间隔、以及已触的次数';

CREATE TABLE IF NOT EXISTS `QRTZ_CRON_TRIGGERS`
(
    SCHED_NAME      VARCHAR(120) NOT NULL COMMENT '调度器名称',
    TRIGGER_NAME    VARCHAR(200) NOT NULL COMMENT '触发器名称',
    TRIGGER_GROUP   VARCHAR(200) NOT NULL COMMENT '触发器所属组',
    CRON_EXPRESSION VARCHAR(120) NOT NULL COMMENT 'cron表达式',
    TIME_ZONE_ID    VARCHAR(80) COMMENT '时区',
    PRIMARY KEY (SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP),
    FOREIGN KEY (SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP)
    REFERENCES QRTZ_TRIGGERS(SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP)
    ) ENGINE=InnoDB
    DEFAULT CHARSET = utf8mb4
    COLLATE = utf8mb4_general_ci
    ROW_FORMAT = DYNAMIC COMMENT ='存储Cron触发器，包括Cron表达式和时区信息';

CREATE TABLE IF NOT EXISTS `QRTZ_SIMPROP_TRIGGERS`
(
    SCHED_NAME      VARCHAR(120)    NOT NULL COMMENT '调度器名称',
    TRIGGER_NAME    VARCHAR(200)    NOT NULL COMMENT '触发器名称',
    TRIGGER_GROUP   VARCHAR(200)    NOT NULL COMMENT '触发器所属',
    STR_PROP_1      VARCHAR(512)    NULL COMMENT 'String类型的trigger的第一个参数',
    STR_PROP_2      VARCHAR(512)    NULL COMMENT 'String类型的trigger的第二个参数',
    STR_PROP_3      VARCHAR(512)    NULL COMMENT 'String类型的trigger的第三个参数',
    INT_PROP_1      INT             NULL COMMENT 'int类型的trigger的第一个参数',
    INT_PROP_2      INT             NULL COMMENT 'int类型的trigger的第二个参数',
    LONG_PROP_1     BIGINT          NULL COMMENT 'long类型的trigger的第一个参数',
    LONG_PROP_2     BIGINT          NULL COMMENT 'long类型的trigger的第二个参数',
    DEC_PROP_1      NUMERIC(13,4)   NULL COMMENT 'decimal类型的trigger的第一个参数',
    DEC_PROP_2      NUMERIC(13,4)   NULL COMMENT 'decimal类型的trigger的第二个参数',
    BOOL_PROP_1     VARCHAR(1)      NULL COMMENT 'Boolean类型的trigger的第一个参数',
    BOOL_PROP_2     VARCHAR(1)      NULL COMMENT 'Boolean类型的trigger的第二个参数',
    PRIMARY KEY (SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP),
    FOREIGN KEY (SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP)
    REFERENCES QRTZ_TRIGGERS(SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP)
    ) ENGINE=InnoDB
    DEFAULT CHARSET = utf8mb4
    COLLATE = utf8mb4_general_ci
    ROW_FORMAT = DYNAMIC COMMENT ='触发器相关的表';

CREATE TABLE IF NOT EXISTS `QRTZ_BLOB_TRIGGERS`
(
    SCHED_NAME      VARCHAR(120)    NOT NULL COMMENT '调度器名称',
    TRIGGER_NAME    VARCHAR(200)    NOT NULL COMMENT '触发器名称',
    TRIGGER_GROUP   VARCHAR(200)    NOT NULL COMMENT '触发器所属组',
    BLOB_DATA       BLOB            NULL COMMENT '存放持久化Trigger对象',
    PRIMARY KEY (SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP),
    INDEX (SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP),
    FOREIGN KEY (SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP)
    REFERENCES QRTZ_TRIGGERS(SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP)
    ) ENGINE=InnoDB
    DEFAULT CHARSET = utf8mb4
    COLLATE = utf8mb4_general_ci
    ROW_FORMAT = DYNAMIC COMMENT ='触发器作为BLOB类型存储';

CREATE TABLE IF NOT EXISTS `QRTZ_CALENDARS`
(
    SCHED_NAME      VARCHAR(120)    NOT NULL COMMENT '调度器名称',
    CALENDAR_NAME   VARCHAR(200)    NOT NULL COMMENT '日历名称',
    CALENDAR        BLOB            NOT NULL COMMENT '存放持久化calendar对象',
    PRIMARY KEY (SCHED_NAME, CALENDAR_NAME)
    ) ENGINE=InnoDB
    DEFAULT CHARSET = utf8mb4
    COLLATE = utf8mb4_general_ci
    ROW_FORMAT = DYNAMIC COMMENT ='以BLOB类型存储Quartz的Calendar信息';

CREATE TABLE IF NOT EXISTS `QRTZ_PAUSED_TRIGGER_GRPS`
(
    SCHED_NAME      VARCHAR(120) NOT NULL COMMENT '调度器名称',
    TRIGGER_GROUP   VARCHAR(200) NOT NULL COMMENT '触发器所属组',
    PRIMARY KEY (SCHED_NAME, TRIGGER_GROUP)
    ) ENGINE=InnoDB
    DEFAULT CHARSET = utf8mb4
    COLLATE = utf8mb4_general_ci
    ROW_FORMAT = DYNAMIC COMMENT ='存储已暂停的Trigger组的信息';

CREATE TABLE IF NOT EXISTS `QRTZ_FIRED_TRIGGERS`
(
    SCHED_NAME          VARCHAR(120)    NOT NULL COMMENT '调度器名称',
    ENTRY_ID            VARCHAR(95)     NOT NULL COMMENT '调度器实例id',
    TRIGGER_NAME        VARCHAR(200)    NOT NULL COMMENT '触发器名称',
    TRIGGER_GROUP       VARCHAR(200)    NOT NULL COMMENT '触发器所属组',
    INSTANCE_NAME       VARCHAR(200)    NOT NULL COMMENT '调度器实例名',
    FIRED_TIME          BIGINT(13)      NOT NULL COMMENT '触发时间',
    SCHED_TIME          BIGINT(13)      NOT NULL COMMENT '定时器制定的时间',
    PRIORITY            INTEGER         NOT NULL COMMENT '优先级',
    STATE               VARCHAR(16)     NOT NULL COMMENT '状态',
    JOB_NAME            VARCHAR(200)    NULL COMMENT 'Job名称',
    JOB_GROUP           VARCHAR(200)    NULL COMMENT 'Job所属组',
    IS_NONCONCURRENT    VARCHAR(1)      NULL COMMENT '是否并发',
    REQUESTS_RECOVERY   VARCHAR(1)      NULL COMMENT '是否接受恢复执行',
    PRIMARY KEY (SCHED_NAME, ENTRY_ID)
    ) ENGINE=InnoDB
    DEFAULT CHARSET = utf8mb4
    COLLATE = utf8mb4_general_ci
    ROW_FORMAT = DYNAMIC COMMENT ='存储与已触发的Trigger相关的状态信息，以及相联Job的执行信息';

CREATE TABLE IF NOT EXISTS `QRTZ_SCHEDULER_STATE`
(
    SCHED_NAME          VARCHAR(120)    NOT NULL COMMENT '调度器名称',
    INSTANCE_NAME       VARCHAR(200)    NOT NULL COMMENT '调度器实例名',
    LAST_CHECKIN_TIME   BIGINT(13)      NOT NULL COMMENT '上次检查时间',
    CHECKIN_INTERVAL    BIGINT(13)      NOT NULL COMMENT '检查间隔时间',
    PRIMARY KEY (SCHED_NAME, INSTANCE_NAME)
    ) ENGINE=InnoDB
    DEFAULT CHARSET = utf8mb4
    COLLATE = utf8mb4_general_ci
    ROW_FORMAT = DYNAMIC COMMENT ='存储调度器状态，以及上次检查时间与检测状态';

CREATE TABLE IF NOT EXISTS `QRTZ_LOCKS`
(
    SCHED_NAME  VARCHAR(120)    NOT NULL COMMENT '调度器名称',
    LOCK_NAME   VARCHAR(40)     NOT NULL COMMENT '悲观锁名称',
    PRIMARY KEY (SCHED_NAME, LOCK_NAME)
    ) ENGINE=InnoDB
    DEFAULT CHARSET = utf8mb4
    COLLATE = utf8mb4_general_ci
    ROW_FORMAT = DYNAMIC COMMENT ='存储程序的悲观锁的信息';

CREATE INDEX IDX_QRTZ_J_REQ_RECOVERY ON QRTZ_JOB_DETAILS(SCHED_NAME,REQUESTS_RECOVERY);
CREATE INDEX IDX_QRTZ_J_GRP ON QRTZ_JOB_DETAILS(SCHED_NAME,JOB_GROUP);

CREATE INDEX IDX_QRTZ_T_J ON QRTZ_TRIGGERS(SCHED_NAME,JOB_NAME,JOB_GROUP);
CREATE INDEX IDX_QRTZ_T_JG ON QRTZ_TRIGGERS(SCHED_NAME,JOB_GROUP);
CREATE INDEX IDX_QRTZ_T_C ON QRTZ_TRIGGERS(SCHED_NAME,CALENDAR_NAME);
CREATE INDEX IDX_QRTZ_T_G ON QRTZ_TRIGGERS(SCHED_NAME,TRIGGER_GROUP);
CREATE INDEX IDX_QRTZ_T_STATE ON QRTZ_TRIGGERS(SCHED_NAME,TRIGGER_STATE);
CREATE INDEX IDX_QRTZ_T_N_STATE ON QRTZ_TRIGGERS(SCHED_NAME,TRIGGER_NAME,TRIGGER_GROUP,TRIGGER_STATE);
CREATE INDEX IDX_QRTZ_T_N_G_STATE ON QRTZ_TRIGGERS(SCHED_NAME,TRIGGER_GROUP,TRIGGER_STATE);
CREATE INDEX IDX_QRTZ_T_NEXT_FIRE_TIME ON QRTZ_TRIGGERS(SCHED_NAME,NEXT_FIRE_TIME);
CREATE INDEX IDX_QRTZ_T_NFT_ST ON QRTZ_TRIGGERS(SCHED_NAME,TRIGGER_STATE,NEXT_FIRE_TIME);
CREATE INDEX IDX_QRTZ_T_NFT_MISFIRE ON QRTZ_TRIGGERS(SCHED_NAME,MISFIRE_INSTR,NEXT_FIRE_TIME);
CREATE INDEX IDX_QRTZ_T_NFT_ST_MISFIRE ON QRTZ_TRIGGERS(SCHED_NAME,MISFIRE_INSTR,NEXT_FIRE_TIME,TRIGGER_STATE);
CREATE INDEX IDX_QRTZ_T_NFT_ST_MISFIRE_GRP ON QRTZ_TRIGGERS(SCHED_NAME,MISFIRE_INSTR,NEXT_FIRE_TIME,TRIGGER_GROUP,TRIGGER_STATE);

CREATE INDEX IDX_QRTZ_FT_TRIG_INST_NAME ON QRTZ_FIRED_TRIGGERS(SCHED_NAME,INSTANCE_NAME);
CREATE INDEX IDX_QRTZ_FT_INST_JOB_REQ_RCVRY ON QRTZ_FIRED_TRIGGERS(SCHED_NAME,INSTANCE_NAME,REQUESTS_RECOVERY);
CREATE INDEX IDX_QRTZ_FT_J_G ON QRTZ_FIRED_TRIGGERS(SCHED_NAME,JOB_NAME,JOB_GROUP);
CREATE INDEX IDX_QRTZ_FT_JG ON QRTZ_FIRED_TRIGGERS(SCHED_NAME,JOB_GROUP);
CREATE INDEX IDX_QRTZ_FT_T_G ON QRTZ_FIRED_TRIGGERS(SCHED_NAME,TRIGGER_NAME,TRIGGER_GROUP);
CREATE INDEX IDX_QRTZ_FT_TG ON QRTZ_FIRED_TRIGGERS(SCHED_NAME,TRIGGER_GROUP);

CREATE TABLE IF NOT EXISTS `t_mapping`
(
    `mapping_id`              VARCHAR(64)   NOT NULL COMMENT '映射关系ID',
    `app_id`                  VARCHAR(64)   NOT NULL COMMENT '应用ID，agent id或workflow id',
    `app_version`             VARCHAR(64)   NULL COMMENT '应用版本id',
    `app_type`                VARCHAR(32)   NOT NULL COMMENT '应用类型，agent或workflow',
    `app_sub_type`            VARCHAR(100)  NULL COMMENT '发布版本子类型',
    `app_name`                VARCHAR(64)   NOT NULL COMMENT '应用名称',
    `resource_id`             VARCHAR(128)  NOT NULL COMMENT '关联的资源ID',
    `resource_type`           VARCHAR(32)   NOT NULL COMMENT '关联的资源类型，tool、repo或workflow',
    `resource_name`           VARCHAR(1000) NULL COMMENT '关联的资源名称',
    `resource_version`        VARCHAR(64)   NULL COMMENT '关联的资源版本',
    `valid`                   TINYINT       NOT NULL DEFAULT '1' COMMENT '关联关系是否有效',
    `resource_desc`           VARCHAR(2048) NULL COMMENT '关联的资源描述',
    `resource_choose_tools`   VARCHAR(2048) NULL COMMENT 'Agent配置的mcp内选择的工具',
    `created_on`              TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_on`              TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `reference_type`          VARCHAR(64)   NULL DEFAULT 'direct' COMMENT 'share表示跨空间共享引用，direct表示本空间直接引用',
    `resource_workspace_id`   VARCHAR(64)   NULL COMMENT '被引用元素所属的来源空间',
    `extends`                 MEDIUMTEXT    NULL COMMENT '额外信息',
    `app_workspace_id`        VARCHAR(64)   NULL COMMENT '引用元素所属的来源空间',
    PRIMARY KEY (`mapping_id`),
    KEY `idx_t_mapping_app_id` (`app_id`),
    KEY `idx_t_mapping_resource_id` (`resource_id`),
    KEY `idx_t_mapping_resource_version` (`resource_version`) USING BTREE,
    KEY `idx_t_mapping_app_version` (`app_version`) USING BTREE
    ) ENGINE = InnoDB
    DEFAULT CHARSET = utf8mb4
    COLLATE = utf8mb4_general_ci
    ROW_FORMAT = DYNAMIC COMMENT ='应用和资源的多对多关系映射表';

CREATE TABLE IF NOT EXISTS `t_release_version` (
    `id`              VARCHAR(64)   NOT NULL COMMENT 'UUID',
    `version_id`      VARCHAR(64)   NOT NULL COMMENT '发布版本唯一标识',
    `version_name`    VARCHAR(64)   NOT NULL COMMENT '版本名称',
    `version_note`    VARCHAR(1024)  NOT NULL COMMENT '版本说明',
    `app_id`          VARCHAR(64)   NOT NULL COMMENT '应用ID，agent id或workflow id',
    `app_type`        VARCHAR(32)   NOT NULL COMMENT '应用类型，agent或workflow',
    `status`          VARCHAR(32)   NULL     COMMENT '发布版本状态，normal或abnormal',
    `dsl_path`        VARCHAR(256)  NULL COMMENT 'DSL相对路径',
    `ir_path`         VARCHAR(256)  NULL COMMENT 'IR相对路径',
    `extend1`         TEXT          NULL COMMENT '扩展字段',
    `creator`         VARCHAR(64)   NULL     COMMENT '版本创建者',
    `creator_id`      VARCHAR(64)   CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL     COMMENT '版本创建者user id',
    `app_sub_type`    VARCHAR(100)  NULL COMMENT '发布版本子类型',
    `released_on`     TIMESTAMP     NULL DEFAULT CURRENT_TIMESTAMP COMMENT '发布时间',
    `deleted`         TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '逻辑删除标记：0-未删除，1-已删除',
    `updated_on`      TIMESTAMP     NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE INDEX `unique_index_app_version_id` (`app_id`, `version_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT='发布版本表';

CREATE TABLE IF NOT EXISTS `t_release_channel` (
    `id`              VARCHAR(64)   NOT NULL COMMENT 'UUID',
    `app_id`          VARCHAR(64)   NOT NULL COMMENT '应用ID，agent id或workflow id',
    `app_type`        VARCHAR(32)   NOT NULL COMMENT '应用类型，agent或workflow',
    `version_id`      VARCHAR(64)   NOT NULL COMMENT '发布版本唯一标识',
    `version_name`    VARCHAR(64)   NOT NULL COMMENT '版本名称',
    `channel_type`    VARCHAR(32)   NOT NULL COMMENT '发布通道类型',
    `entry_point`     VARCHAR(255)  NULL COMMENT '发布通道访问入口',
    `qr_code`         VARCHAR(1024) NULL     COMMENT '访问二维码',
    `short_code`      VARCHAR(16)   NULL     COMMENT '访问的短ID',
    `metadata`        VARCHAR(4096) NULL     COMMENT '发布元数据',
    `status`          VARCHAR(32)   NULL     COMMENT '发布通道状态，releasing、released、release_failed',
    `detail`          VARCHAR(1024) NULL     COMMENT '发布结果详情',
    `creator`         VARCHAR(64)   NULL     COMMENT '版本创建者',
    `creator_id`      VARCHAR(64)   CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL     COMMENT '版本创建者user id',
    `app_sub_type`    VARCHAR(100)  NULL     COMMENT '发布通道子类型',
    `released_on`     TIMESTAMP     NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '发布时间',
    `project_id`      VARCHAR(64)   CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL COMMENT '项目ID',
    `workspace_id`    VARCHAR(64)   NULL COMMENT '工作空间ID',
    `trace_id`        VARCHAR(64)   NULL COMMENT '溯源ID',
    `visibility_scope` VARCHAR(8)   NULL DEFAULT 'TENANT' COMMENT '可见范围：TENANT/PRIVATE/SHARED',
    `call_count`      INT           NULL DEFAULT 100 COMMENT '调用次数限制',
    PRIMARY KEY (`id`),
    KEY `index_t_release_channel_id` (`id`),
    KEY `idx_t_release_channel_app_version` (`app_id`, `version_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT='发布通道记录表';

CREATE TABLE IF NOT EXISTS `t_analytics_event` (
    `event_id`      VARCHAR(64)     NOT NULL COMMENT '事件id， 主键',
    `event_type`    VARCHAR(64)     NOT NULL COMMENT '事件类型',
    `user_id`       VARCHAR(255)    CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL COMMENT 'user id',
    `project_id`    VARCHAR(64)     CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL COMMENT 'project id',
    `app_type`      VARCHAR(255)    NULL COMMENT '应用类型',
    `app_id`        VARCHAR(128)   NULL COMMENT '应用id',
    `channel`       VARCHAR(255)    NULL COMMENT '应用发布渠道',
    `event_time`    TIMESTAMP       NULL DEFAULT CURRENT_TIMESTAMP COMMENT '事件时间',
    `event_date`    TIMESTAMP       NULL DEFAULT CURRENT_TIMESTAMP COMMENT '事件日期',
    `new_app_user`  TINYINT(1)      NULL DEFAULT 0,
    PRIMARY KEY (`event_id`),
    INDEX `event_time`(`event_time` ASC) USING BTREE,
    INDEX `event_date`(`event_date` ASC) USING BTREE,
    INDEX `app_id`(`app_id` ASC) USING BTREE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT='分析事件记录表';

CREATE TABLE IF NOT EXISTS `t_complex_intent` (
    `intent_id`         VARCHAR(64)     NOT NULL    COMMENT '意图id',
    `name`              VARCHAR(64)     NULL        COMMENT '名称',
    `project_id`        VARCHAR(64)     CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL        COMMENT 'project id',
    `domain_id`         VARCHAR(64)     NOT NULL DEFAULT '0' COMMENT '租户 ID',
    `description`       VARCHAR(255)    NULL        COMMENT '描述',
    `branches`          TEXT            NULL        COMMENT '分支数据',
    `creator_id`        VARCHAR(64)     CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL COMMENT '创建人ID',
    `branches_cnt`      INT             NULL COMMENT '分支数',
    `created_on`        TIMESTAMP       NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_on`        TIMESTAMP       NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `workspace_id`      VARCHAR(64)     NULL COMMENT '工作空间ID',
    `trace_id`          VARCHAR(64)     NULL COMMENT '溯源ID',
    PRIMARY KEY (`intent_id`),
    KEY `idx_t_complex_intent_domain` (`domain_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT='复杂意图表';

CREATE TABLE IF NOT EXISTS `t_complex_intent_branch` (
    `branch_id`        VARCHAR(64)     NOT NULL    COMMENT '主键id',
    `intent_id`         VARCHAR(64)     NOT NULL    COMMENT '意图id',
    `branch_index`      INT     NOT NULL    COMMENT '分支id索引',
    `project_id`        VARCHAR(64)     CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL        COMMENT 'project id',
    `branch_name`       VARCHAR(64)     NULL        COMMENT '分支名称',
    `content`           TEXT            NULL        COMMENT '分支数据',
    `faq_ids`           TEXT            NULL        COMMENT '存储的FAQ id列表',
    `creator_id`        VARCHAR(64)     CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL COMMENT '创建人ID',
    `created_on`        TIMESTAMP       NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_on`        TIMESTAMP       NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `workspace_id`      VARCHAR(64)     NULL COMMENT '工作空间ID',
    `trace_id`          VARCHAR(64)     NULL COMMENT '溯源ID',
    PRIMARY KEY (`branch_id`),
    KEY `idx_t_complex_intent_branch_intent` (`intent_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT='复杂意图分支表';

CREATE TABLE IF NOT EXISTS `t_credential`(
    `id`            VARCHAR(64)     NOT NULL        COMMENT 'Credential唯一标识ID，主键',
    `resource_id`   VARCHAR(64)     NOT NULL        COMMENT '资源id',
    `resource_type` VARCHAR(32)     NOT NULL        COMMENT '资源类型',
    `project_id`    VARCHAR(64)     CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL        COMMENT '租户 project id',
    `auth_keys`     VARCHAR(4096)   NOT NULL        COMMENT '凭证 list',
    `user_id`       VARCHAR(255)    CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL        COMMENT '使用者id',
    `workspace_id`  VARCHAR(64)     NULL COMMENT '工作空间ID',
    `domain_id`     VARCHAR(64)     NULL COMMENT '租户id',
    `created_on`    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_on`    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY(`id`),
    KEY `idx_t_credential_updated_on`(`updated_on`),
    KEY `idx_t_credential_domain_id` (`domain_id`),
    KEY `idx_t_credential_user_id_workspace_id_resource_id` (resource_id, user_id, workspace_id)
    ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = DYNAMIC COMMENT = '资源凭证表';

CREATE TABLE IF NOT EXISTS `t_workspace` (
    `id`               VARCHAR(64)   NOT NULL COMMENT '工作空间唯一标识',
    `project_id`       VARCHAR(64)   CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '项目唯一标识',
    `name`             VARCHAR(64)   NULL     COMMENT '工作空间名称',
    `flag`             VARCHAR(64)   NULL     COMMENT '标识符',
    `description`      VARCHAR(2048) NULL     COMMENT '工作空间描述',
    `icon`             MEDIUMTEXT    NULL     COMMENT '工作空间图标',
    `tenant_id`        VARCHAR(64)   NOT NULL COMMENT '租户唯一标识',
    `type`             VARCHAR(32)   NULL COMMENT '工作空间类型',
    `status`           VARCHAR(32)   NULL     COMMENT '工作空间状态',
    `created_on`       TIMESTAMP     NULL     DEFAULT CURRENT_TIMESTAMP                             COMMENT '工作空间创建时间',
    `creator`          VARCHAR(64)   NULL     COMMENT '工作空间创建者',
    `creator_id`       VARCHAR(64)   CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL COMMENT '工作空间创建者id',
    `updated_on`       TIMESTAMP     NULL     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '工作空间更新时间',
    `updater`          VARCHAR(64)   NULL     COMMENT '工作空间更新者',
    `updater_id`       VARCHAR(64)   NULL COMMENT '工作空间更新者id',
    `is_preset_agent`  INT           DEFAULT 0 NULL COMMENT '是否已经预置Agent教学模版，0标识未预置，1标识已预置',
    `domain_id`       VARCHAR(64)   NULL COMMENT '租户ID',
    PRIMARY KEY (`id`),
    KEY `index_t_workspace_id` (`id`),
    KEY `idx_t_workspace_domain` (`domain_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC  COMMENT='工作空间表';

CREATE TABLE IF NOT EXISTS t_workspace_member
(
    id            varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin not null comment '工作空间成员表ID',
    workspace_id  varchar(64) not null comment '工作空间表ID',
    member_id     varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin not null comment '用户ID',
    member_name   varchar(64) not null comment '成员名称',
    member_source varchar(32) not null comment '用户来源',
    domain_id     varchar(64) not null comment '租户ID',
    role          varchar(64) not null comment '角色',
    status        tinyint(1) default 1 not null comment '状态 1=启用,0=禁用',
    creator       varchar(64) not null comment '创建者',
    creator_id    varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin not null comment '创建者 user id',
    updater       varchar(64) not null comment '更新者',
    updater_id    varchar(64) not null comment '更新者 user id',
    created_on    timestamp default CURRENT_TIMESTAMP not null comment '创建时间',
    updated_on    timestamp default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP comment '更新时间',
    PRIMARY KEY (`id`),
    KEY idx_member_id (member_id),
    KEY idx_member_workspace_status (member_id, workspace_id, status),
    KEY idx_t_workspace_member_domain (domain_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT='工作空间成员表';

CREATE TABLE IF NOT EXISTS t_dependency
(
    id VARCHAR(64) NOT NULL COMMENT '资源包id' PRIMARY KEY,
    version_id VARCHAR(64) NOT NULL COMMENT '依赖包版本ID',
    name VARCHAR(32) NULL,
    function_graph_name VARCHAR(64) NULL COMMENT 'function graph名称',
    description VARCHAR(255) NULL COMMENT '资源包描述',
    runtime VARCHAR(64) NULL COMMENT '运行时语言',
    scope VARCHAR(16) NULL COMMENT '资源包可见范围',
    link TEXT NULL COMMENT '资源包链接',
    project_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL COMMENT '项目id',
    domain_id VARCHAR(64) NOT NULL DEFAULT '0' COMMENT '租户 ID',
    workspace_id VARCHAR(64) NULL COMMENT '空间id',
    creator_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '创建用户id',
    created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP NULL COMMENT '创建时间',
    updater_id VARCHAR(64) NULL COMMENT '更新用户id',
    updated_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    version TINYINT NULL COMMENT '版本号',
    deleted TINYINT(1) DEFAULT 0 NULL COMMENT '软删除标志',
    KEY idx_t_dependency_domain (domain_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT '应用中心函数依赖包表';

CREATE TABLE IF NOT EXISTS t_function
(
    id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '函数id' PRIMARY KEY,
    function_urn VARCHAR(256) NOT NULL COMMENT '函数标识',
    name VARCHAR(50) NOT NULL COMMENT '函数名称',
    function_name VARCHAR(64) NOT NULL COMMENT 'functionGraph函数名称',
    runtime VARCHAR(64) NULL COMMENT '运行时语言',
    usage_type VARCHAR(50) NOT NULL COMMENT '函数使用类型',
    function_input LONGTEXT NULL COMMENT '函数输入',
    function_output LONGTEXT NULL COMMENT '函数输出',
    concurrent_num TINYINT DEFAULT 1 NULL COMMENT '并发数',
    visibility VARCHAR(16) NULL COMMENT '函数可见性',
    description VARCHAR(256) NULL COMMENT '函数描述',
    function_expression VARCHAR(255) NULL COMMENT '函数表达式',
    function_code LONGBLOB NULL COMMENT '函数代码',
    code_type VARCHAR(255) NULL COMMENT '代码存储类型',
    project_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL COMMENT '项目id',
    domain_id VARCHAR(64) NOT NULL DEFAULT '0' COMMENT '租户 ID',
    workspace_id VARCHAR(64) NULL COMMENT '空间id',
    creator_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '创建用户id',
    created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP NULL COMMENT '创建时间',
    updater_id VARCHAR(64) NULL COMMENT '更新用户id',
    updated_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted TINYINT(1) DEFAULT 0 NULL COMMENT '软删除标志',
    trace_id VARCHAR(64) NULL COMMENT '溯源ID',
    template_version VARCHAR(64) NOT NULL DEFAULT 'v1' COMMENT '函数模版版本，v1表示老版本，v2表示新版本',
    KEY idx_t_function_domain (domain_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT '函数表';

CREATE TABLE IF NOT EXISTS t_function_dependency_map
(
    id VARCHAR(64) NOT NULL COMMENT '映射关系id' PRIMARY KEY,
    function_id VARCHAR(64) NOT NULL COMMENT '函数ID',
    function_name VARCHAR(64) NOT NULL COMMENT '函数名称',
    dependency_id VARCHAR(64) NOT NULL COMMENT '依赖包ID',
    version_id VARCHAR(64) NOT NULL COMMENT '依赖包版本ID',
    dependency_name VARCHAR(96) NULL COMMENT '依赖包名称',
    runtime VARCHAR(64) NULL COMMENT '运行时语言',
    scope VARCHAR(16) NULL COMMENT '资源包可见范围',
    link TEXT NULL COMMENT '资源包链接',
    valid TINYINT(1) NOT NULL DEFAULT '1' COMMENT '依赖关系是否有效',
    dependency_version INTEGER NULL DEFAULT 0 COMMENT '依赖包版本',
    KEY t_map_function_id_index (function_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT '函数和依赖包关系表';

CREATE TABLE IF NOT EXISTS `t_task` (
    `id`                VARCHAR(64)     NOT NULL COMMENT '任务 id， 主键',
    `name`              VARCHAR(64)     NOT NULL COMMENT '任务名称，可修改',
    `conversation_id`   VARCHAR(64)     NULL COMMENT '会话ID',
    `user_id`           VARCHAR(255)    CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL COMMENT 'user id',
    `project_id`        VARCHAR(64)     CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL COMMENT 'project id',
    `domain_id`         VARCHAR(64)     NULL COMMENT 'domain id',
    `workspace_id`      VARCHAR(64)     NULL COMMENT 'workspace id',
    `type`              VARCHAR(32)     NULL COMMENT '任务类型',
    `mode`              VARCHAR(32)     NULL COMMENT '任务模式，当前仅支持ASYNC',
    `app_id`            VARCHAR(64)     NULL COMMENT '对应工作流或agent id',
    `app_version`       VARCHAR(128)    NULL COMMENT '任务应用版本',
    `is_published`      TINYINT(1)      NULL COMMENT '此工作流是否是发布后',
    `status`            VARCHAR(32)     NULL COMMENT '任务状态',
    `inputs`            MEDIUMTEXT      NULL COMMENT '任务输入',
    `outputs`           MEDIUMTEXT      NULL COMMENT '任务输出',
    `timeout`           INTEGER         NULL COMMENT '工作流超时时间',
    `message`           VARCHAR(2048)   NULL COMMENT '提示消息',
    `create_time`       TIMESTAMP       NOT NULL COMMENT '创建时间',
    `start_time`        TIMESTAMP       NULL COMMENT '任务实际开始时间',
    `update_time`       TIMESTAMP       NULL COMMENT '任务更新日期',
    `finish_time`       TIMESTAMP       NULL COMMENT '任务结束日期',
    PRIMARY KEY (`id`),
    INDEX `idx_create_time`(`create_time` ASC) USING BTREE,
    INDEX `idx_status_time`(`status` ASC, `create_time` ASC) USING BTREE,
    INDEX `idx_finish_time`(`finish_time` ASC) USING BTREE,
    KEY `index_t_task_domain` (`domain_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT='任务记录表';

CREATE TABLE IF NOT EXISTS `t_apig_api_groups` (
    `ID` varchar(36) NOT NULL COMMENT 'API分组id',
    `NAME` text  COMMENT 'api分组名称',
    `DESCRIPTION` text,
    `TENANT_ID` varchar(64) DEFAULT NULL,
    `CREATED_BY_USER_ID` varchar(64) DEFAULT NULL,
    `LAST_UPDATED_BY_USER_ID` varchar(64) DEFAULT NULL,
    `CREATED_DATE` timestamp NULL DEFAULT NULL,
    `LAST_UPDATED_DATE` timestamp NULL DEFAULT NULL,
    `STATUS` varchar(16) NOT NULL,
    PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `t_apig_apis` (
                               `ID` varchar(36) NOT NULL COMMENT 'API id',
                               `NAME` text COMMENT 'api名称',
                               `GROUP_ID` varchar(64) NOT NULL COMMENT 'API分组id',
                               `DESCRIPTION` text,
                               `tenant_id` varchar(64) DEFAULT NULL,
                               `THROTTLING_POLICY_ID` varchar(64) DEFAULT NULL COMMENT '流控策略ID，为空则说明未开启流控。',
                               `API_POLICY_BIND_ID` varchar(64) DEFAULT NULL COMMENT 'api策略和api绑定的关系ID。',
                               `CREATED_BY_USER_ID` varchar(64) DEFAULT NULL,
                               `LAST_UPDATED_BY_USER_ID` varchar(64) DEFAULT NULL,
                               `CREATED_DATE` timestamp NULL DEFAULT NULL,
                               `LAST_UPDATED_DATE` timestamp NULL DEFAULT NULL,
                               `STATUS` varchar(16) NOT NULL,
                               PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `t_environment_manager_info`
(
    `id`           varchar(64)                         not null comment '主键'
        primary key,
    `name`         varchar(48)                         null comment '环境名称',
    `description`  varchar(128)                        null comment '描述',
    `is_default`   tinyint(1)                          null comment '是否默认',
    `status`       varchar(16)                         null comment '环境状态',
    `resources`    varchar(512)                        null comment '环境资源信息',
    `created_on`   timestamp default CURRENT_TIMESTAMP not null comment '环境创建时间',
    `creator_id`   varchar(64)                         null comment '环境创建者user id',
    `updated_on`   timestamp default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP comment '更新时间',
    `updater_id`   varchar(64)                         null comment '环境修改者user id',
    `project_id`   varchar(64)                         null comment '项目id',
    `domain_id`    varchar(64)                         null comment '账号id',
    KEY `idx_t_environment_manager_info_domain` (`domain_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS t_environment_variable_info
(
    id  varchar(64) not null comment '主键'
        primary key,
    env_variable text                                null comment '环境变量',
    created_on   timestamp default CURRENT_TIMESTAMP not null comment '环境创建时间',
    creator_id   varchar(64)  null comment '环境创建者user id',
    updated_on   timestamp default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP comment '更新时间',
    updater_id   varchar(64) null comment '环境修改者user id',
    project_id   varchar(64)  not null comment '项目id',
    workspace_id varchar(64)  not null comment '工作空间',
    env_id       varchar(64)  not null comment '环境id 关联环境表',
    KEY `idx_t_environment_variable_info_env_id` (env_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT '环境变量信息表';

CREATE TABLE IF NOT EXISTS `t_structured_message`
(
    `id`           VARCHAR(64)                         NOT NULL COMMENT '消息ID，主键',
    `name`         VARCHAR(128)                        NULL COMMENT '消息名称（如：无权限）',
    `category`     VARCHAR(64)                         NULL COMMENT '消息分类（如：异常）',
    `content`       text                               NULL COMMENT '消息体（JSON格式）',
    `status`       varchar(64)                         NULL comment '状态',
    `import_method` varchar(64)                        NULL COMMENT '导入方式，如：PAGE/UPLOAD/OTHER',
    `visibility`   VARCHAR(64)  DEFAULT 'WORKSPACE'    NULL COMMENT '可见范围：WORKSPACE/DOMAIN/USER/PROJECT',
    `workspace_id` VARCHAR(64)                         NULL COMMENT '工作空间ID',
    `domain_id`    VARCHAR(64)                         NULL COMMENT '域ID',
    `user_id`      VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL COMMENT '用户ID',
    `project_id`   VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '项目ID',
    `created_on`   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP NOT NULL COMMENT '创建时间',
    `creator_id`   VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL COMMENT '创建者ID',
    `updated_on`   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `updater_id`   VARCHAR(64)                         NULL COMMENT '更新者ID',
    PRIMARY KEY (`id`),
    INDEX `idx_project_visibility` (`project_id`, `visibility`),
    INDEX `idx_workspace` (`workspace_id`),
    INDEX `idx_category` (`category`)
    ) ENGINE = InnoDB
    DEFAULT CHARSET = utf8mb4
    COLLATE = utf8mb4_unicode_ci COMMENT ='结构化消息表';

CREATE TABLE IF NOT EXISTS `t_share_resource`
(
    `resource_id` VARCHAR(128) NOT NULL COMMENT '被共享的源元素ID' PRIMARY KEY,
    `resource_name` VARCHAR(64) NOT NULL COMMENT '被共享的源元素名称',
    `resource_type` VARCHAR(32) NOT NULL COMMENT '资源类型（agent、workflow、tool、mcp等）',
    `workspace_id` VARCHAR(64) NOT NULL COMMENT '源元素归属的空间ID',
    `workspace_name` VARCHAR(64) NOT NULL COMMENT '源元素归属的空间名称',
    `trace_id` VARCHAR(64) NULL COMMENT '被共享的源元素的溯源ID',
    `version_list` VARCHAR(4096) NOT NULL COMMENT '被共享的版本号，按最近顺序排序，多个版本号逗号分隔',
    `project_id` VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '当前企业项目ID',
    `tenant_id` VARCHAR(64) NOT NULL COMMENT '租户ID',
    `creator_id` VARCHAR(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '创建用户ID',
    `creator` VARCHAR(64) NOT NULL COMMENT '创建人',
    `create_time` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updater_id` VARCHAR(128) NOT NULL COMMENT '更新用户ID',
    `updater` VARCHAR(64) NOT NULL COMMENT '更新人',
    `update_time` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    KEY `index_t_share_resource_domain` (`tenant_id`),
    KEY `idx_t_share_resource_resource_type` (`resource_type`),
    KEY `idx_t_share_resource_resource_name` (`resource_name`),
    KEY `idx_t_share_resource_update_time` (`update_time`),
    KEY `idx_t_share_resource_project_workspace_resource` (`project_id`, `workspace_id`, `resource_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = DYNAMIC COMMENT = '跨空间共享资源表';

CREATE TABLE IF NOT EXISTS `t_share_scope`
(
    id VARCHAR(64) NOT NULL COMMENT '授权唯一标识' PRIMARY KEY,
    resource_id VARCHAR(64) NOT NULL COMMENT '被共享的源元素ID',
    resource_type VARCHAR(64) NOT NULL COMMENT '被共享资源类型（agent、workflow、tool、mcp等）',
    workspace_id VARCHAR(64) NOT NULL COMMENT '被授权的空间ID',
    project_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '当前企业项目ID',
    tenant_id VARCHAR(64) NOT NULL COMMENT '租户ID'
    ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE utf8mb4_general_ci ROW_FORMAT = DYNAMIC COMMENT = '保存元素跨空间共享的授权范围';

CREATE TABLE IF NOT EXISTS `t_users` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '用户唯一标识ID',
    `username` VARCHAR(100) NOT NULL UNIQUE COMMENT '用户登录名，唯一标识',
    `real_name` VARCHAR(100) COMMENT '用户真实姓名',
    `email` VARCHAR(100) COMMENT '用户电子邮箱',
    `phone` VARCHAR(20) COMMENT '用户联系电话',
    `department` VARCHAR(100) COMMENT '所属部门',
    `position` VARCHAR(100) COMMENT '职位/岗位',
    `external_id` VARCHAR(100) COMMENT '外部系统用户ID',
    `source` VARCHAR(20) COMMENT '用户来源系统',
    `domain_id` VARCHAR(100) COMMENT '所属域ID',
    `project_id` VARCHAR(100) COMMENT '所属项目ID',
    `created_time` DATETIME COMMENT '创建时间',
    `updated_time` DATETIME COMMENT '更新时间',
    `expire_time` DATETIME COMMENT '过期时间',
    `is_active` BOOLEAN DEFAULT TRUE COMMENT '是否激活状态',
    INDEX `idx_username` (`username`),
    INDEX `idx_external_id` (`external_id`),
    INDEX `idx_domain_project` (`domain_id`, `project_id`),
    INDEX `idx_created_time` (`created_time`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS  `t_sessions` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '会话记录ID',
    `session_id` VARCHAR(255) NOT NULL UNIQUE COMMENT '会话唯一标识ID',
    `user_id` BIGINT COMMENT '关联的用户ID',
    `username` VARCHAR(100) COMMENT '登录用户名',
    `ip_address` VARCHAR(45) COMMENT '登录IP地址',
    `user_agent` TEXT COMMENT '用户浏览器代理信息',
    `login_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '登录时间',
    `last_activity_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '最后活动时间',
    `expire_time` DATETIME COMMENT '会话过期时间',
    `logout_time` DATETIME COMMENT '登出时间',
    `status` VARCHAR(20) DEFAULT 'ACTIVE' COMMENT '会话状态',
    `domain_id` VARCHAR(100) COMMENT '所属域ID',
    `project_id` VARCHAR(100) COMMENT '所属项目ID',
    INDEX `idx_session_id` (`session_id`),
    INDEX `idx_session_user_id` (`user_id`),
    INDEX `idx_session_username` (`username`),
    INDEX `idx_session_status` (`status`),
    INDEX `idx_session_login_time` (`login_time`),
    INDEX `idx_session_expire_time` (`expire_time`),
    INDEX `idx_session_domain_project` (`domain_id`, `project_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS `t_card`
(
    `id`              varchar(64)  NOT NULL COMMENT 'ID',
    `name`            varchar(255) NOT NULL COMMENT '名称',
    `description`     varchar(2000) DEFAULT NULL COMMENT '描述',
    `icon`            mediumtext COMMENT '卡片图标',
    `resource_type`   varchar(64)  DEFAULT NULL COMMENT '卡片资源类型：Package、Site',
    `resource_url`    varchar(2000) DEFAULT NULL COMMENT '卡片资源URL',
    `metadata`        text COMMENT '元数据定义：CLOB字段',
    `project_id`      varchar(64) DEFAULT NULL COMMENT '项目ID',
    `workspace_id`    varchar(64) DEFAULT NULL COMMENT '工作空间ID',
    `status`          varchar(32) DEFAULT '1' COMMENT 'RELEASED-已发布 DRAFT-草稿',
    `asset_type`      varchar(255) DEFAULT NULL COMMENT '资产类型：platform 平台预置、（租户预置）、widgets 自定义',
    `last_version_id` varchar(64) DEFAULT NULL COMMENT '最新版本号',
    `created_on`      timestamp    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `creator_id`      varchar(64)  DEFAULT NULL COMMENT '创建人id',
    `creator`         varchar(64)  NOT NULL COMMENT '创建人',
    `updated_on`      timestamp    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '修改时间',
    `updater_id`      varchar(64)  DEFAULT NULL COMMENT '更新人id',
    `updater`         varchar(64)  NOT NULL COMMENT '修改人',
    `domain_id`       varchar(64)  DEFAULT '0' COMMENT '租户id',
    `trace_id`        varchar(64) DEFAULT NULL COMMENT '溯源ID',
    PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci
  ROW_FORMAT = DYNAMIC COMMENT ='卡片元数据表';

CREATE TABLE IF NOT EXISTS `t_custom_object` (
   `id` varchar(64) NOT NULL,
   `project_id`      VARCHAR(64)   NOT NULL COMMENT '租户的project id',
   `workspace_id` varchar(64)  NULL COMMENT '工作空间id',
   `name` varchar(64)  NULL COMMENT '对象名称',
   `description` varchar(255)  NULL COMMENT '对象描述',
   `object_schema` mediumtext  COMMENT '对象内容',
   `creator_id` varchar(64)  NULL COMMENT '创建人',
   `created_on` timestamp NULL COMMENT '创建时间',
   `updated_on` timestamp NULL COMMENT '更新时间',
   PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC ;

ALTER TABLE t_custom_object ADD COLUMN workspace_id varchar(64) NULL COMMENT '工作空间id';

CREATE TABLE IF NOT EXISTS t_workspace_mapping
(
    `id`                VARCHAR(64)  NOT NULL COMMENT '主键ID',
    `workspace_id`      VARCHAR(64)  NOT NULL COMMENT '内部空间ID',
    `mapping_id`        VARCHAR(128) NOT NULL COMMENT '外部映射ID',
    `extension_content` TEXT         NULL COMMENT '扩展内容（JSON）',
    `source`            VARCHAR(32)  NULL COMMENT '外部来源',
    PRIMARY KEY (id),
    KEY idx_mapping_id (mapping_id)
    ) ENGINE = InnoDB
    DEFAULT CHARSET = utf8mb4
    COLLATE = utf8mb4_general_ci
    ROW_FORMAT = DYNAMIC COMMENT ='工作空间映射表';

CREATE TABLE IF NOT EXISTS t_ops_tenant_config (
    `domain_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '租户id',
    `project_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '项目id',
    `log_group_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '日志组id',
    `log_stream_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '日志流id',
    PRIMARY KEY (`domain_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `t_history_mapping`
(
    `history_id`            varchar(64)  NOT NULL COMMENT '已删除资源关系表唯一标识',
    `mapping_id`            varchar(64)  NOT NULL COMMENT '映射关系ID',
    `app_id`                varchar(64)  NOT NULL COMMENT '应用ID，agent id或workflow id',
    `app_version`           varchar(64)           DEFAULT NULL COMMENT '应用版本id',
    `app_type`              varchar(32)  NOT NULL COMMENT '应用类型，agent或workflow',
    `app_sub_type`          varchar(100)          DEFAULT NULL COMMENT '发布版本子类型',
    `sub_type`              varchar(100)          DEFAULT NULL COMMENT '发布版本子类型',
    `app_name`              varchar(64)           DEFAULT NULL COMMENT '应用名称',
    `resource_id`           varchar(128) NOT NULL COMMENT '关联的资源ID',
    `resource_type`         varchar(32)  NOT NULL COMMENT '关联的资源类型，tool、repo或workflow',
    `resource_name`         varchar(1000)         DEFAULT NULL,
    `resource_version`      varchar(64)           DEFAULT NULL COMMENT '关联的资源版本',
    `valid`                 tinyint      NOT NULL DEFAULT '1' COMMENT '关联关系是否有效',
    `resource_desc`         varchar(2048) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '关联的资源描述',
    `created_on`            timestamp    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_on`            timestamp    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `reference_type`        varchar(64)           DEFAULT 'direct' COMMENT 'share表示跨空间共享引用，direct表示本空间直接引用',
    `resource_workspace_id` varchar(64)           DEFAULT NULL COMMENT '被引用元素所属的来源空间',
    `extends`               mediumtext COMMENT '额外信息',
    `app_workspace_id`      varchar(64)           DEFAULT NULL COMMENT '引用元素所属的来源空间',
    PRIMARY KEY (`history_id`) USING BTREE,
    KEY                     `idx_t_history_mapping_app_id` (`app_id`) USING BTREE,
    KEY                     `idx_t_history_mapping_resource_id` (`resource_id`) USING BTREE,
    KEY                     `idx_t_history_mapping_resource_version` (`resource_version`) USING BTREE,
    KEY                     `idx_t_history_mapping_app_version` (`app_version`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT='已删除资源的关系映射表';

CREATE TABLE `t_history_agent`
(
    `history_id`                  varchar(64) NOT NULL COMMENT '已删除Agent资源表唯一标识',
    `agent_id`                    varchar(64) NOT NULL COMMENT 'agentID标识',
    `project_id`                  varchar(64)          DEFAULT NULL,
    `name`                        varchar(64)          DEFAULT NULL COMMENT 'agent名称',
    `description`                 varchar(1024)        DEFAULT NULL COMMENT '应用描述',
    `icon`                        mediumtext COMMENT 'agent图标',
    `icon_name`                   varchar(64)          DEFAULT NULL COMMENT 'icon图标名称',
    `model_deployment_id`         varchar(128)         DEFAULT NULL,
    `model_name`                  varchar(128)         DEFAULT NULL COMMENT '大模型名称',
    `model_config`                varchar(256)         DEFAULT NULL,
    `instructions`                text,
    `trigger_list`                text COMMENT '触发器',
    `memory_variables`            text COMMENT 'agent的记忆变量',
    `prologue`                    varchar(512)         DEFAULT NULL COMMENT 'agent开场白',
    `suggest_queries`             varchar(4096)        DEFAULT NULL COMMENT 'agent推荐问',
    `additional_questions_config` text COMMENT '追问配置',
    `voice_interaction`           text COMMENT '语音配置',
    `dsl_path`                    varchar(256)         DEFAULT NULL COMMENT 'dsl文件存放路径',
    `ir_path`                     varchar(256)         DEFAULT NULL COMMENT 'IR文件相对路径',
    `type`                        varchar(32)          DEFAULT NULL COMMENT 'agent类型',
    `sub_type`                    varchar(50)          DEFAULT NULL COMMENT 'agent 子类型',
    `status`                      varchar(32)          DEFAULT NULL COMMENT 'agent状态',
    `creator`                     varchar(64)          DEFAULT NULL,
    `creator_id`                  varchar(64)          DEFAULT NULL,
    `created_on`                  timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'agent创建时间',
    `updated_on`                  timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'agent更新时间',
    `published_on`                timestamp NULL DEFAULT NULL COMMENT 'agent发布时间',
    `model_type`                  varchar(64)          DEFAULT NULL COMMENT '模型类型',
    `knowledge_retrieve_policy`   mediumtext COMMENT '知识检索策略（json）',
    `workflow_switch_enabled`     tinyint(1) NOT NULL DEFAULT '0' COMMENT '工作流跳转',
    `scheduling_mode`             varchar(32) NOT NULL DEFAULT 'ReAct' COMMENT 'agent调度模式，ReAct、RAG',
    `model`                       varchar(64)          DEFAULT NULL COMMENT '模型资产名称',
    `content_review`              mediumtext COMMENT 'Agent 内容审核',
    `workspace_id`                varchar(64)          DEFAULT NULL COMMENT '工作空间ID',
    `trace_id`                    varchar(64)          DEFAULT NULL COMMENT '溯源ID',
    `safety_barrier`              tinyint(1) DEFAULT NULL COMMENT 'Agent 安全护栏',
    `domain_id`                   varchar(64)          DEFAULT NULL,
    `agent_variables`             mediumtext COMMENT 'Agent变量列表',
    `memory_config`               mediumtext COMMENT '记忆配置',
    `plan_qa_independent`         tinyint(1) DEFAULT NULL COMMENT '规划与问答模型是否独立配置',
    `plan_model`                  varchar(64)          DEFAULT NULL COMMENT '规划模型资产名称',
    `plan_model_deployment_id`    varchar(128)         DEFAULT NULL COMMENT '规划模型的deployment_id',
    `plan_model_name`             varchar(128)         DEFAULT NULL COMMENT '规划模型名称',
    `plan_model_config`           varchar(256)         DEFAULT NULL COMMENT '规划模型参数配置',
    `plan_model_type`             varchar(64)          DEFAULT NULL COMMENT '规划模型类型',
    `deleted`                     tinyint(1) NOT NULL DEFAULT '0' COMMENT '逻辑删除标记：0-未删除，1-已删除',
    `is_shared`                   tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否已共享（0=否，1=是）',
    `is_share`                    tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否已共享（0=否，1=是）',
    PRIMARY KEY (`history_id`) USING BTREE,
    KEY                           `index_t_agent_history_agent_id` (`agent_id`) USING BTREE,
    KEY                           `IDX_T_AGENT_HISTORY_PROJECT_AGENT` (`project_id`,`agent_id`,`workspace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT='已删除的Agent资源表';

CREATE TABLE `t_history_release_version`
(
    `history_id`   varchar(64)   NOT NULL COMMENT '已删除资源版本表唯一标识',
    `id`           varchar(64)   NOT NULL COMMENT '资源版本表唯一标识',
    `version_id`   varchar(64)   NOT NULL COMMENT '发布版本唯一标识',
    `version_name` varchar(64)   NOT NULL COMMENT '版本名称',
    `version_note` varchar(1024) NOT NULL COMMENT '版本说明',
    `app_id`       varchar(64)   NOT NULL COMMENT '应用ID，agent id或workflow id',
    `app_type`     varchar(32)   NOT NULL COMMENT '应用类型，agent或workflow',
    `status`       varchar(32)  DEFAULT NULL COMMENT '发布版本状态，normal或abnormal',
    `dsl_path`     varchar(256) DEFAULT NULL COMMENT 'DSL相对路径',
    `ir_path`      varchar(256) DEFAULT NULL COMMENT 'IR相对路径',
    `creator`      varchar(64)  DEFAULT NULL COMMENT '版本创建者',
    `creator_id`   varchar(64)  DEFAULT NULL,
    `app_sub_type` varchar(100) DEFAULT NULL COMMENT '发布版本子类型',
    `sub_type`     varchar(100) DEFAULT NULL COMMENT '发布版本子类型',
    `released_on`  timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '发布时间',
    `extend1`      text COMMENT '扩展字段',
    `deleted`      tinyint(1) NOT NULL DEFAULT '0' COMMENT '逻辑删除标记：0-未删除，1-已删除',
    `updated_on`   timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`history_id`) USING BTREE,
    UNIQUE KEY `unique_index_app_version_id_delete` (`app_id`,`version_id`,`deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT='已删除资源的发布版本表';

CREATE TABLE IF NOT EXISTS `t_agent_code` (
    `id` VARCHAR ( 64 ) NOT NULL COMMENT 'agent唯一标识',
    `name` VARCHAR ( 64 ) DEFAULT NULL COMMENT 'agent名称',
    `description` VARCHAR ( 1024 ) DEFAULT NULL COMMENT '应用描述',
    `icon_name` VARCHAR ( 64 ) DEFAULT NULL COMMENT 'icon图标名称',
    `type` VARCHAR ( 32 ) DEFAULT NULL COMMENT 'agent类型',
    `status` VARCHAR ( 32 ) DEFAULT NULL COMMENT 'agent状态',
    `builder_sandbox_urn` VARCHAR ( 64 ) DEFAULT NULL COMMENT 'Relay Agent沙箱urn',
    `dev_sandbox_urn` VARCHAR ( 64 ) DEFAULT NULL COMMENT 'CodeInterpreter沙箱urn',
    `trace_id` VARCHAR ( 64 ) DEFAULT NULL COMMENT '溯源ID',
    `project_id` VARCHAR ( 64 ) DEFAULT NULL COMMENT '租户的project id',
    `workspace_id` VARCHAR ( 64 ) DEFAULT NULL COMMENT '工作空间ID',
    `domain_id` VARCHAR ( 64 ) DEFAULT NULL COMMENT '租户的domain id',
    `user_id` VARCHAR ( 64 ) DEFAULT NULL COMMENT '创建人id',
    `user_name` VARCHAR ( 64 ) DEFAULT NULL COMMENT '创建人名称',
    `created_on` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'agent创建时间',
    `updated_on` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'agent更新时间',
    `published_on` TIMESTAMP NULL DEFAULT NULL COMMENT 'agent发布时间',
    `auto_gen_flag` TINYINT(1) DEFAULT NULL COMMENT '自动生成标识,(0=否，1=是)',
    KEY `index_t_agent_id` ( `id` ) USING BTREE,
    KEY `index_t_agent_project_agent` ( `project_id`, `workspace_id`, `id` )
    ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = DYNAMIC COMMENT = '高代码智能体表';

CREATE TABLE IF NOT EXISTS `t_agent_code_session` (
    `id` VARCHAR ( 64 ) NOT NULL COMMENT '主键ID',
    `agent_id` VARCHAR ( 64 ) DEFAULT NULL COMMENT 'agent唯一标识',
    `session_id` VARCHAR ( 64 ) DEFAULT NULL COMMENT 'session id',
    `trace_id` VARCHAR ( 64 ) DEFAULT NULL COMMENT '溯源ID',
    `project_id` VARCHAR ( 64 ) DEFAULT NULL COMMENT '租户的project id',
    `workspace_id` VARCHAR ( 64 ) DEFAULT NULL COMMENT '工作空间ID',
    `created_on` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'agent创建时间',
    `updated_on` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'agent更新时间',
    PRIMARY KEY (`id`) USING BTREE
    ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = DYNAMIC COMMENT = '高代码智能体session会话表';

CREATE TABLE IF NOT EXISTS `t_skill` (
    `skill_id`        VARCHAR(64)   NOT NULL COMMENT '技能唯一标识。',
    `domain_id`       VARCHAR(64)   NOT NULL COMMENT '租户 ID',
    `name`            VARCHAR(64)   NOT NULL COMMENT '技能名称',
    `icon`            MEDIUMTEXT    NOT NULL COMMENT '图标(base64)。',
    `status`          VARCHAR(32)   NOT NULL COMMENT '状态：developed（可用），developing（开发中）',
    `source`          VARCHAR(32)   NOT NULL COMMENT '来源：custom（自定义），import（导入）',
    `description`     VARCHAR(1024) NOT NULL COMMENT '技能描述（最新版本）',
    `creator_id`      VARCHAR(64)   NOT NULL COMMENT '创建人id',
    `creator_name`    VARCHAR(64)   NOT NULL COMMENT '创建人名字',
    `created_at`      BIGINT        NOT NULL DEFAULT 0 COMMENT '创建时间',
    `updated_at`      BIGINT        NOT NULL DEFAULT 0 COMMENT '更新时间',
    `latest_version`  VARCHAR(64)   NULL COMMENT '最新版本号',
    `used_version`    VARCHAR(64)   NULL COMMENT '启用的版本号',
    `workspace_id`    VARCHAR(64)   NULL COMMENT '空间ID',
    `project_id`      VARCHAR(64)   NULL COMMENT '项目ID',
    `tag_id`          VARCHAR(64)   NULL COMMENT '资产分类',
    `published_asset` VARCHAR(64)   NOT NULL DEFAULT '0' COMMENT '资产是否已上架，1为上架',
    PRIMARY KEY (`skill_id`),
    KEY `idx_t_skill_domain_id` (`domain_id`)
    ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = DYNAMIC COMMENT = '技能表';

CREATE TABLE IF NOT EXISTS `t_skill_version` (
    `id`             VARCHAR(64)   NOT NULL COMMENT '系统版本号。版本唯一标识，格式 uuid',
    `skill_id`       VARCHAR(64)   NOT NULL COMMENT '关联的 Skill ID',
    `version_name`   VARCHAR(32)   NOT NULL COMMENT '系统版本名',
    `used`           TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '启用状态：1（已启用），0（未启用）',
    `name`           VARCHAR(64)   NOT NULL COMMENT '名字',
    `description`    VARCHAR(1024) NOT NULL COMMENT '版本描述',
    `obs_path`       VARCHAR(1024) NOT NULL COMMENT '制品包 OBS 路径',
    `creator_id`     VARCHAR(64)   NOT NULL COMMENT '创建人id',
    `creator_name`   VARCHAR(64)   NOT NULL COMMENT '创建人名字',
    `created_at`     BIGINT        NOT NULL DEFAULT 0 COMMENT '创建时间',
    PRIMARY KEY (`id`),
    KEY `idx_t_skill_version_skill_id` (`skill_id`)
    ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = DYNAMIC COMMENT = '技能版本表';

-- memory tables
CREATE TABLE IF NOT EXISTS `t_memory_repo` (
    `id` varchar(64) NOT NULL COMMENT '主键id',
    `name` varchar(64) NOT NULL COMMENT '记忆库名称',
    `description` VARCHAR(1000) COMMENT '描述',
    `icon` MEDIUMTEXT NULL COMMENT '图标',
    `time_span` int(11) DEFAULT NULL COMMENT '间隔时间，单位分钟',
    `conversation_round` int(11) DEFAULT NULL COMMENT '最大对话轮数',
    `long_term_memory_strategies` TEXT NOT NULL COMMENT '记忆提取策略，使用json string格式存储',
    `project_id` varchar(64) NOT NULL COMMENT '租户唯一标识',
    `workspace_id` varchar(64) NOT NULL COMMENT '项目空间ID',
    `domain_id` varchar(64) NOT NULL COMMENT 'IAM账号ID，租户ID',
    `created_user_id` varchar(64) NOT NULL COMMENT '创建人（用户ID）',
    `created_user_name` varchar(255) NOT NULL COMMENT '创建人（用户名）',
    `last_update_user_id` varchar(64) DEFAULT NULL COMMENT '更新人（用户id）',
    `last_update_user_name` varchar(255) DEFAULT NULL COMMENT '更新人（用户名）',
    `create_time` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='记忆库表';

-- model tables
CREATE TABLE IF NOT EXISTS `t_sys_model_service_provider` (
    `ID` varchar(40) NOT NULL,
    `PROVIDER_NAME` varchar(64) NOT NULL COMMENT '供应商名称',
    `PROVIDER_NAME_EN` varchar(64) NOT NULL COMMENT '供应商英文名称',
    `DESCRIPTION` varchar(1024) DEFAULT NULL COMMENT '供应商描述',
    `DESCRIPTION_EN` varchar(1024) DEFAULT NULL COMMENT '供应商英文描述',
    `TAGS` varchar(1024) DEFAULT NULL COMMENT '标签',
    `PROVIDER_URL` varchar(255) DEFAULT NULL COMMENT '厂商外链',
    `CREATED_DATE` bigint DEFAULT NULL COMMENT '创建日期',
    `LAST_UPDATED_DATE` bigint DEFAULT NULL COMMENT '更新日期',
    `LOGO` longtext COMMENT 'LOGO',
    `STATUS` varchar(16) DEFAULT NULL COMMENT '预留状态字段',
    `priority` int DEFAULT '100' COMMENT '优先级',
    PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT='系统预置模型服务供应商';

CREATE TABLE IF NOT EXISTS `t_user_model_service_provider` (
    `ID` varchar(64) NOT NULL,
    `PROVIDER_NAME` varchar(256) NOT NULL COMMENT '供应商名称',
    `PROVIDER_NAME_EN` varchar(256) NOT NULL COMMENT '供应商英文名称',
    `DESCRIPTION` varchar(1024) DEFAULT NULL COMMENT '供应商描述',
    `TAGS` varchar(1024) DEFAULT NULL COMMENT '标签',
    `PROVIDER_URL` varchar(255) DEFAULT NULL COMMENT '厂商外链',
    `CREATED_DATE` bigint DEFAULT NULL COMMENT '创建日期',
    `LAST_UPDATED_DATE` bigint DEFAULT NULL COMMENT '更新日期',
    `LOGO` longtext COMMENT 'LOGO',
    `STATUS` varchar(16) DEFAULT NULL COMMENT '预留状态字段',
    `DOMAIN_ID` varchar(40) NOT NULL COMMENT '账号ID',
    `PROJECT_ID` varchar(40) NOT NULL COMMENT '项目ID',
    `WORKSPACE_ID` varchar(40) NOT NULL COMMENT '空间ID',
    `CREATED_BY_USER` varchar(64) DEFAULT NULL COMMENT '创建用户名称',
    `LAST_UPDATED_BY_USER` varchar(64) DEFAULT NULL COMMENT '更新用户名称',
    `IDENTITY_ID` varchar(40) DEFAULT NULL,
    PRIMARY KEY (`ID`),
    KEY `usp_idx_PROJECT_AND_WORKSPACE` (`PROJECT_ID`,`WORKSPACE_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT='用户模型服务供应商';

CREATE TABLE IF NOT EXISTS `t_user_model_service_provider_backup` (
    `ID` varchar(64) NOT NULL,
    `PROVIDER_NAME` varchar(256) NOT NULL COMMENT '供应商名称',
    `PROVIDER_NAME_EN` varchar(256) NOT NULL COMMENT '供应商英文名称',
    `DESCRIPTION` varchar(1024) DEFAULT NULL COMMENT '供应商描述',
    `TAGS` varchar(1024) DEFAULT NULL COMMENT '标签',
    `PROVIDER_URL` varchar(255) DEFAULT NULL COMMENT '厂商外链',
    `CREATED_DATE` bigint DEFAULT NULL COMMENT '创建日期',
    `LAST_UPDATED_DATE` bigint DEFAULT NULL COMMENT '更新日期',
    `LOGO` longtext COMMENT 'LOGO',
    `STATUS` varchar(16) DEFAULT NULL COMMENT '预留状态字段',
    `DOMAIN_ID` varchar(40) NOT NULL COMMENT '账号ID',
    `PROJECT_ID` varchar(40) NOT NULL COMMENT '项目ID',
    `WORKSPACE_ID` varchar(40) NOT NULL COMMENT '空间ID',
    `CREATED_BY_USER` varchar(64) DEFAULT NULL COMMENT '创建用户名称',
    `LAST_UPDATED_BY_USER` varchar(64) DEFAULT NULL COMMENT '更新用户名称',
    `IDENTITY_ID` varchar(40) DEFAULT NULL,
    PRIMARY KEY (`ID`),
    KEY `PB_USP_IDX_PROJECT_AND_WORKSPACE` (`PROJECT_ID`,`WORKSPACE_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT='用户模型服务供应商';

CREATE TABLE IF NOT EXISTS `t_provider_auth_metadata` (
    `ID` varchar(64) NOT NULL,
    `PROVIDER_ID` varchar(64) DEFAULT NULL,
    `AUTH_TYPE` varchar(32) NOT NULL COMMENT '认证类型',
    `AUTH_INFO` varchar(1024) NOT NULL COMMENT '鉴权元数据定义',
    `AUTH_URL` varchar(256) DEFAULT NULL COMMENT '获取鉴权的url地址',
    `CREATED_BY_USER` varchar(64) DEFAULT NULL COMMENT '创建人ID',
    `CREATED_DATE` bigint DEFAULT NULL COMMENT '创建时间',
    `LAST_UPDATED_DATE` bigint DEFAULT NULL COMMENT '最近更新时间',
    `DOMAIN_ID` varchar(64) NOT NULL COMMENT '租户',
    `PROJECT_ID` varchar(64) NOT NULL COMMENT '项目空间ID',
    `WORKSPACE_ID` varchar(40) NOT NULL COMMENT '空间ID',
    `IDENTITY_ID` varchar(40) DEFAULT NULL,
    PRIMARY KEY (`ID`),
    KEY `idx_auth_metadata_PROVIDER_ID` (`PROVIDER_ID`),
    KEY `pm_idx_PROJECT_AND_WORKSPACE` (`PROJECT_ID`,`WORKSPACE_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT='服务供应商认证元数据定义';

CREATE TABLE IF NOT EXISTS `t_provider_auth_metadata_backup` (
    `ID` varchar(64) NOT NULL,
    `PROVIDER_ID` varchar(64) DEFAULT NULL,
    `AUTH_TYPE` varchar(32) NOT NULL COMMENT '认证类型',
    `AUTH_INFO` varchar(1024) NOT NULL COMMENT '鉴权元数据定义',
    `AUTH_URL` varchar(256) DEFAULT NULL COMMENT '获取鉴权的url地址',
    `CREATED_BY_USER` varchar(64) DEFAULT NULL COMMENT '创建人ID',
    `CREATED_DATE` bigint DEFAULT NULL COMMENT '创建时间',
    `LAST_UPDATED_DATE` bigint DEFAULT NULL COMMENT '最近更新时间',
    `DOMAIN_ID` varchar(64) NOT NULL COMMENT '租户',
    `PROJECT_ID` varchar(64) NOT NULL COMMENT '项目空间ID',
    `WORKSPACE_ID` varchar(40) NOT NULL COMMENT '空间ID',
    `IDENTITY_ID` varchar(40) DEFAULT NULL,
    PRIMARY KEY (`ID`),
    KEY `AMB_IDX_PROVIDER_ID` (`PROVIDER_ID`),
    KEY `AMB_PM_IDX_PROJECT_AND_WORKSPACE` (`PROJECT_ID`,`WORKSPACE_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT='服务供应商认证元数据定义';

CREATE TABLE IF NOT EXISTS `t_provider_auth_info` (
    `ID` varchar(64) NOT NULL,
    `PROVIDER_ID` varchar(64) DEFAULT NULL,
    `AUTH_METADATA_ID` varchar(64) DEFAULT NULL,
    `AUTH_TYPE` varchar(32) NOT NULL COMMENT '认证类型',
    `AUTH_INFO` TEXT NULL COMMENT '认证信息',
    `CREATED_BY_USER` varchar(64) NOT NULL COMMENT '创建人ID',
    `CREATED_DATE` bigint NOT NULL COMMENT '创建时间',
    `LAST_UPDATED_DATE` bigint NOT NULL COMMENT '最近更新时间',
    `DOMAIN_ID` varchar(64) NOT NULL COMMENT '租户ID',
    `PROJECT_ID` varchar(64) NOT NULL COMMENT '项目空间ID',
    `WORKSPACE_ID` varchar(40) NOT NULL COMMENT '空间ID',
    `IDENTITY_ID` varchar(40) DEFAULT NULL,
    `SYNC_STATUS` varchar(40) default 'finish',
    PRIMARY KEY (`ID`),
    UNIQUE KEY `uq_idx_PROJECT_AND_WORKSPACE` (`PROJECT_ID`,`WORKSPACE_ID`,`AUTH_METADATA_ID`),
    KEY `idx_PROVIDER_ID` (`PROVIDER_ID`),
    KEY `AUTH_SYNC_STATUS_IDX` (`SYNC_STATUS`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT='模型服务供应商鉴权认证信息';

CREATE TABLE IF NOT EXISTS `t_provider_auth_info_backup` (
    `ID` varchar(64) NOT NULL,
    `PROVIDER_ID` varchar(64) DEFAULT NULL,
    `AUTH_METADATA_ID` varchar(64) DEFAULT NULL,
    `AUTH_TYPE` varchar(32) NOT NULL COMMENT '认证类型',
    `AUTH_INFO` TEXT NULL COMMENT '认证信息',
    `CREATED_BY_USER` varchar(64) NOT NULL COMMENT '创建人ID',
    `CREATED_DATE` bigint NOT NULL COMMENT '创建时间',
    `LAST_UPDATED_DATE` bigint NOT NULL COMMENT '最近更新时间',
    `DOMAIN_ID` varchar(64) NOT NULL COMMENT '租户ID',
    `PROJECT_ID` varchar(64) NOT NULL COMMENT '项目空间ID',
    `WORKSPACE_ID` varchar(40) NOT NULL COMMENT '空间ID',
    `IDENTITY_ID` varchar(40) DEFAULT NULL,
    `SYNC_STATUS` varchar(40) default 'finish',
    PRIMARY KEY (`ID`),
    UNIQUE KEY `AIB_UQ_IDX_PROJECT_AND_WORKSPACE` (`PROJECT_ID`,`WORKSPACE_ID`,`AUTH_METADATA_ID`),
    KEY `AIB_IDX_PROVIDER_ID` (`PROVIDER_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT='模型服务供应商鉴权认证信息';

CREATE TABLE IF NOT EXISTS `t_model_service` (
    `ID` varchar(80) NOT NULL,
    `PROVIDER_ID` varchar(64) DEFAULT NULL,
    `SERVICE_NAME` varchar(64) NOT NULL COMMENT '模型服务名称',
    `SERVICE_KEY` varchar(128) NOT NULL COMMENT 'MODEL_SERVICE_KEY模型服务关键字',
    `MODEL_NAME` varchar(64) NOT NULL COMMENT '模型名称',
    `MODEL_VERSION` varchar(64) NOT NULL COMMENT '模型版本',
    `MODEL_TYPE` varchar(32) NOT NULL COMMENT '模型功能类型，枚举值LLM、TEXT-TO-IMAGE、IMAGE-TO-TEXT、AUDIO-TO-TEXT、Text-Embedding',
    `MODEL_TAGS` text COMMENT '模型标签',
    `MODEL_DESCRIPTION` text COMMENT '模型描述',
    `MODEL_DESCRIPTION_EN` text COMMENT '模型英文描述',
    `MODEL_DEPLOY_TYPE` varchar(32) NOT NULL COMMENT '模型部署类型，枚举值PLATFORM-INTEGRATION、PRIVATE-INTEGRATION',
    `DOCUMENT_URL` varchar(255) DEFAULT NULL COMMENT '模型描述md文件的obs地址',
    `MODEL_SIZE` float DEFAULT NULL COMMENT '模型规模，单位为B',
    `CONTEXT_LENGTH` int DEFAULT NULL COMMENT '模型上下文长度，大语言模型适用',
    `MODEL_PRIORITY` int unsigned DEFAULT NULL COMMENT '模型优先级',
    `DOMAIN_ID` varchar(64) NOT NULL,
    `PROJECT_ID` varchar(64) NOT NULL COMMENT '项目空间ID',
    `WORKSPACE_ID` varchar(40) NOT NULL COMMENT '空间ID',
    `CREATED_BY_USER` varchar(64) DEFAULT 'SYSTEM' COMMENT '创建人ID',
    `LAST_UPDATED_BY_USER` varchar(64) DEFAULT 'SYSTEM' COMMENT '最近修改人ID',
    `CREATED_DATE` bigint DEFAULT NULL COMMENT '创建时间',
    `LAST_UPDATED_DATE` bigint DEFAULT NULL COMMENT '最近更新时间',
    `API_URL` varchar(256) NOT NULL DEFAULT '' COMMENT 'API URL',
    `IS_REASONING` tinyint DEFAULT NULL COMMENT '模型是否支持思考',
    `IS_SUPPORT_CLOSE_REASONING` tinyint DEFAULT NULL COMMENT '深度思考开关',
    `IS_NETWORK` tinyint DEFAULT NULL COMMENT '是否支持联网',
    `IS_SUPPORT_FUNCTION` tinyint NOT NULL DEFAULT '0' COMMENT '是否支持FunctionCall',
    `INTERFACE_PROTOCOL` varchar(32) NOT NULL DEFAULT '' COMMENT '接口协议',
    `IS_SUPPORT_STREAM` tinyint NOT NULL DEFAULT '1' COMMENT '是否支持流式请求',
    `AUTH_METADATA_ID` varchar(64) DEFAULT NULL,
    `SYSTEM_PROMPT` varchar(1024) default null comment '模型推荐system prompt',
    `PUBLISH_STATUS` varchar(16) NOT NULL DEFAULT 'offline' COMMENT '发布状态:offline online',
    `THROTTLING_POLICY` int default -1 comment '流控策略',
    `LOGO` longtext COMMENT 'LOGO',
    `STATUS` varchar(40) DEFAULT NULL,
    `IDENTITY_ID` varchar(80) DEFAULT NULL,
    `IS_PUBLIC` tinyint DEFAULT 0 COMMENT '是否公开',
    `SYNC_STATUS` varchar(40) default 'finish',
    `DISCLAIMER`  text DEFAULT NULL COMMENT '模型免责声明',
    `DISCLAIMER_EN`  text DEFAULT NULL COMMENT '模型免责声明',
    PRIMARY KEY (`ID`),
    KEY `SERVICE_NAME_IDX` (`PROJECT_ID`,`WORKSPACE_ID`,`SERVICE_NAME`),
    KEY `PROVIDER_ID_INDEX` (`PROVIDER_ID`) USING BTREE,
    KEY `PUBLIC_TAG_IDX` (`IS_PUBLIC`),
    KEY `MODEL_SYNC_STATUS_IDX` (`SYNC_STATUS`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `t_model_service_backup` (
    `ID` varchar(80) NOT NULL,
    `PROVIDER_ID` varchar(64) DEFAULT NULL,
    `SERVICE_NAME` varchar(64) NOT NULL COMMENT '模型服务名称',
    `SERVICE_KEY` varchar(128) NOT NULL COMMENT 'MODEL_SERVICE_KEY模型服务关键字',
    `MODEL_NAME` varchar(64) NOT NULL COMMENT '模型名称',
    `MODEL_VERSION` varchar(64) NOT NULL COMMENT '模型版本',
    `MODEL_TYPE` varchar(32) NOT NULL COMMENT '模型功能类型，枚举值LLM、TEXT-TO-IMAGE、IMAGE-TO-TEXT、AUDIO-TO-TEXT、Text-Embedding',
    `MODEL_TAGS` text COMMENT '模型标签',
    `MODEL_DESCRIPTION` text COMMENT '模型描述',
    `MODEL_DEPLOY_TYPE` varchar(32) NOT NULL COMMENT '模型部署类型，枚举值PLATFORM-INTEGRATION、PRIVATE-INTEGRATION',
    `DOCUMENT_URL` varchar(255) DEFAULT NULL COMMENT '模型描述md文件的obs地址',
    `MODEL_SIZE` float DEFAULT NULL COMMENT '模型规模，单位为B',
    `CONTEXT_LENGTH` int DEFAULT NULL COMMENT '模型上下文长度，大语言模型适用',
    `MODEL_PRIORITY` int unsigned DEFAULT NULL COMMENT '模型优先级',
    `DOMAIN_ID` varchar(64) NOT NULL,
    `PROJECT_ID` varchar(64) NOT NULL COMMENT '项目空间ID',
    `WORKSPACE_ID` varchar(40) NOT NULL COMMENT '空间ID',
    `CREATED_BY_USER` varchar(64) DEFAULT 'SYSTEM' COMMENT '创建人ID',
    `LAST_UPDATED_BY_USER` varchar(64) DEFAULT 'SYSTEM' COMMENT '最近修改人ID',
    `CREATED_DATE` bigint DEFAULT NULL COMMENT '创建时间',
    `LAST_UPDATED_DATE` bigint DEFAULT NULL COMMENT '最近更新时间',
    `API_URL` varchar(256) NOT NULL DEFAULT '' COMMENT 'API URL',
    `IS_REASONING` tinyint DEFAULT NULL COMMENT '模型是否支持思考',
    `IS_NETWORK` tinyint DEFAULT NULL COMMENT '是否支持联网',
    `IS_SUPPORT_FUNCTION` tinyint NOT NULL DEFAULT '0' COMMENT '是否支持FunctionCall',
    `INTERFACE_PROTOCOL` varchar(32) NOT NULL DEFAULT '' COMMENT '接口协议',
    `IS_SUPPORT_STREAM` tinyint NOT NULL DEFAULT '1' COMMENT '是否支持流式请求',
    `AUTH_METADATA_ID` varchar(64) DEFAULT NULL,
    `SYSTEM_PROMPT` varchar(1024) default null comment '模型推荐system prompt',
    `PUBLISH_STATUS` varchar(16) NOT NULL DEFAULT 'offline' COMMENT '发布状态:offline online',
    `THROTTLING_POLICY` int default -1 comment '流控策略',
    `LOGO` longtext COMMENT 'LOGO',
    `STATUS` varchar(40) DEFAULT NULL,
    `IDENTITY_ID` varchar(40) DEFAULT NULL,
    `IS_PUBLIC` tinyint DEFAULT 0 COMMENT '是否公开',
    `SYNC_STATUS` varchar(40) default 'finish',
    PRIMARY KEY (`ID`),
    KEY `MSB_SERVICE_NAME_IDX` (`PROJECT_ID`,`WORKSPACE_ID`,`SERVICE_NAME`),
    KEY `MSB_PROVIDER_ID_INDEX` (`PROVIDER_ID`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `t_model_service_metadata` (
    `ID` varchar(64) NOT NULL COMMENT '唯一主键ID',
    `TYPE` varchar(16) NOT NULL COMMENT 'metadata类型, model_type, logo等',
    `ATTR_KEY` varchar(64) NOT NULL,
    `ATTR_VALUE` text NOT NULL,
    PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `t_free_model_service` (
    `ID` varchar(40) NOT NULL,
    `PROVIDER_ID` varchar(40) DEFAULT NULL,
    `SERVICE_NAME` varchar(64) NOT NULL COMMENT '模型服务名称',
    `SERVICE_KEY` varchar(128) NOT NULL COMMENT 'MODEL_SERVICE_KEY模型服务关键字',
    `MODEL_NAME` varchar(64) NOT NULL COMMENT '模型名称',
    `MODEL_VERSION` varchar(64) NOT NULL COMMENT '模型版本',
    `MODEL_TYPE` varchar(32) NOT NULL COMMENT '模型功能类型，枚举值LLM、TEXT-TO-IMAGE、IMAGE-TO-TEXT、AUDIO-TO-TEXT、Text-Embedding',
    `MODEL_TAGS` text COMMENT '模型标签',
    `MODEL_DESCRIPTION` text COMMENT '模型描述',
    `MODEL_DEPLOY_TYPE` varchar(32) NOT NULL COMMENT '模型部署类型，枚举值PLATFORM-INTEGRATION、PRIVATE-INTEGRATION',
    `DOCUMENT_URL` varchar(255) DEFAULT NULL COMMENT '模型描述md文件的obs地址',
    `MODEL_SIZE` float DEFAULT NULL COMMENT '模型规模，单位为B',
    `CONTEXT_LENGTH` int DEFAULT NULL COMMENT '模型上下文长度，大语言模型适用',
    `MODEL_PRIORITY` int unsigned DEFAULT NULL COMMENT '模型优先级',
    `DOMAIN_ID` varchar(64) NOT NULL,
    `PROJECT_ID` varchar(64) NOT NULL COMMENT '项目空间ID',
    `WORKSPACE_ID` varchar(40) NOT NULL COMMENT '空间ID',
    `CREATED_BY_USER` varchar(64) DEFAULT 'SYSTEM' COMMENT '创建人ID',
    `LAST_UPDATED_BY_USER` varchar(64) DEFAULT 'SYSTEM' COMMENT '最近修改人ID',
    `CREATED_DATE` bigint DEFAULT NULL COMMENT '创建时间',
    `LAST_UPDATED_DATE` bigint DEFAULT NULL COMMENT '最近更新时间',
    `API_URL` varchar(256) NOT NULL DEFAULT '' COMMENT 'API URL',
    `IS_REASONING` tinyint DEFAULT NULL COMMENT '模型是否支持思考',
    `IS_NETWORK` tinyint DEFAULT NULL COMMENT '是否支持联网',
    `IS_SUPPORT_FUNCTION` tinyint NOT NULL DEFAULT '0' COMMENT '是否支持FunctionCall',
    `INTERFACE_PROTOCOL` varchar(32) NOT NULL DEFAULT '' COMMENT '接口协议',
    `IS_SUPPORT_STREAM` tinyint NOT NULL DEFAULT '1' COMMENT '是否支持流式请求',
    `AUTH_METADATA_ID` varchar(64) DEFAULT NULL,
    `SYSTEM_PROMPT` varchar(1024) default null comment '模型推荐system prompt',
    `PUBLISH_STATUS` varchar(16) NOT NULL DEFAULT 'offline' COMMENT '发布状态:offline online',
    `THROTTLING_POLICY` int default -1 comment '流控策略',
    `LOGO` longtext COMMENT 'LOGO',
    `STATUS` varchar(40) DEFAULT NULL,
    PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `t_router_strategy` (
    `ID` varchar(64)  NOT NULL COMMENT '模型路由策略ID',
    `STRATEGY_NAME` varchar(64)  NOT NULL COMMENT '模型路由策略名称',
    `STRATEGY_TYPE` varchar(32)  COMMENT '模型路由策略类型',
    `STRATEGY_KEY` varchar(128)  NOT NULL COMMENT '模型路由策略调用ID',
    `STRATEGY_TAGS` text  NULL COMMENT '模型路由策略标签',
    `STRATEGY_DESCRIPTION` text  NULL COMMENT '模型路由策略描述',
    `SERVICE_ID_LIST` text  NULL COMMENT '模型服务ID列表',
    `STRATEGY_TIMEOUT` int NULL DEFAULT NULL COMMENT '模型路由策略超时时间',
    `STRATEGY_RETRY_COUNT` int NULL DEFAULT NULL COMMENT '模型服务重试次数',
    `SERVICE_COUNT` int NULL DEFAULT NULL COMMENT '模型服务数量',
    `PREPARE_ATTRIBUTE` text  NULL COMMENT '预留属性，格式为JSON',
    `DOMAIN_ID` varchar(64)  NOT NULL COMMENT 'DMOAINID',
    `PROJECT_ID` varchar(64)  NOT NULL COMMENT '项目ID',
    `WORKSPACE_ID` varchar(64)  NOT NULL COMMENT '空间ID',
    `CREATED_BY_USER_NAME` varchar(64)  NULL DEFAULT 'SYSTEM' COMMENT '创建人',
    `LAST_UPDATED_BY_USER_NAME` varchar(64)  NULL DEFAULT NULL COMMENT '最近使用人',
    `CREATED_DATE` BIGINT(20) NULL DEFAULT NULL COMMENT '创建时间',
    `LAST_UPDATED_DATE` BIGINT(20) NULL DEFAULT NULL COMMENT '最近更新时间',
    `TRACE_ID` varchar(64)  NOT NULL COMMENT '模型路由策略traceId',
    PRIMARY KEY (`ID`) ,
    INDEX `PW_ID_INDEX`(`PROJECT_ID`, `WORKSPACE_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `t_router_strategy_backup` (
    `ID` varchar(64)  NOT NULL COMMENT '模型路由策略ID',
    `STRATEGY_NAME` varchar(64)  NOT NULL COMMENT '模型路由策略名称',
    `STRATEGY_TYPE` varchar(32)  COMMENT '模型路由策略类型',
    `STRATEGY_KEY` varchar(128)  NOT NULL COMMENT '模型路由策略调用ID',
    `STRATEGY_TAGS` text  NULL COMMENT '模型路由策略标签',
    `STRATEGY_DESCRIPTION` text  NULL COMMENT '模型路由策略描述',
    `SERVICE_ID_LIST` text  NULL COMMENT '模型服务ID列表',
    `STRATEGY_TIMEOUT` int NULL DEFAULT NULL COMMENT '模型路由策略超时时间',
    `STRATEGY_RETRY_COUNT` int NULL DEFAULT NULL COMMENT '模型服务重试次数',
    `SERVICE_COUNT` int NULL DEFAULT NULL COMMENT '模型服务数量',
    `PREPARE_ATTRIBUTE` text  NULL COMMENT '预留属性，格式为JSON',
    `DOMAIN_ID` varchar(64)  NOT NULL COMMENT 'DMOAINID',
    `PROJECT_ID` varchar(64)  NOT NULL COMMENT '项目ID',
    `WORKSPACE_ID` varchar(64)  NOT NULL COMMENT '空间ID',
    `CREATED_BY_USER_NAME` varchar(64)  NULL DEFAULT 'SYSTEM' COMMENT '创建人',
    `LAST_UPDATED_BY_USER_NAME` varchar(64)  NULL DEFAULT NULL COMMENT '最近使用人',
    `CREATED_DATE` BIGINT(20) NULL DEFAULT NULL COMMENT '创建时间',
    `LAST_UPDATED_DATE` BIGINT(20) NULL DEFAULT NULL COMMENT '最近更新时间',
    PRIMARY KEY (`ID`) ,
    INDEX `SB_PW_ID_INDEX`(`PROJECT_ID`, `WORKSPACE_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `t_api_keys` (
    `API_KEY_ID` VARCHAR(80) NOT NULL COMMENT 'API Key 唯一标识，UUID',
    `API_KEY_NAME` VARCHAR(64) NOT NULL COMMENT 'API Key 名称',
    `API_KEY_VALUE` VARCHAR(256) NOT NULL COMMENT 'API Key 加密后的值',
    `DOMAIN_ID` varchar(64)  NOT NULL COMMENT 'DOMAINID',
    `PROJECT_ID` varchar(64)  NOT NULL COMMENT '项目ID',
    `WORKSPACE_ID` varchar(64)  NOT NULL COMMENT '空间ID',
    `CREATED_BY_USER_NAME` varchar(64)  NULL DEFAULT 'SYSTEM' COMMENT '创建人',
    `LAST_UPDATED_BY_USER_NAME` varchar(64)  NULL DEFAULT NULL COMMENT '最近使用人',
    `CREATED_DATE` BIGINT(20) NULL DEFAULT NULL COMMENT '创建时间',
    `DESCRIPTION` VARCHAR(1024) NOT NULL COMMENT 'API Key 描述',
    `USER_ID` VARCHAR(64) NOT NULL COMMENT '用户ID',
    PRIMARY KEY (`API_KEY_ID`) ,
    INDEX `AK_PW_ID_INDEX`(`PROJECT_ID`, `WORKSPACE_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `t_provider_auth_bound_records`(
    `ID` varchar(64) NOT NULL COMMENT '主键Id',
    `PROVIDER_AUTH_ID` varchar(64) NOT NULL COMMENT '模型供应商鉴权信息配置id',
    `DOMAIN_ID` varchar(64) NOT NULL COMMENT '租户DomainId',
    `PROVIDER_ID` varchar(64) DEFAULT NULL,
    `CREATED_BY_USER` varchar(64) DEFAULT 'SYSTEM' COMMENT '绑定人ID',
    `CREATED_DATE` bigint DEFAULT NULL COMMENT '鉴权绑定时间',
    PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `t_user_model_subscribe_settings`(
    `ID` varchar(64) NOT NULL COMMENT '主键Id',
    `DOMAIN_ID` varchar(64) NOT NULL COMMENT '租户DomainId',
    `PROJECT_ID` varchar(64)  DEFAULT NULL COMMENT '租户项目ID',
    `IS_AUTO_SUBSCRIBE_NEW_MODEL` tinyint DEFAULT 0 COMMENT '是否自动开通新增模型; 0: 否, 1: 是; 默认为0;',
    `CREATED_DATE` bigint DEFAULT NULL COMMENT '创建时间',
    `LAST_UPDATED_DATE` bigint DEFAULT NULL COMMENT '最近更新时间',
    PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS T_MODEL_INTERFACE_PROTOCOL
(
    ID varchar(16) not null,
    protocol varchar(32) not null,
    en_name varchar(32) not null,
    zh_name varchar(32) not null,
    model_types varchar(128) not null,
    visible varchar(8),
    PRIMARY KEY(ID)
);

-- prompt tables
CREATE TABLE IF NOT EXISTS `t_pe_task`
(
    `id`            varchar(60) NOT NULL COMMENT '唯一标识一个工程任务',
    `name`          varchar(512) NOT NULL COMMENT '任务名称',
    `description`   text NULL COMMENT '任务描述',
    `iteration_num` int NOT NULL DEFAULT 0 COMMENT '候选模板迭代次数',
    `project_id`    varchar(60) NULL DEFAULT NULL COMMENT 'project id',
    `industry_id`   varchar(36) NULL COMMENT '行业id',
    `creator`       varchar(36) NOT NULL COMMENT '创建人',
    `updater`       varchar(36) NULL DEFAULT NULL COMMENT '修改人',
    `created_on`    timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_on`    timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    `workspace_id`  varchar(64) NULL COMMENT '工作空间ID',
    PRIMARY KEY (`id`),
    UNIQUE INDEX `uniq_t_pe_task_name`(`name` ASC, `project_id` ASC),
    INDEX           `idx_creator`(`creator` ASC),
    INDEX           `idx_updater`(`updater` ASC),
    INDEX           `idx_project_id`(`project_id` ASC)
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '工程任务表' ROW_FORMAT = DYNAMIC;

CREATE TABLE IF NOT EXISTS `t_pe_tag`
(
    `id`         varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '主键UUID',
    `name`       varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '名称/值，唯一',
    `name_en`    varchar(128) NOT NULL COMMENT '英文标签名称',
    `created_on` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_on` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `workspace_id` varchar(64) NULL COMMENT '工作空间ID',
    PRIMARY KEY (`id`) USING BTREE,
    UNIQUE INDEX `uniq_t_pe_tag_name`(`name` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = 'prompt标签表' ROW_FORMAT = DYNAMIC;

CREATE TABLE IF NOT EXISTS `t_pe_evaluation_task`
(
    `id`               varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT 'UUID',
    `name`             varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '评估任务名称',
    `method`           varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '选择的评估方法',
    `task_id`          varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '任务工程id',
    `test_set_id`      varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '选择的测试数据集uri',
    `description`      text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '任务描述',
    `created_on`       timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '评估任务创建时间',
    `updated_on`       timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '评估任务更新时间',
    `status`           varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '评估任务状态，共8种状态：等待中、评估中、评估成功、评估失败、重启、部分评估成功、正在中止、已中止',
    `creator`          varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '创建人',
    `prompts`          json NULL COMMENT '模板列表信息，最多九项',
    `regular_expression` VARCHAR(64) NULL COMMENT '评估正则表达式',
    `eval_model_config` TEXT NULL COMMENT '模型评估配置',
    `workspace_id`     varchar(64) NULL COMMENT '工作空间ID',
    PRIMARY KEY (`id`) USING BTREE,
    INDEX              `pe_evaluation_task_id`(`task_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

CREATE TABLE IF NOT EXISTS `t_pe_evaluation_result`
(
    `id`                 varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '评估结果id',
    `evaluation_task_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '评估任务id',
    `prompt_id`          varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '候选模板id',
    `test_num`           int                                                          NOT NULL COMMENT '测试用例行号',
    `generate_result`    text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '结果',
    `eval_result`        json                                                         NOT NULL COMMENT '评估结果',
    `eval_failed_reason` varchar(255) DEFAULT NULL COMMENT '评估失败原因',
    `workspace_id`       varchar(64) NULL COMMENT '工作空间ID',
    PRIMARY KEY (`id`) USING BTREE,
    INDEX                `pe_result_test_id`(`test_num` ASC) USING BTREE,
    INDEX                `pe_result_prompt_id`(`prompt_id` ASC) USING BTREE,
    INDEX                `pe-eval-task-id-fk`(`evaluation_task_id` ASC) USING BTREE,
    UNIQUE               `pe_pid_etid_tn_ux` (`evaluation_task_id`,`prompt_id`,`test_num`) USING BTREE,
    CONSTRAINT `pe-eval-task-id-fk` FOREIGN KEY (`evaluation_task_id`) REFERENCES `t_pe_evaluation_task` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

CREATE TABLE IF NOT EXISTS `t_pe_prompt`
(
    `id`           varchar(36) NOT NULL COMMENT 'UUID',
    `name`         varchar(255) NULL DEFAULT NULL COMMENT '模板名称',
    `model`        varchar(128) NOT NULL COMMENT '模型名称',
    `model_config` json NULL COMMENT '模型参数{"temperature":0.8,"presence_penalty":0}',
    `task_id`      varchar(600) NULL DEFAULT NULL COMMENT '所属工程任务id',
    `source`       varchar(36) NOT NULL COMMENT '来源（模型调优、playground调优、实验调优、无来源）',
    `type`         tinyint(1) NOT NULL COMMENT '0标识历史，1标识候选',
    `question`     varchar(4000) NOT NULL COMMENT 'question',
    `answer`       text NULL COMMENT 'answer',
    `variables`    json NULL COMMENT '模板信息，[{"id":"id","name":"name","value":"value","task_id":"task_id"}]',
    `manual_score` tinyint NULL DEFAULT NULL COMMENT '人工打分',
    `creator`      varchar(36) NOT NULL COMMENT '创建人',
    `updater`      varchar(36) NULL DEFAULT NULL COMMENT '修改人',
    `created_on`   timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_on`   timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `workspace_id` varchar(64) NULL COMMENT '工作空间ID',
    `file_id`      varchar(64) NULL COMMENT '文件ID',
    PRIMARY KEY (`id`)
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '候选模板' ROW_FORMAT = DYNAMIC;

CREATE TABLE IF NOT EXISTS `t_history_prompt` (
    `id`          VARCHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '模板id',
    `name`        VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '模板名称',
    `content`     TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '模板内容',
    `source`      VARCHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '模板来源',
    `variables`   TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '变量',
    `pt_type`     VARCHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '模板类型',
    `project_id`  VARCHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目id',
    `industry_id` VARCHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '行业id',
    `description` VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '描述',
    `creator`     VARCHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '创建人',
    `updater`     VARCHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '修改人',
    `created_on`  TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_on`  TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `workspace_id` VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '工作空间ID',
    `domain_id`   VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '租户id',
    `tag_ids`     VARCHAR(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '标签id列表',
    PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '历史提示词模板表' ROW_FORMAT = DYNAMIC;

CREATE TABLE IF NOT EXISTS `t_pe_prompt_template`
(
    `id`           varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'UUID',
    `question`     varchar(4000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '问题',
    `answer`       text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '答案',
    `model`        varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '模型',
    `model_config` json NULL COMMENT '模型参数',
    `variables`    json NULL COMMENT '模板信息',
    `creator`      varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '创建人',
    `created_on`   timestamp NULL DEFAULT NULL COMMENT '创建时间',
    `workspace_id` varchar(64) NULL COMMENT '工作空间ID',
    PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

CREATE TABLE IF NOT EXISTS `t_pe_variable`
(
    `id`             varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '唯一标识一个变量',
    `key`            varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin         NOT NULL COMMENT '变量key',
    `name`           varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '参数名称',
    `pe_task_id`     varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '工程任务id',
    `relation_count` tinyint                                                       NOT NULL COMMENT '关联的候选模板数',
    `create_time`    bigint                                                        NOT NULL,
    `workspace_id`   varchar(64) NULL COMMENT '工作空间ID',
    PRIMARY KEY (`id`) USING BTREE,
    KEY              `idx_task` (`pe_task_id`) USING BTREE,
    KEY              `UNIQUE_VARIABLE` (`key`,`pe_task_id`) USING BTREE,
    CONSTRAINT `t_pe_variable_fk_task` FOREIGN KEY (`pe_task_id`) REFERENCES `t_pe_task` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT='工程任务变量表';

CREATE TABLE IF NOT EXISTS `t_dataset`
(
    `dataset_id`   varchar(64) NOT NULL COMMENT '数据集主键',
    `dataset_name` varchar(128) NOT NULL COMMENT '数据集名称',
    `dataset_type` varchar(128) NOT NULL COMMENT '数据集类型',
    `project_id`   varchar(64) NOT NULL COMMENT '项目id',
    `obs_path`     varchar(255) NOT NULL COMMENT 'obs桶路径',
    `create_time`  datetime NOT NULL COMMENT '添加时间',
    `update_time`  datetime NOT NULL COMMENT '更新时间',
    `description`  varchar(512) NULL DEFAULT '' COMMENT '描述',
    `workspace_id` varchar(64) NULL COMMENT '工作空间ID',
    PRIMARY KEY (`dataset_id`)
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '数据集管理表' ROW_FORMAT = DYNAMIC;

CREATE TABLE IF NOT EXISTS `t_job_instance`
(
    `id`          varchar(36) NOT NULL,
    `name`        varchar(128) NULL DEFAULT NULL COMMENT '任务名称',
    `created_on`  timestamp   NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `updated_on`  timestamp NULL DEFAULT NULL,
    `job_spec_id` varchar(36) NOT NULL COMMENT '关联的job_spc',
    `context`     mediumtext NOT NULL COMMENT '任务参数，json格式',
    `retry_time`  int NOT NULL COMMENT '重试次数。最开始是0，当这个重试次数到达max时，停止执行。因此最多执行次数，max_retyr_time + 1',
    `status`      varchar(16) NOT NULL COMMENT '任务状态，Pending, Running, Retrying, Failed, Success',
    `started_on`  timestamp NULL DEFAULT NULL COMMENT '启动时间',
    `ended_on`    timestamp NULL DEFAULT NULL COMMENT '任务结束时间',
    `handler_id`  varchar(64) NULL DEFAULT NULL COMMENT '有哪个handler实例实行这个任务',
    `account_id`  varchar(36) NOT NULL,
    `workspace_id` varchar(64) NULL COMMENT '工作空间ID',
    PRIMARY KEY (`id`),
    INDEX `index_name`(`name` ASC)
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '一个任务的实例，同一个job_spec的不同job_instance代表不同的任务实例，参数不一样，在前台展示也是两条数据' ROW_FORMAT = DYNAMIC;

CREATE TABLE IF NOT EXISTS `t_mapping_pe_task_tag`
(
    `task_id`     varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '工程任务id',
    `tag_id`      varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '标签id',
    `workspace_id` varchar(64) NULL COMMENT '工作空间ID',
    INDEX          `idx_tmptt_task`(`task_id` ASC) USING BTREE,
    INDEX          `idx_tmptt_tag`(`tag_id` ASC) USING BTREE,
    CONSTRAINT     `t_mapping_pe_task_tag_fk_tag` FOREIGN KEY (`tag_id`) REFERENCES `t_pe_tag` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT     `t_mapping_pe_task_tag_fk_task` FOREIGN KEY (`task_id`) REFERENCES `t_pe_task` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '标签和任务关联关系表' ROW_FORMAT = DYNAMIC;

CREATE TABLE IF NOT EXISTS `t_job_spec`
(
    `id`         varchar(36) NOT NULL,
    `created_on` timestamp   NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `updated_on` timestamp NULL DEFAULT NULL,
    `name`       varchar(32) NOT NULL COMMENT '任务的名称',
    `type`       varchar(32) NOT NULL COMMENT '任务类型，polling（定时任务），cluster（分发任务）',
    `workspace_id` varchar(64) NULL COMMENT '工作空间ID',
    PRIMARY KEY (`id`)
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '记录任务的描述信息，一条记录对应一种任务类型。这些任务类型是可以枚举的。不同任务类型交给不同类型的Worker处理' ROW_FORMAT = DYNAMIC;

CREATE TABLE IF NOT EXISTS `t_pe_industry`
(
    `id`          varchar(36)  not NULL COMMENT '主键UUID',
    `name`        VARCHAR(128) NOT NULL COMMENT '行业名称',
    `name_en`     varchar(128) NOT NULL COMMENT '英文行业名称',
    `description` TEXT COMMENT '行业描述',
    `library_type` VARCHAR(50) COMMENT '组件类别，提示词，插件，MCP',
    `created_on`  timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_on`  timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `workspace_id` varchar(64) NULL COMMENT '工作空间ID',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT='prompt行业表';

CREATE TABLE IF NOT EXISTS `t_pe_prompt_library`
(
    `id`          varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '模板id',
    `name`        varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '模板名称',
    `content`     TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '模板内容',
    `source`      varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '模板来源',
    `variables`   TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '变量',
    `pt_type`     varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '模板类型',
    `project_id`  varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目id',
    `industry_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '行业id',
    `description` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '描述',
    `creator`     varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '创建人',
    `updater`     varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '修改人',
    `created_on`  timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_on`  timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `workspace_id` varchar(64) NULL COMMENT '工作空间ID',
    `domain_id`   varchar(64) NULL COMMENT '租户id',
    `is_share`    TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已共享（0=否，1=是)',
    PRIMARY KEY (`id`) USING BTREE,
    INDEX          `key_name`(`name` ASC) USING BTREE,
    INDEX          `key_project_id`(`project_id` ASC) USING BTREE,
    CONSTRAINT fk_pe_prompt_library_industry_id FOREIGN KEY (`industry_id`) REFERENCES `t_pe_industry`(`id`)
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '模板表' ROW_FORMAT = DYNAMIC;

CREATE TABLE IF NOT EXISTS `t_mapping_pe_template_tag`
(
    `template_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '模板id',
    `tag_id`      varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '标签id',
    `workspace_id` varchar(64) NULL COMMENT '工作空间ID',
    INDEX          `key_template_id`(`template_id` ASC) USING BTREE,
    INDEX          `key_tag`(`tag_id` ASC) USING BTREE,
    CONSTRAINT     `fk_tag_id` FOREIGN KEY (`tag_id`) REFERENCES `t_pe_tag` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT     `fk_template_id` FOREIGN KEY (`template_id`) REFERENCES `t_pe_prompt_library` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '标签和正式模板关联关系表' ROW_FORMAT = DYNAMIC;

CREATE TABLE IF NOT EXISTS `t_pe_optimization_task` (
    `id`              VARCHAR ( 36 ) NOT NULL COMMENT 'UUID',
    `project_id`      VARCHAR ( 36 ) NOT NULL COMMENT '项目ID',
    `task_id`         VARCHAR ( 36 ) NOT NULL COMMENT '工程id',
    `name`            VARCHAR ( 255 ) NOT NULL COMMENT '优化任务名称',
    `description`     TEXT COMMENT '任务描述',
    `jiuwen_task_id`  VARCHAR ( 128 ) NOT NULL DEFAULT '' COMMENT '九问任务ID',
    `prompts`         json NULL COMMENT '模板列表信息，最多九项',
    `test_set_id`     VARCHAR ( 36 ) NOT NULL COMMENT '用例集ID',
    `model_config`    TEXT COMMENT '优化模型',
    `assistant_config` TEXT COMMENT '评分模型',
    `num_iter`        INT NOT NULL DEFAULT 3 COMMENT '优化的迭代轮数',
    `best_prompt`     TEXT DEFAULT NULL COMMENT '当前时刻优化后的模板',
    `error_msg`       TEXT DEFAULT NULL COMMENT '错误消息',
    `progress_rate`   FLOAT DEFAULT 0 COMMENT '当前时刻优化进度，离散数值',
    `status`          VARCHAR ( 255 ) DEFAULT NULL COMMENT '优化任务状态，共5种状态：等待中、优化中、优化成功、优化失败、已暂停',
    `creator`         VARCHAR ( 36 ) NOT NULL COMMENT '创建人',
    `created_on`      TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP COMMENT '优化任务创建时间',
    `running_on`      TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP COMMENT '任务启动时间',
    `updated_on`      TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '优化创建时间',
    `type`            VARCHAR(16) NOT NULL DEFAULT 'expansion' COMMENT '优化任务类型',
    `workspace_id`    varchar(64) NULL COMMENT '工作空间ID',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uniq_task_id_name` (`task_id`, `name`),
    KEY `ix_task_id` (`task_id`),
    KEY `ix_creator_status` (`creator`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;

CREATE TABLE IF NOT EXISTS `t_pe_op_task` (
    `id`              VARCHAR(64) NOT NULL COMMENT '唯一标识一个提示词优化任务',
    `jiuwen_task_id`  VARCHAR(128) NULL COMMENT '九问优化任务id',
    `name`            VARCHAR(64) NOT NULL COMMENT '提示词优化任务名称',
    `desc`            TEXT NOT NULL COMMENT '提示词优化任务描述',
    `pt_type`         VARCHAR(32) NULL COMMENT '提示词优化任务类型，text文本类型，multi多模态',
    `pt_text`         TEXT NULL COMMENT '优化文本',
    `pt_vars`         TEXT NULL COMMENT '提示词变量',
    `exec_time`       TIMESTAMP NULL COMMENT '提示词优化任务执行时间',
    `pt_model`        VARCHAR(255) NULL COMMENT '优化提示词模型',
    `exec_object`     VARCHAR(255) NULL COMMENT '提示词优化任务执行对象',
    `max_iter_num`    INT NULL COMMENT '提示词优化任务最大迭代次数',
    `target_acc`      VARCHAR(32) NULL COMMENT '提示词优化任务目标精度',
    `show_case_num`   INT NULL COMMENT '终提示词里的示例个数，最多为用例集里的用例个数',
    `target_type`     VARCHAR(32) NULL COMMENT '用例的目标类型，objective客观任务，subjective主观任务',
    `progress_rate`   DOUBLE NULL DEFAULT NULL COMMENT '执行进度',
    `message`         TEXT CHARACTER SET utf8mb4 NULL COMMENT '运行信息',
    `score_standard`  TEXT NULL COMMENT '评分标准',
    `back_knowledge`  TEXT NULL COMMENT '背景知识',
    `status`          TINYINT NULL COMMENT '运行状态，0草稿、1等待执行、2执行中、3执行成功、4执行失败',
    `project_id`      VARCHAR(64) NULL COMMENT '项目id',
    `workspace_id`    VARCHAR(64) NULL COMMENT '空间id',
    `creator`         VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '工具创建者',
    `creator_id`      VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '工具创建者user id',
    `created_time`    TIMESTAMP(0) NULL DEFAULT CURRENT_TIMESTAMP(0) COMMENT '创建时间',
    `updated_time`    TIMESTAMP(0) NULL DEFAULT CURRENT_TIMESTAMP(0) ON UPDATE CURRENT_TIMESTAMP(0) COMMENT '更新时间',
    `prompt_id`       VARCHAR(64) NULL DEFAULT NULL COMMENT '我的提示词模板ID',
    `domain_id`       varchar(64) NULL COMMENT '租户id',
    `algorithm`       varchar(32) NULL COMMENT '优化算法',
    PRIMARY KEY (`id`),
    KEY `idx_t_pe_op_task_domain_id` (`domain_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='提示词优化任务表' ROW_FORMAT=DYNAMIC;

CREATE TABLE IF NOT EXISTS `t_history_op_task` (
    `id`              VARCHAR(64)  NOT NULL COMMENT '唯一标识一个提示词优化任务',
    `jiuwen_task_id`  VARCHAR(128) NULL     COMMENT '九问优化任务id',
    `name`            VARCHAR(64)  NOT NULL COMMENT '提示词优化任务名称',
    `desc`            TEXT         NOT NULL COMMENT '提示词优化任务描述',
    `pt_type`         VARCHAR(32)  NULL     COMMENT '提示词优化任务类型，text文本类型，multi多模态',
    `pt_text`         TEXT         NULL     COMMENT '优化文本',
    `pt_vars`         TEXT         NULL     COMMENT '提示词变量',
    `exec_time`       TIMESTAMP    NULL     COMMENT '提示词优化任务执行时间',
    `pt_model`        VARCHAR(255) NULL     COMMENT '优化提示词模型',
    `exec_object`     VARCHAR(255) NULL     COMMENT '提示词优化任务执行对象',
    `max_iter_num`    INT          NULL     COMMENT '提示词优化任务最大迭代次数',
    `target_acc`      VARCHAR(32)  NULL     COMMENT '提示词优化任务目标精度',
    `show_case_num`   INT          NULL     COMMENT '终提示词里的示例个数，最多为用例集里的用例个数',
    `target_type`     VARCHAR(32)  NULL     COMMENT '用例的目标类型，objective客观任务，subjective主观任务',
    `progress_rate`   DOUBLE       NULL     DEFAULT NULL COMMENT '执行进度',
    `message`         TEXT         NULL     COMMENT '运行信息',
    `score_standard`  TEXT         NULL     COMMENT '评分标准',
    `back_knowledge`  TEXT         NULL     COMMENT '背景知识',
    `status`          TINYINT      NULL     COMMENT '运行状态，0草稿、1等待执行、2执行中、3执行成功、4执行失败',
    `project_id`      VARCHAR(64)  NULL     COMMENT '项目id',
    `workspace_id`    VARCHAR(64)  NULL     COMMENT '空间id',
    `creator`         VARCHAR(64)  NULL     COMMENT '工具创建者',
    `creator_id`      VARCHAR(64)  NULL     COMMENT '工具创建者user id',
    `created_time`    TIMESTAMP    NULL     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_time`    TIMESTAMP    NULL     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `prompt_id`       VARCHAR(64)  NULL     COMMENT '我的提示词模板ID',
    `domain_id`       VARCHAR(64)  NULL     COMMENT '租户id',
    `algorithm`       varchar(32)  NULL     COMMENT '优化算法',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='历史提示词优化任务表' ROW_FORMAT=DYNAMIC;

-- tool tables
CREATE TABLE IF NOT EXISTS `t_mcp` (
    `server_id`     VARCHAR(64) NOT NULL COMMENT 'mcp 服务唯一标识',
    `project_id`    VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '租户唯一标识',
    `server_name`   VARCHAR(64) NOT NULL COMMENT 'mcp 服务名称',
    `server_name_en` VARCHAR(64) NULL COMMENT '服务英文名',
    `server_desc`   VARCHAR(1000) NOT NULL COMMENT 'mcp 服务描述',
    `icon`          MEDIUMTEXT NULL COMMENT 'mcp 服务图标',
    `icon_name`     VARCHAR(64)   NULL COMMENT 'icon图标名称',
    `tools`         TEXT NOT NULL COMMENT 'mcp 服务暴露的工具',
    `visibility`    VARCHAR(32) NOT NULL DEFAULT 'project' COMMENT '可见范围：user,project(默认),workspace,domain,global',
    `url`           VARCHAR(256) NOT NULL COMMENT 'mcp 服务地址',
    `auth`          VARCHAR(4096) NULL COMMENT 'mcp 认证配置',
    `type`          VARCHAR(32) NOT NULL COMMENT 'mcp 服务类型，取值为inner或custom，添加的服务为custom类型',
    `category`      VARCHAR(32) NULL COMMENT '服务类别：public,template',
    `creator`       VARCHAR(64) NOT NULL COMMENT '创建者',
    `creator_id`    VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '创建者 user id',
    `created_on`    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_on`    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`server_id`),
    UNIQUE INDEX `idx_t_mcp_project_id_mcp_server_name_en` (`project_id`, `server_name_en`),
    KEY `idx_t_mcp_server_updated_on` (`updated_on`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = DYNAMIC COMMENT = 'mcp服务';

CREATE TABLE IF NOT EXISTS `t_mcp_config`(
    `id`          VARCHAR(64) NOT NULL COMMENT 'Config唯一标识ID',
    `server_id`   VARCHAR(64) NOT NULL COMMENT 'mcp服务id',
    `project_id`  VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '租户 project id',
    `auth_keys`   VARCHAR(4096) NOT NULL COMMENT 'mcp 认证配置',
    `creator_id`  VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '租户 user id',
    `created_on`  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_on`  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY(`id`),
    UNIQUE INDEX `idx_t_mcp_config_creator_id_project_id_server_id`(`server_id`, `creator_id`, `project_id`),
    KEY `idx_t_mcp_config_updated_on`(`updated_on`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = DYNAMIC COMMENT = 'mcp服务配置';

CREATE TABLE ws_mcp_server_def
(
    id                      varchar(64)       not null primary key,
    server_code             varchar(255)      null COMMENT 'mcp服务编码',
    icon                    longtext          null COMMENT '图标',
    name                    varchar(255)      null COMMENT '名称',
    name_en                 varchar(255)      null COMMENT '英文名称',
    description             varchar(2048)     null COMMENT '藐视',
    description_en          varchar(2048)     null COMMENT '英文描述',
    readme                  longtext          null COMMENT '服务简介',
    server_config           longtext          null COMMENT '服务配置信息',
    tools                   longtext          null COMMENT '工具列表',
    type                    varchar(64)       null COMMENT '类型',
    org_type                varchar(64)       null COMMENT '部署类型  npx uvx sse',
    deleted                 tinyint default 0 null COMMENT '删除标识',
    tenant_id               varchar(64)       not null COMMENT '租户id',
    dept_code               varchar(64)       null comment '部门id',
    created_date            timestamp         not null DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    created_by_user_id      varchar(64)       null COMMENT '创建用户',
    last_updated_date       timestamp         not null DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    last_updated_by_user_id varchar(64)       null COMMENT '更新用户',
    url                     varchar(255)      null COMMENT '服务的url地址',
    install_times           bigint  default 0 null COMMENT '部署次数',
    view_times              bigint  default 0 null COMMENT '访问次数',
    category                VARCHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '行业分类ID，关联 t_pe_industry.id (UUID)',
    CONSTRAINT fk_ws_mcp_category_industry_id FOREIGN KEY (category) REFERENCES t_pe_industry(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

CREATE TABLE ws_mcp_service_def
(
    id                        varchar(64)       not null primary key,
    name                      varchar(255)      null COMMENT '部署的mcp服务名称',
    name_en                   varchar(255)      null COMMENT '部署的mcp服务英文名称',
    description               varchar(2048)     null COMMENT '部署的mcp服务描述',
    description_en            varchar(2048)     null COMMENT '部署的mcp服务英文描述',
    fc_instance_url           varchar(255)      null COMMENT 'mcp服务的访问地址',
    fc_instance_id            varchar(255)       null COMMENT 'functiongraph的实例id',
    fc_instance_status        varchar(64)       null COMMENT 'mcp服务的状态',
    fc_region                 varchar(64)       null COMMENT 'region',
    apig_group_id             varchar(64)       null COMMENT 'apig的分组id',
    apig_instance_id          varchar(255)       null COMMENT 'apig的实例id',
    deleted                   tinyint default 0 null COMMENT '删除标识',
    tenant_id                 varchar(64)       null COMMENT '租户id',
    dept_code                 varchar(64)       null comment '部门id',
    created_date              timestamp         not null DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    created_by_user_id        varchar(64)       null COMMENT '创建租户',
    last_updated_date         timestamp         not null DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    last_updated_by_user_id   varchar(64)       null COMMENT '更新租户',
    readme                    longtext          null COMMENT '服务介绍',
    server_config             longtext          null COMMENT '服务配置',
    tools                     longtext          null COMMENT '工具列表',
    deploy_type               varchar(64)       null COMMENT '部署类型 sse',
    org_type                  varchar(64)       null COMMENT '服务类型 sse npx uvx',
    function_name             varchar(128)      null COMMENT '函数名称',
    server_id                 varchar(64)       null COMMENT '服务id',
    function_urn              varchar(256)      null COMMENT 'functiongraph的urn地址',
    function_application_name varchar(118)      null COMMENT 'functiongraph的应用名称',
    domain_id                 varchar(64)       null comment '域名编号',
    unique_code               varchar(64)       null comment '唯一编码',
    project_id                varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin null COMMENT '项目id',
    workspace_id              varchar(64)       null COMMENT '工作空间id',
    icon                      longtext          null COMMENT '图标',
    node_type                 varchar(64)       NOT NULL DEFAULT 'Mcp' comment '节点类型',
    auth_type                 varchar(64)       null comment '鉴权类型',
    trace_id                  varchar(64)       null COMMENT '溯源ID',
    visibility                ENUM('global','workspace','user') DEFAULT 'workspace' COMMENT '可见范围',
    auth_info                 MEDIUMTEXT NULL COMMENT 'MCP鉴权信息',
    third_resource            varchar(32)       null COMMENT '第三方资源类型: 自有的,ROMA,KooGallery',
    third_id                  varchar(128)      null COMMENT '第三方资源ID',
    third_version_id          varchar(128)      null COMMENT '第三方资源版本ID',
    fail_reason               VARCHAR(500) DEFAULT NULL COMMENT '部署失败具体原因/错误信息',
    is_share                  TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已共享（0=否，1=是)'
);

CREATE TABLE ws_mcp_server_rating
(
    rating_id    int unsigned auto_increment primary key,
    server_id    varchar(32) not null COMMENT '服务id',
    tenant_id    varchar(32) not null COMMENT '租户id',
    score        tinyint     not null COMMENT '评分',
    created_date datetime    not null COMMENT '创建时间',
    updated_date datetime    null COMMENT '更新时间',
    constraint server_id unique (server_id, tenant_id)
) comment 'MCP服务评分表';

CREATE TABLE IF NOT EXISTS `t_tool` (
    `tool_id`           VARCHAR(84)   NOT NULL COMMENT '工具唯一标识',
    `project_id`        VARCHAR(64)   CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '租户唯一标识',
    `tool_display_name` VARCHAR(64)   NOT NULL COMMENT '工具展示名称',
    `tool_chinese_name` VARCHAR(64)   NULL COMMENT '工具展示中文名称',
    `tool_desc`         VARCHAR(600)  NOT NULL COMMENT '工具的描述',
    `icon`              MEDIUMTEXT    NULL COMMENT '工具图标',
    `icon_name`         VARCHAR(64)   NULL COMMENT 'icon图标名称',
    `visibility`        VARCHAR(32)   NOT NULL DEFAULT 'project' COMMENT '可见范围：user,project(默认),workspace,domain,global',
    `request_info`      MEDIUMTEXT    NULL COMMENT '工具请求信息',
    `auth_info`         MEDIUMTEXT    NULL COMMENT '工具鉴权信息',
    `input_schema`      MEDIUMTEXT    NULL COMMENT '工具入参的JsonSchema',
    `output_schema`     MEDIUMTEXT    NULL COMMENT '工具出参的JsonSchema',
    `intf_type`         MEDIUMTEXT    NULL COMMENT '接口类型，取值：blocking，streaming，默认blocking',
    `type`              VARCHAR(32)   NOT NULL COMMENT '工具类型，取值为inner或custom，创建的工具为custom类型',
    `metadata`          VARCHAR(4096) NULL COMMENT '扩展字段',
    `creator`           VARCHAR(64)   NULL COMMENT '工具创建者',
    `creator_id`        VARCHAR(64)   CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL COMMENT '工具创建者user id',
    `created_on`        TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_on`        TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `test_status`       MEDIUMTEXT    NULL COMMENT '工具测试状态，0：失败；1：成功；2：未知',
    `last_version_id`   VARCHAR(64)   NULL COMMENT '插件最新版本号',
    `customize_node`    TINYINT(1)    NULL COMMENT '是否是自定义节点，1表示是自定义节点,0或空表示不是',
    `published`         TINYINT(1)    NULL COMMENT '是否是自定义节点，1表示是自定义节点,0或空表示不是',
    `call_mode`         VARCHAR(16)   DEFAULT 'api' COMMENT '插件执行类型。api：api类型的插件；functiongraph：函数类型的插件；如果为空，则默认是api;',
    `domain_id`         varchar(64)   NULL COMMENT '租户id',
    `is_input_list`     MEDIUMTEXT    NULL COMMENT '流式封装',
    `is_output_list`    MEDIUMTEXT    NULL COMMENT '流式封装',
    `auth_required`     TINYINT(1)    NULL DEFAULT 0 COMMENT '插件是否需要鉴权',
    `workspace_id`      varchar(64)   NULL COMMENT '工作空间ID',
    `trace_id`          varchar(64)   NULL COMMENT '溯源ID',
    `is_free`           tinyint(1)    DEFAULT 0 COMMENT '是否是免费插件，0:未知，1:免费，2:付费',
    `label`             VARCHAR(32)   NULL DEFAULT 'normal' COMMENT '插件类型，用于区分是否用在deepsearch',
    `is_share`          TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '是否已共享（0=否，1=是)',
    `category`          VARCHAR(36)   CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '分类',
    PRIMARY KEY (`tool_id`),
    KEY `idx_t_tool_updated_on` (`updated_on`),
    CONSTRAINT fk_t_tool_category_industry_id FOREIGN KEY (category) REFERENCES t_pe_industry(id) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = DYNAMIC COMMENT ='工具';

CREATE TABLE IF NOT EXISTS `t_history_tool` (
    `history_id`        VARCHAR(64)   NOT NULL DEFAULT '' COMMENT '历史表主键 id',
    `tool_id`           VARCHAR(64)   NOT NULL COMMENT '工具唯一标识',
    `project_id`        VARCHAR(64)   NOT NULL COMMENT '租户唯一标识',
    `tool_display_name` VARCHAR(64)   NOT NULL COMMENT '工具展示名称',
    `tool_chinese_name` VARCHAR(64)   NULL COMMENT '工具展示中文名称',
    `tool_desc`         VARCHAR(600)  NOT NULL COMMENT '工具的描述',
    `icon`              MEDIUMTEXT    NULL COMMENT '工具图标',
    `icon_name`         VARCHAR(64)   NULL COMMENT 'icon图标名称',
    `visibility`        VARCHAR(32)   NOT NULL DEFAULT 'project' COMMENT '可见范围：user,project(默认),workspace,domain,global',
    `request_info`      MEDIUMTEXT    NULL COMMENT '工具请求信息',
    `auth_info`         MEDIUMTEXT    NULL COMMENT '工具鉴权信息',
    `input_schema`      MEDIUMTEXT    NULL COMMENT '工具入参的JsonSchema',
    `output_schema`     MEDIUMTEXT    NULL COMMENT '工具出参的JsonSchema',
    `intf_type`         MEDIUMTEXT    NULL COMMENT '接口类型，取值：blocking，streaming，默认blocking',
    `type`              VARCHAR(32)   NOT NULL COMMENT '工具类型，取值为inner或custom，创建的工具为custom类型',
    `metadata`          VARCHAR(4096) NULL COMMENT '扩展字段',
    `creator`           VARCHAR(64)   NULL COMMENT '工具创建者',
    `creator_id`        VARCHAR(64)   NULL COMMENT '工具创建者user id',
    `created_on`        TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_on`        TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `test_status`       MEDIUMTEXT    NULL COMMENT '工具测试状态，0：失败；1：成功；2：未知',
    `last_version_id`   VARCHAR(64)   NULL COMMENT '插件最新版本号',
    `customize_node`    TINYINT(1)    NULL DEFAULT NULL COMMENT '是否是自定义节点，1表示是自定义节点,0或空表示不是',
    `is_input_list`     MEDIUMTEXT    NULL COMMENT '流式封装',
    `is_output_list`    MEDIUMTEXT    NULL COMMENT '流式封装',
    `auth_required`     TINYINT(1)    NULL DEFAULT 0 COMMENT '插件是否需要鉴权',
    `workspace_id`      VARCHAR(64)   NULL COMMENT '工作空间ID',
    `trace_id`          VARCHAR(64)   NULL COMMENT '溯源ID',
    `published`         TINYINT(1)    NULL COMMENT '是否是自定义节点，1表示是自定义节点,0或空表示不是',
    `call_mode`         VARCHAR(16)   NULL DEFAULT 'api' COMMENT '调用模式',
    `is_free`           TINYINT(1)    NULL DEFAULT 0 COMMENT '是否是免费插件，0:未知，1:免费，2:付费',
    `domain_id`         VARCHAR(64)   NULL COMMENT '租户id',
    `label`             VARCHAR(32)   NULL DEFAULT 'normal' COMMENT '插件类型，用于区分是否用在deepsearch',
    `is_share`          TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '是否已共享（0=否，1=是）',
    `category`          VARCHAR(36)   CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '分类',
    PRIMARY KEY (`history_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = DYNAMIC COMMENT = '历史工具表';

CREATE TABLE IF NOT EXISTS `t_mapping_agent_tool`
(
    `agent_id`     VARCHAR(64) NOT NULL COMMENT 'agent id',
    `tool_id`      VARCHAR(64) NOT NULL COMMENT 'tool_id',
    `project_id`   VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT 'project_id',
    `resident`     TINYINT(1)  NOT NULL DEFAULT '0' COMMENT '是否为常驻工具',
    `created_on`   TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_on`   TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`agent_id`, `tool_id`, `project_id`),
    KEY `idx_t_mapping_agent_tool_assistant_id` (`agent_id`),
    KEY `idx_t_mapping_agent_tool_project_id` (`project_id`),
    KEY `idx_t_mapping_agent_tool_tool_id` (`tool_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = DYNAMIC COMMENT ='agent和tool的多对多关系映射表';

CREATE TABLE IF NOT EXISTS `t_mapping_tool_function`
(
    `id`          varchar(36)  NOT NULL,
    `function_id` varchar(64)  NOT NULL COMMENT '函数id',
    `plugin_id`   varchar(64)  NOT NULL COMMENT '插件id',
    `tool_id`     varchar(64)  NOT NULL COMMENT '工具id',
    `created_on`  timestamp    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `creator_id`  varchar(64)  DEFAULT NULL,
    `updated_on`  timestamp    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `updater_id`  varchar(64)  DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY  `idx_t_mapping_tool_function_updated_on` (`updated_on`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT='tool和function多对多关系映射表';

CREATE TABLE IF NOT EXISTS `t_task` (
                                        `id`                VARCHAR(64)     NOT NULL COMMENT '任务 id， 主键',
    `name`              VARCHAR(64)     NOT NULL COMMENT '任务名称，可修改',
    `conversation_id`   VARCHAR(64)     NULL COMMENT '会话ID',
    `user_id`           VARCHAR(64)     NULL COMMENT 'user id',
    `project_id`        VARCHAR(64)     NULL COMMENT 'project id',
    `domain_id`         VARCHAR(64)     NULL COMMENT 'domain id',
    `workspace_id`      VARCHAR(64)     NULL COMMENT 'workspace id',
    `type`              VARCHAR(32)     NULL COMMENT '任务类型',
    `mode`              VARCHAR(32)     NULL COMMENT '任务模式，当前仅支持ASYNC',
    `app_id`            VARCHAR(64)     NULL COMMENT '对应工作流或agent id',
    `app_version`       VARCHAR(128)    NULL COMMENT '任务应用版本',
    `is_published`      TINYINT(1)      NULL COMMENT '此工作流是否是发布后',
    `status`            VARCHAR(32)     NULL COMMENT '任务状态',
    `inputs`            MEDIUMTEXT      NULL COMMENT '任务输入',
    `outputs`           MEDIUMTEXT      NULL COMMENT '任务输出',
    `timeout`           INTEGER         NULL COMMENT '工作流超时时间',
    `message`           VARCHAR(2048)   NULL COMMENT '提示消息',
    `create_time`       TIMESTAMP       NOT NULL COMMENT '创建时间',
    `start_time`        TIMESTAMP       NULL COMMENT '任务实际开始时间',
    `update_time`       TIMESTAMP       NULL COMMENT '任务更新日期',
    `finish_time`       TIMESTAMP       NULL COMMENT '任务结束日期',
    PRIMARY KEY (`id`),
    INDEX `idx_create_time`(`create_time` ASC) USING BTREE,
    INDEX `idx_status_time`(`status` ASC, `create_time` ASC) USING BTREE,
    INDEX `idx_finish_time`(`finish_time` ASC) USING BTREE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC COMMENT='任务记录表';

