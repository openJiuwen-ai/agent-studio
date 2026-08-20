CREATE TABLE IF NOT EXISTS t_agent_space_login_log
(
    id           varchar(128) NOT NULL,
    login_domain varchar(255),
    user_id      varchar(32),
    oper_ip      varchar(48)  NOT NULL,
    oper_type    varchar(32)  NOT NULL,
    session_id   varchar(128),
    service_ip   varchar(48),
    oper_time    TIMESTAMP,
    login_center varchar(32)  NOT NULL,
    logout_type  varchar(32),
    success_flag SMALLINT     NULL DEFAULT 1,
    content      TEXT,
    domain_id    varchar(32),
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS t_agent_space_oper_log
(
    id            BIGSERIAL                                              NOT NULL,
    obj_type      varchar(32) NOT NULL,
    obj_id_field  varchar(32)  DEFAULT NULL,
    obj_id_value  varchar(32)  DEFAULT NULL,
    oper_type     varchar(32) NOT NULL,
    oper_ip       varchar(255) DEFAULT NULL,
    content       TEXT,
    oper_user     varchar(32)  DEFAULT NULL,
    oper_time     TIMESTAMP                                              NOT NULL,
    domain_id     varchar(32)  DEFAULT NULL,
    response_code varchar(32)  DEFAULT NULL,
    response_msg  varchar(255) DEFAULT NULL,
    success_flag  SMALLINT                                               NOT NULL DEFAULT 0,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ws_agent_task_resource
(
    id                varchar(255) NOT NULL,
    agent_id          varchar(255) NOT NULL,
    task_id           varchar(255) NOT NULL,
    is_enable         BOOLEAN     DEFAULT FALSE,
    status            varchar(255) DEFAULT NULL,
    agent_uri         varchar(255) DEFAULT NULL,
    web_uri           varchar(255) DEFAULT NULL,
    created_date      TIMESTAMP    DEFAULT NULL,
    last_updated_date TIMESTAMP    DEFAULT NULL,
    resource_id       varchar(36)  DEFAULT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ws_agent_builder_action_def
(
    id                      varchar(64) NOT NULL,
    step_id                 varchar(64)   DEFAULT NULL,
    type                    varchar(64)   DEFAULT NULL,
    tool_type               varchar(255)  DEFAULT NULL,
    content                 TEXT,
    display_content         text,
    plan_content            text,
    reasoning_content       text,
    file_list               varchar(2048) DEFAULT NULL,
    finished                INTEGER       DEFAULT NULL,
    domain_id               varchar(64)   DEFAULT NULL,
    dept_code               varchar(64)   DEFAULT NULL,
    created_date            TIMESTAMP     DEFAULT NULL,
    created_by_user_id      varchar(64)   DEFAULT NULL,
    last_updated_date       TIMESTAMP     DEFAULT NULL,
    last_updated_by_user_id varchar(64)   DEFAULT NULL,
    deleted                 BOOLEAN       DEFAULT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ws_agent_builder_file_def
(
    id                      varchar(64) NOT NULL,
    source_id               varchar(64),
    message_id              varchar(64),
    koo_page_id             varchar(128)         DEFAULT NULL,
    name                    varchar(512)         DEFAULT NULL,
    task_id                 varchar(64)          DEFAULT NULL,
    uri                     varchar(2048)        DEFAULT NULL,
    url                     varchar(2048)        DEFAULT NULL,
    type                    INTEGER              DEFAULT NULL,
    content                 TEXT,
    storage_type            INTEGER     NOT NULL DEFAULT 0,
    domain_id               varchar(64)          DEFAULT NULL,
    dept_code               varchar(64)          DEFAULT NULL,
    created_date            TIMESTAMP            DEFAULT NULL,
    created_by_user_id      varchar(64)          DEFAULT NULL,
    last_updated_date       TIMESTAMP            DEFAULT NULL,
    last_updated_by_user_id varchar(64)          DEFAULT NULL,
    deleted                 BOOLEAN              DEFAULT NULL,
    PRIMARY KEY (id)
);

ALTER TABLE ws_agent_builder_file_def ADD COLUMN IF NOT EXISTS extra_config text;

CREATE TABLE IF NOT EXISTS ws_agent_builder_message_def
(
    id                      varchar(64) NOT NULL,
    parent_id               varchar(64),
    task_id                 varchar(64)   DEFAULT NULL,
    type                    INTEGER       DEFAULT NULL,
    content                 text,
    file_list               varchar(2048) DEFAULT NULL,
    mcp_list                varchar(2048) DEFAULT NULL,
    domain_id               varchar(64)   DEFAULT NULL,
    dept_code               varchar(64)   DEFAULT NULL,
    created_date            TIMESTAMP     DEFAULT NULL,
    created_by_user_id      varchar(64)   DEFAULT NULL,
    last_updated_date       TIMESTAMP     DEFAULT NULL,
    last_updated_by_user_id varchar(64)   DEFAULT NULL,
    deleted                 BOOLEAN       DEFAULT NULL,
    rating                  INTEGER       DEFAULT (-1),
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ws_agent_builder_quota_def
(
    id                      varchar(64) NOT NULL,
    type                    varchar(255) DEFAULT NULL,
    quota                   INTEGER      DEFAULT NULL,
    used                    INTEGER      DEFAULT NULL,
    domain_id               varchar(64)  DEFAULT NULL,
    dept_code               varchar(64)  DEFAULT NULL,
    created_date            TIMESTAMP    DEFAULT NULL,
    created_by_user_id      varchar(64)  DEFAULT NULL,
    last_updated_date       TIMESTAMP    DEFAULT NULL,
    last_updated_by_user_id varchar(64)  DEFAULT NULL,
    deleted                 BOOLEAN      DEFAULT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ws_agent_builder_step_def
(
    id                      varchar(64) NOT NULL,
    agent_name              varchar(64) DEFAULT NULL,
    message_id              varchar(64) DEFAULT NULL,
    finished                BOOLEAN     DEFAULT NULL,
    domain_id               varchar(64) DEFAULT NULL,
    dept_code               varchar(64) DEFAULT NULL,
    created_date            TIMESTAMP    DEFAULT NULL,
    created_by_user_id      varchar(64) DEFAULT NULL,
    last_updated_date       TIMESTAMP    DEFAULT NULL,
    last_updated_by_user_id varchar(64) DEFAULT NULL,
    deleted                 BOOLEAN     DEFAULT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ws_agent_builder_task_def
(
    id                      varchar(64)   NOT NULL,
    name                    varchar(255)  DEFAULT NULL,
    agent_type              INTEGER       DEFAULT NULL,
    run_type                INTEGER       DEFAULT 0 NOT NULL,
    agent_id                varchar(64)   NULL,
    agent_list              varchar(255)  DEFAULT NULL,
    run_mode                INTEGER       DEFAULT NULL,
    status                  INTEGER       DEFAULT NULL,
    display_info            varchar(2048) DEFAULT NULL,
    extra_agent_config      varchar(2048) DEFAULT NULL,
    scheduled               BOOLEAN       DEFAULT NULL,
    storage_type            INTEGER       DEFAULT NULL,
    domain_id               varchar(64)   NOT NULL,
    dept_code               varchar(64)   DEFAULT NULL,
    created_date            TIMESTAMP     NOT NULL,
    created_by_user_id      varchar(64)   NOT NULL,
    last_updated_date       TIMESTAMP     DEFAULT NULL,
    last_updated_by_user_id varchar(64)   DEFAULT NULL,
    deleted                 BOOLEAN       DEFAULT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS t_agent_default
(
    id           varchar(64)  NOT NULL PRIMARY KEY,
    agent_id     varchar(64)  NULL,
    name         varchar(128) NOT NULL,
    description  varchar(255) NULL,
    icon         TEXT         NULL,
    creator      varchar(64)  NULL,
    created_date TIMESTAMP    NULL,
    updated_at   TIMESTAMP    NULL,
    type         INTEGER      NULL,
    sort         INTEGER      NULL
);

CREATE TABLE IF NOT EXISTS t_agent
(
    id                varchar(64)   NOT NULL,
    agent_id          varchar(64)   NOT NULL,
    type              varchar(32)   NULL,
    workspace_id      varchar(64)   NOT NULL,
    creator           varchar(64)   NULL,
    status            varchar(32)   NULL,
    domain_id         varchar(64)   NOT NULL,
    created_date      TIMESTAMP     NOT NULL,
    last_updated_date TIMESTAMP     NULL,
    deleted           BOOLEAN DEFAULT false NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS t_quick_command
(
    id                      varchar(64) NOT NULL,
    agent_id                varchar(64) NOT NULL,
    name                    varchar(64) NOT NULL,
    active                  INTEGER     NOT NULL,
    description             TEXT        NULL,
    content                 TEXT        NOT NULL,
    display_no              INTEGER     NOT NULL,
    recommend               INTEGER     NOT NULL,
    domain_id               varchar(64) NOT NULL,
    created_date            TIMESTAMP   NOT NULL,
    created_by_user_id      varchar(64) NOT NULL,
    last_updated_date       TIMESTAMP   NOT NULL,
    last_updated_by_user_id varchar(64) NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS t_i18n_resource
(
    id       BIGSERIAL                                                       NOT NULL,
    i18n_key varchar(255) NOT NULL,
    locale   varchar(50)  NOT NULL,
    message  text NOT NULL,
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_step_id_deleted ON ws_agent_builder_action_def (step_id, deleted);
CREATE INDEX IF NOT EXISTS idx_domain_id_task_id_deleted ON ws_agent_builder_file_def (domain_id, task_id, deleted);
CREATE INDEX IF NOT EXISTS idx_task_id_name_deleted ON ws_agent_builder_file_def (task_id, deleted);
CREATE INDEX IF NOT EXISTS idx_task_id ON ws_agent_builder_file_def (task_id);
CREATE INDEX IF NOT EXISTS name_and_task_id ON ws_agent_builder_file_def (name, task_id);
CREATE INDEX IF NOT EXISTS idx_task_id_deleted ON ws_agent_builder_message_def (task_id, deleted);
CREATE INDEX IF NOT EXISTS idx_message_id_deleted ON ws_agent_builder_step_def (message_id, deleted);
CREATE INDEX IF NOT EXISTS idx_domain_id_deleted ON ws_agent_builder_task_def (domain_id, deleted);
CREATE INDEX IF NOT EXISTS idx_agent_id ON t_agent (agent_id);
CREATE INDEX IF NOT EXISTS idx_domain_id ON t_agent (domain_id);
CREATE INDEX IF NOT EXISTS t_quick_command_agent_id_index ON t_quick_command (agent_id);
CREATE INDEX IF NOT EXISTS t_quick_command_domain_id_index ON t_quick_command (domain_id);
CREATE UNIQUE INDEX IF NOT EXISTS uk_key_locale ON t_i18n_resource (i18n_key, locale);
