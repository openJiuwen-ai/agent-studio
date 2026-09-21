CREATE TABLE t_kb_connection_router
(
    id                           varchar(100) NOT NULL,
    tenant_type                  varchar(100) NOT NULL,
    domain_id                    varchar(100) NOT NULL,
    knowledge_base_connection_id varchar(100) NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE t_knowledge_base
(
    id                           varchar(64)   NOT NULL,
    name                         varchar(1000) NULL     DEFAULT NULL,
    type                         varchar(50)   NOT NULL,
    repo_type                    varchar(255)  NULL     DEFAULT NULL,
    share_scope                  varchar(64)   NULL     DEFAULT NULL,
    status                       varchar(10)   NOT NULL DEFAULT 'OPEN',
    icon                         TEXT    NULL,
    description                  varchar(1000) NULL     DEFAULT NULL,
    knowledge_base_connection_id varchar(100)  NULL     DEFAULT NULL,
    external_id                  varchar(100)  NULL     DEFAULT NULL,
    create_time                  bigint                                                         NOT NULL,
    update_time                  bigint                                                         NOT NULL,
    project_id                   varchar(64)   NOT NULL,
    domain_id                    varchar(64)   NOT NULL,
    domain_name                  varchar(64)   NOT NULL,
    created_user_id              varchar(64)   NOT NULL,
    created_user_name            varchar(64)   NOT NULL,
    last_update_user_id          varchar(64)   NOT NULL,
    last_update_user_name        varchar(64)   NOT NULL,
    workspace_id                 varchar(64)   NULL     DEFAULT NULL,
    copy_source_id               varchar(100)  NULL     DEFAULT NULL,
    embedding_model_service_id   varchar(64)   NULL     DEFAULT NULL,
    rerank_model_service_id       varchar(80)   NULL     DEFAULT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE t_knowledge_base_config
(
    id          varchar(64)  NOT NULL,
    config_type varchar(64)  NOT NULL,
    config_item varchar(64)  NOT NULL,
    value       TEXT   NOT NULL,
    description varchar(255) NOT NULL,
    domain_id   varchar(64)  NOT NULL,
    PRIMARY KEY (id, domain_id)
);

CREATE TABLE t_knowledge_base_connection
(
    id                      varchar(64)   NOT NULL,
    connector_id            varchar(64)   NOT NULL,
    name                    varchar(64)   NOT NULL,
    description             varchar(1000) NULL DEFAULT NULL,
    icon                    TEXT    NOT NULL,
    used_abilities          TEXT    NULL,
    params                  TEXT    NULL,
    knowledge_base_used     int                                                            NULL DEFAULT NULL,
    knowledge_base_capacity int                                                            NULL DEFAULT NULL,
    krb5_file               text          NULL,
    keytab_file             text          NULL,
    status                  varchar(20)   NULL DEFAULT NULL,
    domain_id               varchar(64)   NOT NULL,
    domain_name             varchar(64)   NOT NULL,
    create_user_id          varchar(64)   NOT NULL,
    create_user_name        varchar(64)   NOT NULL,
    create_time             bigint                                                         NOT NULL,
    update_user_id          varchar(64)   NOT NULL,
    update_user_name        varchar(64)   NOT NULL,
    update_time             bigint                                                         NOT NULL,
    project_id              varchar(64)   NOT NULL,
    workspace_id            varchar(64)   NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE t_knowledge_base_connector
(
    id               varchar(64)   NOT NULL,
    name             varchar(100)  NOT NULL,
    icon             TEXT    NOT NULL,
    description      varchar(1000) NULL DEFAULT NULL,
    deploy_mode      varchar(64)   NULL DEFAULT NULL,
    type             varchar(64)   NULL DEFAULT NULL,
    param_definition TEXT    NULL,
    help_text        TEXT    NULL,
    domain_id        varchar(64)   NOT NULL,
    domain_name      varchar(64)   NOT NULL,
    create_user_id   varchar(64)   NOT NULL,
    create_user_name varchar(64)   NOT NULL,
    create_time      bigint                                                         NOT NULL,
    update_user_id   varchar(64)   NOT NULL,
    update_user_name varchar(64)   NOT NULL,
    update_time      bigint                                                         NOT NULL,
    project_id       varchar(64)   NOT NULL,
    workspace_id     varchar(64)   NULL DEFAULT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE t_knowledge_base_connector_ability
(
    id           varchar(50)   NOT NULL,
    code         varchar(50)   NOT NULL,
    name         varchar(100)  NOT NULL,
    description  varchar(1000) NULL DEFAULT NULL,
    connector_id varchar(20)   NOT NULL,
    sub_ability  TEXT    NULL,
    PRIMARY KEY (id)
);

CREATE TABLE t_knowledge_base_obs_config
(
    id                  varchar(64)  NOT NULL,
    knowledge_base_id   varchar(64)  NULL DEFAULT NULL,
    obs_bucket_name     varchar(255) NULL DEFAULT NULL,
    obs_input_directory varchar(255) NULL DEFAULT NULL,
    task_status         varchar(36)  NULL DEFAULT NULL,
    domain_id           varchar(64)  NOT NULL,
    domain_name         varchar(64)  NOT NULL,
    created_user_id     varchar(64)  NOT NULL,
    created_user_name   varchar(64)  NOT NULL,
    create_time         bigint                                                        NOT NULL,
    update_user_id      varchar(64)  NOT NULL,
    update_user_name    varchar(64)  NOT NULL,
    update_time         bigint                                                        NOT NULL,
    project_id          varchar(64)  NOT NULL,
    workspace_id        varchar(64)  NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE t_knowledge_base_obs_execute_record
(
    id                varchar(64) NOT NULL,
    obs_config_id     varchar(64) NULL DEFAULT NULL,
    start_time        bigint                                                       NULL DEFAULT NULL,
    end_time          bigint                                                       NULL DEFAULT NULL,
    status            varchar(36) NULL DEFAULT NULL,
    log_detail        TEXT    NULL,
    domain_id         varchar(64) NOT NULL,
    domain_name       varchar(64) NOT NULL,
    created_user_id   varchar(64) NOT NULL,
    created_user_name varchar(64) NOT NULL,
    create_time       bigint                                                       NOT NULL,
    update_user_id    varchar(64) NOT NULL,
    update_user_name  varchar(64) NOT NULL,
    update_time       bigint                                                       NOT NULL,
    project_id        varchar(64) NOT NULL,
    workspace_id      varchar(64) NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE t_knowledge_clean_task_info
(
    task_id     varchar(64) NOT NULL,
    domain_id   varchar(64) NOT NULL,
    status      varchar(10) NULL DEFAULT 'PROCESSING',
    create_time bigint                                                       NOT NULL,
    finish_time bigint                                                       NULL DEFAULT NULL,
    PRIMARY KEY (task_id)
);

CREATE TABLE t_knowledge_i18n_resource
(
    id       bigint                                                        NOT NULL,
    i18n_key varchar(255) NOT NULL,
    locale   varchar(50)  NOT NULL,
    message  text         NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE t_knowledge_repo
(
    knowledge_repo_id varchar(64)   NOT NULL,
    project_id        varchar(64)   NOT NULL,
    display_name      varchar(64)   NOT NULL,
    "desc"            varchar(128)  NOT NULL,
    type             varchar(32)   NOT NULL,
    icon              TEXT    NULL,
    icon_name         varchar(64)   NULL     DEFAULT NULL,
    size              bigint                                                         NOT NULL,
    file_num          int                                                            NOT NULL,
    domain_id         varchar(64)   NULL     DEFAULT NULL,
    domain_name       varchar(64)   NULL     DEFAULT NULL,
    creator           varchar(64)   NULL     DEFAULT NULL,
    creator_id        varchar(64)   NULL     DEFAULT NULL,
    metadata          varchar(4096) NULL     DEFAULT NULL,
    created_on        timestamp                                                      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on        timestamp                                                      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source            varchar(64)   NOT NULL,
    status            varchar(16)   NOT NULL DEFAULT 'OPEN',
    PRIMARY KEY (knowledge_repo_id)
);

CREATE TABLE t_knowledge_segment_rule
(
    id                           varchar(64)  NOT NULL,
    project_id                   varchar(64)  NOT NULL,
    domain_id                    varchar(64)  NULL     DEFAULT NULL,
    domain_name                  varchar(64)  NULL     DEFAULT NULL,
    rule                         TEXT   NOT NULL,
    creator                      varchar(64)  NULL     DEFAULT NULL,
    creator_id                   varchar(64)  NULL     DEFAULT NULL,
    created_on                   timestamp                                                     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on                   timestamp                                                     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    workspace_id                 varchar(64)  NULL     DEFAULT NULL,
    knowledge_base_connection_id varchar(200) NULL     DEFAULT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE t_knowledge_share_scope
(
    id                varchar(64) NOT NULL,
    knowledge_base_id varchar(64) NULL DEFAULT NULL,
    workspace_id      varchar(64) NULL DEFAULT NULL,
    project_id        varchar(64) NULL DEFAULT NULL,
    created_user_id   varchar(64) NULL DEFAULT NULL,
    created_user_name varchar(64) NULL DEFAULT NULL,
    create_time       bigint                                                       NULL DEFAULT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE t_knowledge_test_record
(
    record_id         varchar(64)   NOT NULL,
    knowledge_repo_id varchar(64)   NOT NULL,
    project_id        varchar(64)   NOT NULL,
    domain_id         varchar(64)   NULL     DEFAULT NULL,
    domain_name       varchar(64)   NULL     DEFAULT NULL,
    query             varchar(4096) NOT NULL,
    created_on        timestamp                                                      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (record_id)
);

CREATE TABLE IF NOT EXISTS t_knowledge_file
(
    file_id     varchar(64)   NOT NULL,
    kb_id       varchar(64)   NOT NULL,
    project_id  varchar(64)   NOT NULL,
    file_name   varchar(128)  NOT NULL,
    file_type   varchar(16)   NULL DEFAULT NULL,
    file_size   bigint        NOT NULL DEFAULT 0,
    file_status varchar(16)   NOT NULL DEFAULT 'RUNNING',
    file_tags   varchar(1024) NULL DEFAULT NULL,
    doc_ids     varchar(2048) NULL DEFAULT NULL,
    obs_path    varchar(512)  NULL DEFAULT NULL,
    create_time bigint        NOT NULL DEFAULT 0,
    update_time bigint        NOT NULL DEFAULT 0,
    PRIMARY KEY (file_id)
);

CREATE INDEX IF NOT EXISTS idx_kb_id ON t_knowledge_file (kb_id);
CREATE INDEX IF NOT EXISTS idx_project_kb ON t_knowledge_file (project_id, kb_id);

CREATE INDEX IF NOT EXISTS idx_domain_type ON t_knowledge_base (domain_id, type);
CREATE INDEX IF NOT EXISTS idx_kb_connection_id ON t_knowledge_base (knowledge_base_connection_id);
CREATE UNIQUE INDEX IF NOT EXISTS t_knowledge_base_config_unique ON t_knowledge_base_config (config_type, config_item, domain_id);
CREATE UNIQUE INDEX IF NOT EXISTS knowledge_obs_config_idx ON t_knowledge_base_obs_config (knowledge_base_id);
CREATE INDEX IF NOT EXISTS obs_config_execute_idx ON t_knowledge_base_obs_execute_record (obs_config_id);
CREATE INDEX IF NOT EXISTS idx_domain_id ON t_knowledge_clean_task_info (domain_id);
CREATE UNIQUE INDEX IF NOT EXISTS uk_key_locale ON t_knowledge_i18n_resource (i18n_key, locale);
CREATE INDEX IF NOT EXISTS idx_t_knowledge_repo_updated_on ON t_knowledge_repo (updated_on);
CREATE INDEX IF NOT EXISTS idx_t_knowledge_segment_rule_updated_on ON t_knowledge_segment_rule (updated_on);
CREATE INDEX IF NOT EXISTS idx_t_knowledge_test_record_created_on ON t_knowledge_test_record (created_on);
