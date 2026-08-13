CREATE TABLE t_kb_connection_router
(
    id                           varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'id',
    tenant_type                  varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '租户类型',
    domain_id                    varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '租户id',
    knowledge_base_connection_id varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '知识库连接id',
    PRIMARY KEY (id) USING BTREE
) ENGINE = InnoDB
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_general_ci COMMENT = '知识库连接路由表'
  ROW_FORMAT = Dynamic;

CREATE TABLE t_knowledge_base
(
    id                           varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '知识库ID',
    name                         varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL     DEFAULT NULL COMMENT '知识库名称',
    type                         varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '知识库类型，internal-默认，external-第三方',
    repo_type                    varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NULL     DEFAULT NULL COMMENT '知识库存储类型，exclusive独享，share共享',
    share_scope                  varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NULL     DEFAULT NULL COMMENT '存储共享范围',
    status                       varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL DEFAULT 'OPEN' COMMENT '启用，停用',
    icon                         mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci    NULL COMMENT '图标',
    description                  varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL     DEFAULT NULL COMMENT '知识库描述',
    knowledge_base_connection_id varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NULL     DEFAULT NULL COMMENT '来源第三方知识库连接ID',
    external_id                  varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NULL     DEFAULT NULL COMMENT '第三方知识库的外部ID',
    create_time                  bigint                                                         NOT NULL COMMENT '记录创建时间',
    update_time                  bigint                                                         NOT NULL COMMENT '记录最后更新时间',
    project_id                   varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '项目id',
    domain_id                    varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '创建租户（租户id）',
    domain_name                  varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '创建租户（租户名）',
    created_user_id              varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '创建人（用户ID）',
    created_user_name            varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '创建人（用户名）',
    last_update_user_id          varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '更新人（用户id）',
    last_update_user_name        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '更新人（用户名）',
    workspace_id                 varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NULL     DEFAULT NULL COMMENT '工作空间id',
    copy_source_id               varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NULL     DEFAULT NULL COMMENT '复制来源的知识库ID，知识库是从其他空间复制而来时有效',
    PRIMARY KEY (id) USING BTREE,
    INDEX idx_domain_type (domain_id ASC, type ASC) USING BTREE,
    INDEX idx_kb_connection_id (knowledge_base_connection_id ASC) USING BTREE
) ENGINE = InnoDB
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_general_ci COMMENT = '存储知识库信息'
  ROW_FORMAT = Dynamic;

CREATE TABLE t_knowledge_base_config
(
    id          varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '主键',
    config_type varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '配置类型',
    config_item varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '需要配置的具体条目',
    value       mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '值',
    description varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '描述',
    domain_id   varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '租户id',
    PRIMARY KEY (id, domain_id) USING BTREE,
    UNIQUE INDEX t_knowledge_base_config_unique (config_type ASC, config_item ASC, domain_id ASC) USING BTREE
) ENGINE = InnoDB
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_general_ci COMMENT = '知识库系统配置表'
  ROW_FORMAT = Dynamic;


CREATE TABLE t_knowledge_base_connection
(
    id                      varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '第三方知识库连接id',
    connector_id            varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '使用的连接器id',
    name                    varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '连接名称',
    description             varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '描述',
    icon                    mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci    NOT NULL COMMENT '连接器图标',
    used_abilities          mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci    NULL COMMENT '开启能力集合, 使用JSON结构存储',
    params                  mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci    NULL COMMENT '连接信息参数',
    knowledge_base_used     int                                                            NULL DEFAULT NULL COMMENT '知识库连接实例下已经使用的容量',
    knowledge_base_capacity int                                                            NULL DEFAULT NULL COMMENT '知识库连接实例总容量',
    krb5_file               text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci          NULL COMMENT 'Kerberos二进制密钥文件',
    keytab_file             text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci          NULL COMMENT 'Kerberos配置文件',
    status                  varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NULL DEFAULT NULL COMMENT '状态，OPEN-启用，CLOSE-停用',
    domain_id               varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '租户id',
    domain_name             varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '租户名',
    create_user_id          varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '创建人ID',
    create_user_name        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '创建人名称',
    create_time             bigint                                                         NOT NULL COMMENT '创建日期',
    update_user_id          varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '更新人ID',
    update_user_name        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '更新人名称',
    update_time             bigint                                                         NOT NULL COMMENT '更新日期',
    project_id              varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '项目ID',
    workspace_id            varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '所属的空间ID',
    PRIMARY KEY (id) USING BTREE
) ENGINE = InnoDB
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_general_ci COMMENT = '第三方知识库连接信息表'
  ROW_FORMAT = Dynamic;


CREATE TABLE t_knowledge_base_connector
(
    id               varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '连接器ID',
    name             varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '连接器名称',
    icon             mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci    NOT NULL COMMENT '连接器图标',
    description      varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '连接器描述',
    deploy_mode      varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NULL DEFAULT NULL COMMENT '适用的部署场景，比如HC、HCS等，适用多个场景时使用,分割',
    type             varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NULL DEFAULT NULL COMMENT '知识源接入类型',
    param_definition mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci    NULL COMMENT '参数定义,JSON结构',
    help_text        mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci    NULL COMMENT '帮助说明',
    domain_id        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '租户id',
    domain_name      varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '租户名',
    create_user_id   varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '创建人ID',
    create_user_name varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '创建人名称',
    create_time      bigint                                                         NOT NULL COMMENT '创建日期',
    update_user_id   varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '更新人ID',
    update_user_name varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '更新人名称',
    update_time      bigint                                                         NOT NULL COMMENT '更新日期',
    project_id       varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '项目ID',
    workspace_id     varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NULL DEFAULT NULL COMMENT '工作空间id',
    PRIMARY KEY (id) USING BTREE
) ENGINE = InnoDB
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_general_ci COMMENT = '第三方知识库连接器表'
  ROW_FORMAT = Dynamic;


CREATE TABLE t_knowledge_base_connector_ability
(
    id           varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '连接器能力ID',
    code         varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '连接器能力编码',
    name         varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '连接器能力名称',
    description  varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '连接器能力描述',
    connector_id varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '归属的连接器ID',
    sub_ability  mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci    NULL COMMENT '子能力信息，使用JSON结构存储',
    PRIMARY KEY (id) USING BTREE
) ENGINE = InnoDB
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_general_ci COMMENT = '第三方知识库连接器能力表'
  ROW_FORMAT = Dynamic;



CREATE TABLE t_knowledge_base_obs_config
(
    id                  varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '配置ID',
    knowledge_base_id   varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NULL DEFAULT NULL COMMENT '知识库ID',
    obs_bucket_name     varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'obs桶名',
    obs_input_directory varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'obs路径',
    task_status         varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NULL DEFAULT NULL COMMENT '任务状态',
    domain_id           varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '租户id',
    domain_name         varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '租户名',
    created_user_id     varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '创建人ID',
    created_user_name   varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '创建人名称',
    create_time         bigint                                                        NOT NULL COMMENT '创建日期',
    update_user_id      varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '更新人ID',
    update_user_name    varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '更新人名称',
    update_time         bigint                                                        NOT NULL COMMENT '更新日期',
    project_id          varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '项目ID',
    workspace_id        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '所属的空间ID',
    PRIMARY KEY (id) USING BTREE,
    UNIQUE INDEX knowledge_obs_config_idx (knowledge_base_id ASC) USING BTREE
) ENGINE = InnoDB
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_general_ci COMMENT = '知识库OBS配置表'
  ROW_FORMAT = Dynamic;

CREATE TABLE t_knowledge_base_obs_execute_record
(
    id                varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '调度记录id',
    obs_config_id     varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '知识库ID',
    start_time        bigint                                                       NULL DEFAULT NULL COMMENT '调度开始时间',
    end_time          bigint                                                       NULL DEFAULT NULL COMMENT '调度结束时间',
    status            varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '状态',
    log_detail        longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci    NULL COMMENT '日志信息',
    domain_id         varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '租户id',
    domain_name       varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '租户名',
    created_user_id   varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '创建人ID',
    created_user_name varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '创建人名称',
    create_time       bigint                                                       NOT NULL COMMENT '创建日期',
    update_user_id    varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '更新人ID',
    update_user_name  varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '更新人名称',
    update_time       bigint                                                       NOT NULL COMMENT '更新日期',
    project_id        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '项目ID',
    workspace_id      varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '所属的空间ID',
    PRIMARY KEY (id) USING BTREE,
    INDEX obs_config_execute_idx (obs_config_id ASC) USING BTREE
) ENGINE = InnoDB
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_general_ci COMMENT = 'obs执行记录表'
  ROW_FORMAT = Dynamic;

CREATE TABLE t_knowledge_clean_task_info
(
    task_id     varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '任务ID',
    domain_id   varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'DOMAINID',
    status      varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT 'PROCESSING' COMMENT '任务状态',
    create_time bigint                                                       NOT NULL COMMENT '创建时间',
    finish_time bigint                                                       NULL DEFAULT NULL COMMENT '任务完成时间',
    PRIMARY KEY (task_id) USING BTREE,
    INDEX idx_domain_id (domain_id ASC) USING BTREE
) ENGINE = InnoDB
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_general_ci COMMENT = '清理租户任务信息表'
  ROW_FORMAT = Dynamic;

CREATE TABLE t_knowledge_i18n_resource
(
    id       bigint                                                        NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    i18n_key varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '国际化Key',
    locale   varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '语言区域 (如 zh-cn, en-us)',
    message  text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci         NOT NULL COMMENT '翻译后的展示文案',
    PRIMARY KEY (id) USING BTREE,
    UNIQUE INDEX uk_key_locale (i18n_key ASC, locale ASC) USING BTREE
) ENGINE = InnoDB
  AUTO_INCREMENT = 81
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_general_ci COMMENT = '知识库国际化资源表'
  ROW_FORMAT = Dynamic;


CREATE TABLE t_knowledge_repo
(
    knowledge_repo_id varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '知识库id',
    project_id        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '租户唯一标识',
    display_name      varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '知识库名称',
    `desc`              varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '知识库描述',
    type              varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '知识库类型，internal：OP账号下的知识库，external：用户账号下的知识库',
    icon              mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci    NULL COMMENT '知识库图标',
    icon_name         varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NULL     DEFAULT NULL COMMENT 'icon图标名称',
    size              bigint                                                         NOT NULL COMMENT '知识库中所有文件的总大小（Byte）',
    file_num          int                                                            NOT NULL COMMENT '知识库中所有文件数量',
    domain_id         varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NULL     DEFAULT NULL COMMENT '创建租户（租户id）',
    domain_name       varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NULL     DEFAULT NULL COMMENT '创建租户（租户名）',
    creator           varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NULL     DEFAULT NULL COMMENT '知识库创建者',
    creator_id        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NULL     DEFAULT NULL COMMENT '知识库创建者user id',
    metadata          varchar(4096) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL     DEFAULT NULL COMMENT '扩展字段',
    created_on        timestamp                                                      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_on        timestamp                                                      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    source            varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '知识库来源，支持KooSearch、LakeSearch',
    status            varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL DEFAULT 'OPEN' COMMENT '知识库启停状态，OPEN、CLOSE',
    PRIMARY KEY (knowledge_repo_id) USING BTREE,
    INDEX idx_t_knowledge_repo_updated_on (updated_on ASC) USING BTREE
) ENGINE = InnoDB
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_general_ci COMMENT = '知识库'
  ROW_FORMAT = Dynamic;

CREATE TABLE t_knowledge_segment_rule
(
    id                           varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '规则id',
    project_id                   varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NOT NULL COMMENT '租户唯一标识',
    domain_id                    varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NULL     DEFAULT NULL COMMENT '创建租户（租户id）',
    domain_name                  varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NULL     DEFAULT NULL COMMENT '创建租户（租户名）',
    rule                         mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '用户定义规则',
    creator                      varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NULL     DEFAULT NULL COMMENT '规则创建者',
    creator_id                   varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NULL     DEFAULT NULL COMMENT '规则创建者user id',
    created_on                   timestamp                                                     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_on                   timestamp                                                     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    workspace_id                 varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci  NULL     DEFAULT NULL COMMENT '工作空间id',
    knowledge_base_connection_id varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL     DEFAULT NULL COMMENT '知识源连接id',
    PRIMARY KEY (id) USING BTREE,
    INDEX idx_t_knowledge_segment_rule_updated_on (updated_on ASC) USING BTREE
) ENGINE = InnoDB
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_general_ci COMMENT = '知识层级分段规则'
  ROW_FORMAT = Dynamic;

CREATE TABLE t_knowledge_share_scope
(
    id                varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'id',
    knowledge_base_id varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '被共享的知识库id',
    workspace_id      varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '被授权的空间id',
    project_id        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目id',
    created_user_id   varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '创建人id',
    created_user_name varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '创建人名称',
    create_time       bigint                                                       NULL DEFAULT NULL COMMENT '创建时间',
    PRIMARY KEY (id) USING BTREE
) ENGINE = InnoDB
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_general_ci COMMENT = '知识库共享范围'
  ROW_FORMAT = Dynamic;

CREATE TABLE t_knowledge_test_record
(
    record_id         varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '测试记录id',
    knowledge_repo_id varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '知识库id',
    project_id        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NOT NULL COMMENT '租户项目id',
    domain_id         varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NULL     DEFAULT NULL COMMENT '创建租户（租户id）',
    domain_name       varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci   NULL     DEFAULT NULL COMMENT '创建租户（租户名）',
    query             varchar(4096) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '测试的输入',
    created_on        timestamp                                                      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (record_id) USING BTREE,
    INDEX idx_t_knowledge_test_record_created_on (created_on ASC) USING BTREE
) ENGINE = InnoDB
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_general_ci COMMENT = '知识库命中测试记录表'
  ROW_FORMAT = Dynamic;

ALTER TABLE t_knowledge_base
    ADD COLUMN embedding_model_service_id varchar(64) NULL DEFAULT NULL COMMENT 'Embedding模型服务ID',
    ADD COLUMN rerank_model_service_id varchar(80) NULL DEFAULT NULL COMMENT 'Rerank模型服务ID';
