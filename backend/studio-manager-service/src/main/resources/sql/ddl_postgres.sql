/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

-- common-service tables
CREATE TABLE IF NOT EXISTS t_common_license_record  (
    id varchar(36)   NOT NULL,
    sku_code varchar(64)   NOT NULL,
    attr_code varchar(64)   NOT NULL,
    resource_id varchar(36)   NOT NULL,
    oper_type varchar(8)   NOT NULL,
    quantity varchar(64)   NOT NULL,
    created_by_user_id varchar(32)   NULL DEFAULT NULL,
    created_date timestamp NOT NULL,
    last_updated_by_user_id varchar(32)   NULL DEFAULT NULL,
    last_updated_date timestamp NOT NULL,
    domain_id varchar(64)   NULL DEFAULT NULL,
    PRIMARY KEY (id)
    );

CREATE TABLE IF NOT EXISTS t_common_license  (
    id varchar(36)   NOT NULL,
    resource_id varchar(36)   NULL DEFAULT NULL,
    sku_code varchar(64)   NULL DEFAULT NULL,
    attr_code varchar(64)   NULL DEFAULT NULL,
    status varchar(32)   NULL DEFAULT NULL,
    current_value varchar(256)   NOT NULL,
    max_value varchar(32)   NULL DEFAULT '-1',
    type varchar(8)   NULL DEFAULT '2',
    created_by_user_id varchar(32)   NULL DEFAULT NULL,
    created_date timestamp NULL DEFAULT NULL,
    last_updated_by_user_id varchar(32)   NULL DEFAULT NULL,
    last_updated_date timestamp NULL DEFAULT NULL,
    domain_id varchar(64)   NULL DEFAULT NULL,
    main_key_id varchar(255) NULL,
    main_key_alias varchar(255) NULL,
    version int NULL,
    active SMALLINT NULL,
    latest SMALLINT NULL,
    PRIMARY KEY (id)
    );

CREATE TABLE IF NOT EXISTS t_common_reource_inst  (
    resource_id varchar(36)   NOT NULL,
    parent_id varchar(36)   NULL DEFAULT NULL,
    sku_code varchar(64)   NULL DEFAULT NULL,
    domain_id varchar(32)   NULL DEFAULT NULL,
    instance_id varchar(32)   NULL DEFAULT NULL,
    subproduct_code varchar(64)   NULL DEFAULT NULL,
    status varchar(32)   NULL DEFAULT NULL,
    cbc_order_id varchar(64)   NOT NULL,
    subproduct_id varchar(64)   NULL DEFAULT NULL,
    cloud_service_type varchar(64)   NULL DEFAULT NULL,
    region_id varchar(32)   NOT NULL,
    project_id varchar(64)   NOT NULL,
    created_date timestamp NULL DEFAULT NULL,
    created_by_user_id varchar(32)   NULL DEFAULT NULL,
    last_updated_date timestamp NULL DEFAULT NULL,
    last_updated_by_user_id varchar(32)   NULL DEFAULT NULL,
    PRIMARY KEY (resource_id)
    );

CREATE TABLE IF NOT EXISTS t_common_tenant  (
    domain_id varchar(64)   NOT NULL,
    domain_name varchar(256)   NOT NULL,
    description varchar(256)   NULL DEFAULT NULL,
    created_date TIMESTAMP NOT NULL,
    last_updated_date TIMESTAMP NOT NULL,
    status varchar(16)   NOT NULL,
    tenant_type varchar(2)   NULL DEFAULT NULL,
    ext_info varchar(256)   NULL DEFAULT NULL,
    PRIMARY KEY (domain_id)
    );

CREATE TABLE IF NOT EXISTS t_common_kms_info  (
    id varchar(255)  NOT NULL,
    domain_id varchar(64)  NOT NULL,
    cipher_text varchar(1024)  NULL DEFAULT NULL,
    status varchar(10)  NULL DEFAULT NULL,
    created_date timestamp NULL DEFAULT NULL,
    created_by_user_id varchar(32)  NULL DEFAULT NULL,
    last_updated_date timestamp NULL DEFAULT NULL,
    last_updated_by_user_id varchar(32)  NULL DEFAULT NULL,
    main_key_id varchar(255) NULL,
    main_key_alias varchar(255) NULL,
    version int NULL,
    active SMALLINT NULL,
    latest SMALLINT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS t_common_kms_relation  (
  domain_id varchar(64) NOT NULL,
  main_key_id varchar(255) NULL DEFAULT NULL,
  related_primary_key varchar(255) NULL DEFAULT NULL,
  type varchar(255) NULL DEFAULT NULL,
  created_date timestamp NULL DEFAULT NULL,
  created_by_user_id varchar(32) NULL DEFAULT NULL,
  last_updated_date timestamp NULL DEFAULT NULL,
  last_updated_by_user_id varchar(32) NULL DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS t_common_agreement  (
    id varchar(255)  NOT NULL,
    domain_id varchar(255)  NOT NULL,
    version varchar(32)  NOT NULL,
    privacy_statement varchar(255)  NOT NULL,
    agree_flag varchar(255) NULL DEFAULT NULL,
    created_date TIMESTAMP NULL DEFAULT NULL,
    created_by_user_id varchar(255)  NULL DEFAULT NULL,
    last_updated_date TIMESTAMP NULL DEFAULT NULL,
    last_updated_by_user_id varchar(255)  NULL DEFAULT NULL,
    PRIMARY KEY (id)
    );

-- manager tables
CREATE TABLE IF NOT EXISTS t_agent (
    agent_id                    VARCHAR(64)   NOT NULL,
    project_id                  VARCHAR(64) NOT NULL,
    name                        VARCHAR(64)   NULL,
    description                 VARCHAR(1024) NULL,
    icon                        TEXT    NULL,
    icon_name                   VARCHAR(64)   NULL,
    model_deployment_id         VARCHAR(128)  NULL,
    model_name                  VARCHAR(128)  NULL,
    model_config                VARCHAR(256)  NULL,
    instructions                TEXT          NULL,
    trigger_list                TEXT          NULL,
    memory_variables            TEXT          NULL,
    prologue                    VARCHAR(512)  NULL,
    suggest_queries             VARCHAR(4096) NULL,
    additional_questions_config TEXT          NULL,
    voice_interaction           TEXT          NULL,
    dsl_path                    VARCHAR(256)  NULL,
    ir_path                     VARCHAR(256)  NULL,
    type                        VARCHAR(32)   NULL,
    sub_type                    VARCHAR(50)   NULL,
    status                      VARCHAR(32)   NULL,
    creator                     VARCHAR(64)   NULL,
    creator_id                  VARCHAR(64) NULL,
    created_on                  TIMESTAMP     NULL     DEFAULT CURRENT_TIMESTAMP,
    updated_on                  TIMESTAMP     NULL     DEFAULT CURRENT_TIMESTAMP,
    published_on                TIMESTAMP     NULL,
    model_type                  VARCHAR(64)   NULL,
    knowledge_retrieve_policy   TEXT    NULL,
    workflow_switch_enabled     BOOLEAN NOT NULL DEFAULT FALSE,
    scheduling_mode             VARCHAR(32)   NOT NULL DEFAULT 'ReAct',
    model                       VARCHAR(64)   NULL,
    content_review              TEXT    NULL,
    safety_barrier              BOOLEAN    NULL,
    workspace_id                VARCHAR(64)   NULL,
    trace_id                    VARCHAR(64)   NULL,
    domain_id                   VARCHAR(64)   NULL,
    agent_variables             TEXT    NULL,
    memory_config               TEXT    NULL,
    plan_qa_independent         BOOLEAN    NULL,
    plan_model                  VARCHAR(64)   NULL,
    plan_model_deployment_id    VARCHAR(128)  NULL,
    plan_model_name             VARCHAR(128)  NULL,
    plan_model_config           VARCHAR(128)  NULL,
    plan_model_type             VARCHAR(64)   NULL,
    deleted                     BOOLEAN    NOT NULL DEFAULT false,
    is_share                    SMALLINT    NOT NULL DEFAULT 0,
    reference                   VARCHAR(64)   NULL,
    input_variables             TEXT    NULL,
    PRIMARY KEY (agent_id)
    );

CREATE TABLE IF NOT EXISTS t_agent_version (
    version_id                  VARCHAR(64)   NOT NULL,
    agent_id                    VARCHAR(64)   NOT NULL,
    project_id                  VARCHAR(64) NOT NULL,
    name                        VARCHAR(64)   NULL,
    description                 VARCHAR(1024) NULL,
    icon                        TEXT    NULL,
    icon_name                   VARCHAR(64)   NULL,
    tags                        VARCHAR(512)  NULL,
    instructions                TEXT          NULL,
    trigger_list                TEXT          NULL,
    prologue                    VARCHAR(512)  NULL,
    suggest_queries             VARCHAR(4096) NULL,
    additional_questions_config TEXT          NULL,
    ir_path                     VARCHAR(256)  NULL,
    dsl_path                    VARCHAR(256)  NULL,
    is_online                   BOOLEAN NOT NULL DEFAULT true,
    creator                     VARCHAR(64)   NULL,
    created_on                  TIMESTAMP     NULL,
    updated_on                  TIMESTAMP     NULL,
    published_on                TIMESTAMP     NULL,
    workspace_id                VARCHAR(64)   NULL,
    PRIMARY KEY (version_id)
    );

CREATE TABLE IF NOT EXISTS t_agent_workflow (
    id                  VARCHAR(64)   NOT NULL,
    name                VARCHAR(64)   NOT NULL,
    code                VARCHAR(64)   NULL,
    description         VARCHAR(1024) NULL,
    avatar              TEXT    NULL,
    icon_name           VARCHAR(64)   NULL,
    customize_node      SMALLINT    NULL,
    dsl_path            VARCHAR(256)  NULL,
    ir_path             VARCHAR(256)  NULL,
    status              VARCHAR(32)   NULL,
    trigger_list        TEXT          NULL,
    visibility          VARCHAR(32)   NULL,
    created_at          BIGINT    NULL,
    updated_at          BIGINT    NULL,
    published_at        BIGINT    NULL,
    created_by          VARCHAR(64)   NULL,
    creator_id          VARCHAR(64) NULL,
    updated_by          VARCHAR(64)   NULL,
    updater_id          VARCHAR(64)   NULL,
    project_id          VARCHAR(64) NOT NULL,
    workspace_id        VARCHAR(64)   NULL,
    domain_id           VARCHAR(64)   NOT NULL,
    deploy_wf_version   BIGINT    NULL,
    ref_workflows       TEXT          NULL,
    last_version_id     VARCHAR(64)   NULL,
    deleted             BOOLEAN    NULL,
    test_status         SMALLINT    NULL,
    workflow_type       VARCHAR(32)   NULL,
    trace_id            VARCHAR(64)   NULL,
    is_share            SMALLINT    NOT NULL DEFAULT 0,
    PRIMARY KEY (id)
    );

CREATE TABLE IF NOT EXISTS t_history_agent_workflow (
    history_id          VARCHAR(64)   NOT NULL,
    id                  VARCHAR(64)   NOT NULL,
    name                VARCHAR(64)   NOT NULL,
    code                VARCHAR(64)   NULL,
    description         VARCHAR(1024) NULL,
    avatar              TEXT    NULL,
    icon_name           VARCHAR(64)   NULL,
    dsl_path            VARCHAR(256)  NULL,
    ir_path             VARCHAR(256)  NULL,
    status              VARCHAR(32)   NULL,
    trigger_list        TEXT          NULL,
    visibility          VARCHAR(32)   NULL,
    created_at          BIGINT    NULL,
    updated_at          BIGINT    NULL,
    published_at        BIGINT    NULL,
    created_by          VARCHAR(64)   NULL,
    creator_id          VARCHAR(64)   NULL,
    updated_by          VARCHAR(64)   NULL,
    updater_id          VARCHAR(64)   NULL,
    project_id          VARCHAR(64)   NOT NULL,
    workspace_id        VARCHAR(64)   NULL,
    domain_id           VARCHAR(64)   NOT NULL,
    deploy_wf_version   BIGINT    NULL,
    ref_workflows       TEXT          NULL,
    last_version_id     VARCHAR(64)   NULL,
    deleted             BOOLEAN    NULL,
    test_status         SMALLINT    NULL,
    customize_node      SMALLINT    NULL,
    workflow_type       VARCHAR(32)   NULL,
    trace_id            VARCHAR(64)   NULL,
    is_share            SMALLINT    NOT NULL DEFAULT 0,
    PRIMARY KEY (history_id)
    );

CREATE TABLE IF NOT EXISTS t_app (
    app_id          VARCHAR(64)  NOT NULL,
    project_id      VARCHAR(64) NOT NULL,
    name            VARCHAR(64)  NOT NULL,
    description     VARCHAR(1024) NULL,
    icon            TEXT   NOT NULL,
    icon_name       VARCHAR(64)  NULL,
    tags            VARCHAR(512) NULL,
    app_type        VARCHAR(32)  NOT NULL,
    resource_id     VARCHAR(64)  NOT NULL,
    resource_type   VARCHAR(32)  NOT NULL,
    creator         VARCHAR(64)  NOT NULL,
    published_on    TIMESTAMP    NOT NULL,
    prologue        TEXT         NULL,
    suggest_queries TEXT         NULL,
    workflow_type   VARCHAR(16)  NULL,
    input_params    TEXT   NULL,
    output_params   TEXT   NULL,
    workspace_id    VARCHAR(64)  NULL,
    trace_id        VARCHAR(64)  NULL,
    deleted         BOOLEAN   NOT NULL DEFAULT false,
    updated_on      TIMESTAMP    NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (app_id,project_id)
    );

CREATE TABLE IF NOT EXISTS t_tag (
    tag_id     VARCHAR(64)  NOT NULL,
    name       VARCHAR(128) NOT NULL,
    name_en    VARCHAR(128) NOT NULL,
    created_on TIMESTAMP     NULL     DEFAULT CURRENT_TIMESTAMP,
    updated_on TIMESTAMP     NULL     DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (tag_id)
    );

CREATE TABLE IF NOT EXISTS QRTZ_JOB_DETAILS
(
    SCHED_NAME        VARCHAR(120) NOT NULL,
    JOB_NAME          VARCHAR(200) NOT NULL,
    JOB_GROUP         VARCHAR(200) NOT NULL,
    DESCRIPTION       VARCHAR(250) NULL,
    JOB_CLASS_NAME    VARCHAR(250) NOT NULL,
    IS_DURABLE        VARCHAR(1)   NOT NULL,
    IS_NONCONCURRENT  VARCHAR(1)   NOT NULL,
    IS_UPDATE_DATA    VARCHAR(1)   NOT NULL,
    REQUESTS_RECOVERY VARCHAR(1)   NOT NULL,
    JOB_DATA          BYTEA         NULL,
    PRIMARY KEY (SCHED_NAME, JOB_NAME, JOB_GROUP)
    );

CREATE TABLE IF NOT EXISTS QRTZ_TRIGGERS
(
    SCHED_NAME      VARCHAR(120) NOT NULL,
    TRIGGER_NAME    VARCHAR(200) NOT NULL,
    TRIGGER_GROUP   VARCHAR(200) NOT NULL,
    JOB_NAME        VARCHAR(200) NOT NULL,
    JOB_GROUP       VARCHAR(200) NOT NULL,
    DESCRIPTION     VARCHAR(250) NULL,
    NEXT_FIRE_TIME  BIGINT   NULL,
    PREV_FIRE_TIME  BIGINT   NULL,
    PRIORITY        INTEGER      NULL,
    TRIGGER_STATE   VARCHAR(16)  NOT NULL,
    TRIGGER_TYPE    VARCHAR(8)   NOT NULL,
    START_TIME      BIGINT   NOT NULL,
    END_TIME        BIGINT   NULL,
    CALENDAR_NAME   VARCHAR(200) NULL,
    MISFIRE_INSTR   SMALLINT  NULL,
    JOB_DATA        BYTEA         NULL,
    PRIMARY KEY (SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP),
    FOREIGN KEY (SCHED_NAME, JOB_NAME, JOB_GROUP)
    REFERENCES QRTZ_JOB_DETAILS(SCHED_NAME, JOB_NAME, JOB_GROUP)
    );

CREATE TABLE IF NOT EXISTS QRTZ_SIMPLE_TRIGGERS
(
    SCHED_NAME      VARCHAR(120)    NOT NULL,
    TRIGGER_NAME    VARCHAR(200)    NOT NULL,
    TRIGGER_GROUP   VARCHAR(200)    NOT NULL,
    REPEAT_COUNT    BIGINT       NOT NULL,
    REPEAT_INTERVAL BIGINT      NOT NULL,
    TIMES_TRIGGERED BIGINT      NOT NULL,
    PRIMARY KEY (SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP),
    FOREIGN KEY (SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP)
    REFERENCES QRTZ_TRIGGERS(SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP)
    );

CREATE TABLE IF NOT EXISTS QRTZ_CRON_TRIGGERS
(
    SCHED_NAME      VARCHAR(120) NOT NULL,
    TRIGGER_NAME    VARCHAR(200) NOT NULL,
    TRIGGER_GROUP   VARCHAR(200) NOT NULL,
    CRON_EXPRESSION VARCHAR(120) NOT NULL,
    TIME_ZONE_ID    VARCHAR(80),
    PRIMARY KEY (SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP),
    FOREIGN KEY (SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP)
    REFERENCES QRTZ_TRIGGERS(SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP)
    );

CREATE TABLE IF NOT EXISTS QRTZ_SIMPROP_TRIGGERS
(
    SCHED_NAME      VARCHAR(120)    NOT NULL,
    TRIGGER_NAME    VARCHAR(200)    NOT NULL,
    TRIGGER_GROUP   VARCHAR(200)    NOT NULL,
    STR_PROP_1      VARCHAR(512)    NULL,
    STR_PROP_2      VARCHAR(512)    NULL,
    STR_PROP_3      VARCHAR(512)    NULL,
    INT_PROP_1      INT             NULL,
    INT_PROP_2      INT             NULL,
    LONG_PROP_1     BIGINT          NULL,
    LONG_PROP_2     BIGINT          NULL,
    DEC_PROP_1      NUMERIC(13,4)   NULL,
    DEC_PROP_2      NUMERIC(13,4)   NULL,
    BOOL_PROP_1     VARCHAR(1)      NULL,
    BOOL_PROP_2     VARCHAR(1)      NULL,
    PRIMARY KEY (SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP),
    FOREIGN KEY (SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP)
    REFERENCES QRTZ_TRIGGERS(SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP)
    );

CREATE TABLE IF NOT EXISTS QRTZ_BLOB_TRIGGERS
(
    SCHED_NAME      VARCHAR(120)    NOT NULL,
    TRIGGER_NAME    VARCHAR(200)    NOT NULL,
    TRIGGER_GROUP   VARCHAR(200)    NOT NULL,
    BLOB_DATA       BYTEA            NULL,
    PRIMARY KEY (SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP),
    FOREIGN KEY (SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP)
    REFERENCES QRTZ_TRIGGERS(SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP)
    );

CREATE TABLE IF NOT EXISTS QRTZ_CALENDARS
(
    SCHED_NAME      VARCHAR(120)    NOT NULL,
    CALENDAR_NAME   VARCHAR(200)    NOT NULL,
    CALENDAR        BYTEA            NOT NULL,
    PRIMARY KEY (SCHED_NAME, CALENDAR_NAME)
    );

CREATE TABLE IF NOT EXISTS QRTZ_PAUSED_TRIGGER_GRPS
(
    SCHED_NAME      VARCHAR(120) NOT NULL,
    TRIGGER_GROUP   VARCHAR(200) NOT NULL,
    PRIMARY KEY (SCHED_NAME, TRIGGER_GROUP)
    );

CREATE TABLE IF NOT EXISTS QRTZ_FIRED_TRIGGERS
(
    SCHED_NAME          VARCHAR(120)    NOT NULL,
    ENTRY_ID            VARCHAR(95)     NOT NULL,
    TRIGGER_NAME        VARCHAR(200)    NOT NULL,
    TRIGGER_GROUP       VARCHAR(200)    NOT NULL,
    INSTANCE_NAME       VARCHAR(200)    NOT NULL,
    FIRED_TIME          BIGINT      NOT NULL,
    SCHED_TIME          BIGINT      NOT NULL,
    PRIORITY            INTEGER         NOT NULL,
    STATE               VARCHAR(16)     NOT NULL,
    JOB_NAME            VARCHAR(200)    NULL,
    JOB_GROUP           VARCHAR(200)    NULL,
    IS_NONCONCURRENT    VARCHAR(1)      NULL,
    REQUESTS_RECOVERY   VARCHAR(1)      NULL,
    PRIMARY KEY (SCHED_NAME, ENTRY_ID)
    );

CREATE TABLE IF NOT EXISTS QRTZ_SCHEDULER_STATE
(
    SCHED_NAME          VARCHAR(120)    NOT NULL,
    INSTANCE_NAME       VARCHAR(200)    NOT NULL,
    LAST_CHECKIN_TIME   BIGINT      NOT NULL,
    CHECKIN_INTERVAL    BIGINT      NOT NULL,
    PRIMARY KEY (SCHED_NAME, INSTANCE_NAME)
    );

CREATE TABLE IF NOT EXISTS QRTZ_LOCKS
(
    SCHED_NAME  VARCHAR(120)    NOT NULL,
    LOCK_NAME   VARCHAR(40)     NOT NULL,
    PRIMARY KEY (SCHED_NAME, LOCK_NAME)
    );

CREATE INDEX IF NOT EXISTS IDX_QRTZ_BLOB_TRIG_INST ON QRTZ_BLOB_TRIGGERS(SCHED_NAME,TRIGGER_NAME,TRIGGER_GROUP);

CREATE INDEX IF NOT EXISTS IDX_QRTZ_J_REQ_RECOVERY ON QRTZ_JOB_DETAILS(SCHED_NAME,REQUESTS_RECOVERY);
CREATE INDEX IF NOT EXISTS IDX_QRTZ_J_GRP ON QRTZ_JOB_DETAILS(SCHED_NAME,JOB_GROUP);

CREATE INDEX IF NOT EXISTS IDX_QRTZ_T_J ON QRTZ_TRIGGERS(SCHED_NAME,JOB_NAME,JOB_GROUP);
CREATE INDEX IF NOT EXISTS IDX_QRTZ_T_JG ON QRTZ_TRIGGERS(SCHED_NAME,JOB_GROUP);
CREATE INDEX IF NOT EXISTS IDX_QRTZ_T_C ON QRTZ_TRIGGERS(SCHED_NAME,CALENDAR_NAME);
CREATE INDEX IF NOT EXISTS IDX_QRTZ_T_G ON QRTZ_TRIGGERS(SCHED_NAME,TRIGGER_GROUP);
CREATE INDEX IF NOT EXISTS IDX_QRTZ_T_STATE ON QRTZ_TRIGGERS(SCHED_NAME,TRIGGER_STATE);
CREATE INDEX IF NOT EXISTS IDX_QRTZ_T_N_STATE ON QRTZ_TRIGGERS(SCHED_NAME,TRIGGER_NAME,TRIGGER_GROUP,TRIGGER_STATE);
CREATE INDEX IF NOT EXISTS IDX_QRTZ_T_N_G_STATE ON QRTZ_TRIGGERS(SCHED_NAME,TRIGGER_GROUP,TRIGGER_STATE);
CREATE INDEX IF NOT EXISTS IDX_QRTZ_T_NEXT_FIRE_TIME ON QRTZ_TRIGGERS(SCHED_NAME,NEXT_FIRE_TIME);
CREATE INDEX IF NOT EXISTS IDX_QRTZ_T_NFT_ST ON QRTZ_TRIGGERS(SCHED_NAME,TRIGGER_STATE,NEXT_FIRE_TIME);
CREATE INDEX IF NOT EXISTS IDX_QRTZ_T_NFT_MISFIRE ON QRTZ_TRIGGERS(SCHED_NAME,MISFIRE_INSTR,NEXT_FIRE_TIME);
CREATE INDEX IF NOT EXISTS IDX_QRTZ_T_NFT_ST_MISFIRE ON QRTZ_TRIGGERS(SCHED_NAME,MISFIRE_INSTR,NEXT_FIRE_TIME,TRIGGER_STATE);
CREATE INDEX IF NOT EXISTS IDX_QRTZ_T_NFT_ST_MISFIRE_GRP ON QRTZ_TRIGGERS(SCHED_NAME,MISFIRE_INSTR,NEXT_FIRE_TIME,TRIGGER_GROUP,TRIGGER_STATE);

CREATE INDEX IF NOT EXISTS IDX_QRTZ_FT_TRIG_INST_NAME ON QRTZ_FIRED_TRIGGERS(SCHED_NAME,INSTANCE_NAME);
CREATE INDEX IF NOT EXISTS IDX_QRTZ_FT_INST_JOB_REQ_RCVRY ON QRTZ_FIRED_TRIGGERS(SCHED_NAME,INSTANCE_NAME,REQUESTS_RECOVERY);
CREATE INDEX IF NOT EXISTS IDX_QRTZ_FT_J_G ON QRTZ_FIRED_TRIGGERS(SCHED_NAME,JOB_NAME,JOB_GROUP);
CREATE INDEX IF NOT EXISTS IDX_QRTZ_FT_JG ON QRTZ_FIRED_TRIGGERS(SCHED_NAME,JOB_GROUP);
CREATE INDEX IF NOT EXISTS IDX_QRTZ_FT_T_G ON QRTZ_FIRED_TRIGGERS(SCHED_NAME,TRIGGER_NAME,TRIGGER_GROUP);
CREATE INDEX IF NOT EXISTS IDX_QRTZ_FT_TG ON QRTZ_FIRED_TRIGGERS(SCHED_NAME,TRIGGER_GROUP);

CREATE TABLE IF NOT EXISTS t_mapping
(
    mapping_id              VARCHAR(64)   NOT NULL,
    app_id                  VARCHAR(64)   NOT NULL,
    app_version             VARCHAR(64)   NULL,
    app_type                VARCHAR(32)   NOT NULL,
    app_sub_type            VARCHAR(100)  NULL,
    app_name                VARCHAR(64)   NOT NULL,
    resource_id             VARCHAR(128)  NOT NULL,
    resource_type           VARCHAR(32)   NOT NULL,
    resource_name           VARCHAR(1000) NULL,
    resource_version        VARCHAR(64)   NULL,
    valid                   BOOLEAN NOT NULL DEFAULT TRUE,
    resource_desc           VARCHAR(2048) NULL,
    resource_choose_tools   VARCHAR(2048) NULL,
    created_on              TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on              TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reference_type          VARCHAR(64)   NULL DEFAULT 'direct',
    resource_workspace_id   VARCHAR(64)   NULL,
    extends                 TEXT    NULL,
    app_workspace_id        VARCHAR(64)   NULL,
    PRIMARY KEY (mapping_id)
    );

CREATE TABLE IF NOT EXISTS t_release_version (
    id              VARCHAR(64)   NOT NULL,
    version_id      VARCHAR(64)   NOT NULL,
    version_name    VARCHAR(64)   NOT NULL,
    version_note    VARCHAR(1024)  NOT NULL,
    app_id          VARCHAR(64)   NOT NULL,
    app_type        VARCHAR(32)   NOT NULL,
    status          VARCHAR(32)   NULL,
    dsl_path        VARCHAR(256)  NULL,
    ir_path         VARCHAR(256)  NULL,
    extend1         TEXT          NULL,
    creator         VARCHAR(64)   NULL,
    creator_id      VARCHAR(64) NULL,
    app_sub_type    VARCHAR(100)  NULL,
    released_on     TIMESTAMP     NULL DEFAULT CURRENT_TIMESTAMP,
    deleted         BOOLEAN    NOT NULL DEFAULT false,
    updated_on      TIMESTAMP     NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
    );

CREATE TABLE IF NOT EXISTS t_release_channel (
    id              VARCHAR(64)   NOT NULL,
    app_id          VARCHAR(64)   NOT NULL,
    app_type        VARCHAR(32)   NOT NULL,
    version_id      VARCHAR(64)   NOT NULL,
    version_name    VARCHAR(64)   NOT NULL,
    channel_type    VARCHAR(32)   NOT NULL,
    entry_point     VARCHAR(255)  NULL,
    qr_code         VARCHAR(1024) NULL,
    short_code      VARCHAR(16)   NULL,
    metadata        VARCHAR(4096) NULL,
    status          VARCHAR(32)   NULL,
    detail          VARCHAR(1024) NULL,
    creator         VARCHAR(64)   NULL,
    creator_id      VARCHAR(64) NULL,
    app_sub_type    VARCHAR(100)  NULL,
    released_on     TIMESTAMP     NULL DEFAULT CURRENT_TIMESTAMP,
    project_id      VARCHAR(64) NULL,
    workspace_id    VARCHAR(64)   NULL,
    trace_id        VARCHAR(64)   NULL,
    visibility_scope VARCHAR(8)   NULL DEFAULT 'TENANT',
    call_count      INT           NULL DEFAULT 100,
    PRIMARY KEY (id)
    );

CREATE TABLE IF NOT EXISTS t_analytics_event (
    event_id      VARCHAR(64)     NOT NULL,
    event_type    VARCHAR(64)     NOT NULL,
    user_id       VARCHAR(255) NULL,
    project_id    VARCHAR(64) NULL,
    app_type      VARCHAR(255)    NULL,
    app_id        VARCHAR(128)   NULL,
    channel       VARCHAR(255)    NULL,
    event_time    TIMESTAMP       NULL DEFAULT CURRENT_TIMESTAMP,
    event_date    TIMESTAMP       NULL DEFAULT CURRENT_TIMESTAMP,
    new_app_user  SMALLINT      NULL DEFAULT 0,
    PRIMARY KEY (event_id)
    );

CREATE TABLE IF NOT EXISTS t_complex_intent (
    intent_id         VARCHAR(64)     NOT NULL,
    name              VARCHAR(64)     NULL,
    project_id        VARCHAR(64) NULL,
    domain_id         VARCHAR(64)     NOT NULL DEFAULT '0',
    description       VARCHAR(255)    NULL,
    branches          TEXT            NULL,
    creator_id        VARCHAR(64) NULL,
    branches_cnt      INT             NULL,
    created_on        TIMESTAMP       NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on        TIMESTAMP       NULL DEFAULT CURRENT_TIMESTAMP,
    workspace_id      VARCHAR(64)     NULL,
    trace_id          VARCHAR(64)     NULL,
    PRIMARY KEY (intent_id)
    );

CREATE TABLE IF NOT EXISTS t_complex_intent_branch (
    branch_id        VARCHAR(64)     NOT NULL,
    intent_id         VARCHAR(64)     NOT NULL,
    branch_index      INT     NOT NULL,
    project_id        VARCHAR(64) NULL,
    branch_name       VARCHAR(64)     NULL,
    content           TEXT            NULL,
    faq_ids           TEXT            NULL,
    creator_id        VARCHAR(64) NULL,
    created_on        TIMESTAMP       NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on        TIMESTAMP       NULL DEFAULT CURRENT_TIMESTAMP,
    workspace_id      VARCHAR(64)     NULL,
    trace_id          VARCHAR(64)     NULL,
    PRIMARY KEY (branch_id)
    );

CREATE TABLE IF NOT EXISTS t_credential(
    id            VARCHAR(64)     NOT NULL,
    resource_id   VARCHAR(64)     NOT NULL,
    resource_type VARCHAR(32)     NOT NULL,
    project_id    VARCHAR(64) NOT NULL,
    auth_keys     VARCHAR(4096)   NOT NULL,
    user_id       VARCHAR(255) NOT NULL,
    workspace_id  VARCHAR(64)     NULL,
    domain_id     VARCHAR(64)     NULL,
    created_on    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(id)
    );

CREATE TABLE IF NOT EXISTS t_workspace (
    id               VARCHAR(64)   NOT NULL,
    project_id       VARCHAR(64) NOT NULL,
    name             VARCHAR(64)   NULL,
    flag             VARCHAR(64)   NULL,
    description      VARCHAR(2048) NULL,
    icon             TEXT    NULL,
    tenant_id        VARCHAR(64)   NOT NULL,
    type             VARCHAR(32)   NULL,
    status           VARCHAR(32)   NULL,
    created_on       TIMESTAMP     NULL     DEFAULT CURRENT_TIMESTAMP,
    creator          VARCHAR(64)   NULL,
    creator_id       VARCHAR(64) NULL,
    updated_on       TIMESTAMP     NULL     DEFAULT CURRENT_TIMESTAMP,
    updater          VARCHAR(64)   NULL,
    updater_id       VARCHAR(64)   NULL,
    is_preset_agent  INT           DEFAULT 0 NULL,
    domain_id       VARCHAR(64)   NULL,
    PRIMARY KEY (id)
    );

CREATE TABLE IF NOT EXISTS t_workspace_member
(
    id            varchar(64) not null,
    workspace_id  varchar(64) not null,
    member_id     varchar(64) not null,
    member_name   varchar(64) not null,
    member_source varchar(32) not null,
    domain_id     varchar(64) not null,
    role          varchar(64) not null,
    status        SMALLINT default 1 not null,
    creator       varchar(64) not null,
    creator_id    varchar(64) not null,
    updater       varchar(64) not null,
    updater_id    varchar(64) not null,
    created_on    timestamp default CURRENT_TIMESTAMP not null,
    updated_on    timestamp default CURRENT_TIMESTAMP not null,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS t_dependency
(
    id VARCHAR(64) NOT NULL PRIMARY KEY,
    version_id VARCHAR(64) NOT NULL,
    name VARCHAR(32) NULL,
    function_graph_name VARCHAR(64) NULL,
    description VARCHAR(255) NULL,
    runtime VARCHAR(64) NULL,
    scope VARCHAR(16) NULL,
    link TEXT NULL,
    project_id VARCHAR(64) NULL,
    domain_id VARCHAR(64) NOT NULL DEFAULT '0',
    workspace_id VARCHAR(64) NULL,
    creator_id VARCHAR(64) NOT NULL,
    created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP NULL,
    updater_id VARCHAR(64) NULL,
    updated_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP NULL,
    version SMALLINT NULL,
    deleted BOOLEAN DEFAULT false NULL
);

CREATE TABLE IF NOT EXISTS t_function (
    id VARCHAR(64) NOT NULL PRIMARY KEY,
    function_urn VARCHAR(256) NOT NULL,
    name VARCHAR(50) NOT NULL,
    function_name VARCHAR(64) NOT NULL,
    runtime VARCHAR(64) NULL,
    usage_type VARCHAR(50) NOT NULL,
    function_input TEXT NULL,
    function_output TEXT NULL,
    concurrent_num SMALLINT DEFAULT 1 NULL,
    visibility VARCHAR(16) NULL,
    description VARCHAR(256) NULL,
    function_expression VARCHAR(255) NULL,
    function_code BYTEA NULL,
    code_type VARCHAR(255) NULL,
    project_id VARCHAR(64) NULL,
    domain_id VARCHAR(64) NOT NULL DEFAULT '0',
    workspace_id VARCHAR(64) NULL,
    creator_id VARCHAR(64) NOT NULL,
    created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP NULL,
    updater_id VARCHAR(64) NULL,
    updated_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT false NULL,
    trace_id VARCHAR(64) NULL,
    template_version VARCHAR(64) NOT NULL DEFAULT 'v1'
);

CREATE TABLE IF NOT EXISTS t_function_dependency_map
(
    id VARCHAR(64) NOT NULL PRIMARY KEY,
    function_id VARCHAR(64) NOT NULL,
    function_name VARCHAR(64) NOT NULL,
    dependency_id VARCHAR(64) NOT NULL,
    version_id VARCHAR(64) NOT NULL,
    dependency_name VARCHAR(96) NULL,
    runtime VARCHAR(64) NULL,
    scope VARCHAR(16) NULL,
    link TEXT NULL,
    valid SMALLINT NOT NULL DEFAULT 1,
    dependency_version INTEGER NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS t_task (
    id                VARCHAR(64)     NOT NULL,
    name              VARCHAR(64)     NOT NULL,
    conversation_id   VARCHAR(64)     NULL,
    user_id           VARCHAR(255) NULL,
    project_id        VARCHAR(64) NULL,
    domain_id         VARCHAR(64)     NULL,
    workspace_id      VARCHAR(64)     NULL,
    type              VARCHAR(32)     NULL,
    mode              VARCHAR(32)     NULL,
    app_id            VARCHAR(64)     NULL,
    app_version       VARCHAR(128)    NULL,
    is_published      BOOLEAN      NULL,
    status            VARCHAR(32)     NULL,
    inputs            TEXT      NULL,
    outputs           TEXT      NULL,
    timeout           INTEGER         NULL,
    message           VARCHAR(2048)   NULL,
    create_time       TIMESTAMP       NOT NULL,
    start_time        TIMESTAMP       NULL,
    update_time       TIMESTAMP       NULL,
    finish_time       TIMESTAMP       NULL,
    PRIMARY KEY (id)
    );

CREATE TABLE IF NOT EXISTS t_apig_api_groups (
    ID varchar(36) NOT NULL,
    NAME text,
    DESCRIPTION text,
    TENANT_ID varchar(64) DEFAULT NULL,
    CREATED_BY_USER_ID varchar(64) DEFAULT NULL,
    LAST_UPDATED_BY_USER_ID varchar(64) DEFAULT NULL,
    CREATED_DATE timestamp NULL DEFAULT NULL,
    LAST_UPDATED_DATE timestamp NULL DEFAULT NULL,
    STATUS varchar(16) NOT NULL,
    PRIMARY KEY (ID)
);

CREATE TABLE IF NOT EXISTS t_apig_apis (
                               ID varchar(36) NOT NULL,
                               NAME text,
                               GROUP_ID varchar(64) NOT NULL,
                               DESCRIPTION text,
                               tenant_id varchar(64) DEFAULT NULL,
                               THROTTLING_POLICY_ID varchar(64) DEFAULT NULL,
                               API_POLICY_BIND_ID varchar(64) DEFAULT NULL,
                               CREATED_BY_USER_ID varchar(64) DEFAULT NULL,
                               LAST_UPDATED_BY_USER_ID varchar(64) DEFAULT NULL,
                               CREATED_DATE timestamp NULL DEFAULT NULL,
                               LAST_UPDATED_DATE timestamp NULL DEFAULT NULL,
                               STATUS varchar(16) NOT NULL,
                               PRIMARY KEY (ID)
);

CREATE TABLE IF NOT EXISTS t_environment_manager_info
(
    id           varchar(64)                         not null
        primary key,
    name         varchar(48)                         null,
    description  varchar(128)                        null,
    is_default   BOOLEAN                          null,
    status       varchar(16)                         null,
    resources    varchar(512)                        null,
    created_on   timestamp default CURRENT_TIMESTAMP not null,
    creator_id   varchar(64)                         null,
    updated_on   timestamp default CURRENT_TIMESTAMP not null,
    updater_id   varchar(64)                         null,
    project_id   varchar(64)                         null,
    domain_id    varchar(64)                         null
);

CREATE TABLE IF NOT EXISTS t_environment_variable_info
(
    id  varchar(64) not null
        primary key,
    env_variable text                                null,
    created_on   timestamp default CURRENT_TIMESTAMP not null,
    creator_id   varchar(64)  null,
    updated_on   timestamp default CURRENT_TIMESTAMP not null,
    updater_id   varchar(64) null,
    project_id   varchar(64)  not null,
    workspace_id varchar(64)  not null,
    env_id       varchar(64)  not null
);

CREATE TABLE IF NOT EXISTS t_structured_message
(
    id           VARCHAR(64)                         NOT NULL,
    name         VARCHAR(128)                        NULL,
    category     VARCHAR(64)                         NULL,
    content       text                               NULL,
    status       varchar(64)                         NULL,
    import_method varchar(64)                        NULL,
    visibility   VARCHAR(64)  DEFAULT 'WORKSPACE'    NULL,
    workspace_id VARCHAR(64)                         NULL,
    domain_id    VARCHAR(64)                         NULL,
    user_id      VARCHAR(255) NULL,
    project_id   VARCHAR(64) NOT NULL,
    created_on   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP NOT NULL,
    creator_id   VARCHAR(64) NULL,
    updated_on   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updater_id   VARCHAR(64)                         NULL,
    PRIMARY KEY (id)
    );

CREATE TABLE IF NOT EXISTS t_share_resource
(
    resource_id VARCHAR(128) NOT NULL PRIMARY KEY,
    resource_name VARCHAR(64) NOT NULL,
    resource_type VARCHAR(32) NOT NULL,
    workspace_id VARCHAR(64) NOT NULL,
    workspace_name VARCHAR(64) NOT NULL,
    trace_id VARCHAR(64) NULL,
    version_list VARCHAR(4096) NOT NULL,
    project_id VARCHAR(64) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    creator_id VARCHAR(128) NOT NULL,
    creator VARCHAR(64) NOT NULL,
    create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updater_id VARCHAR(128) NOT NULL,
    updater VARCHAR(64) NOT NULL,
    update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS t_share_scope
(
    id VARCHAR(64) NOT NULL PRIMARY KEY,
    resource_id VARCHAR(64) NOT NULL,
    resource_type VARCHAR(64) NOT NULL,
    workspace_id VARCHAR(64) NOT NULL,
    project_id VARCHAR(64) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL
    );

CREATE TABLE IF NOT EXISTS t_users (
    id BIGINT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    real_name VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20),
    department VARCHAR(100),
    position VARCHAR(100),
    external_id VARCHAR(100),
    source VARCHAR(20),
    domain_id VARCHAR(100),
    project_id VARCHAR(100),
    created_time TIMESTAMP,
    updated_time TIMESTAMP,
    expire_time TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
    );

CREATE TABLE IF NOT EXISTS  t_sessions (
    id BIGINT PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL UNIQUE,
    user_id BIGINT,
    username VARCHAR(100),
    ip_address VARCHAR(45),
    user_agent TEXT,
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expire_time TIMESTAMP,
    logout_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    domain_id VARCHAR(100),
    project_id VARCHAR(100)
    );

CREATE TABLE IF NOT EXISTS t_card
(
    id              varchar(64)  NOT NULL,
    name            varchar(255) NOT NULL,
    description     varchar(2000) DEFAULT NULL,
    icon            TEXT,
    resource_type   varchar(64)  DEFAULT NULL,
    resource_url    varchar(2000) DEFAULT NULL,
    metadata        text,
    project_id      varchar(64) DEFAULT NULL,
    workspace_id    varchar(64) DEFAULT NULL,
    status          varchar(32) DEFAULT '1',
    asset_type      varchar(255) DEFAULT NULL,
    last_version_id varchar(64) DEFAULT NULL,
    created_on      timestamp    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator_id      varchar(64)  DEFAULT NULL,
    creator         varchar(64)  NOT NULL,
    updated_on      timestamp    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updater_id      varchar(64)  DEFAULT NULL,
    updater         varchar(64)  NOT NULL,
    domain_id       varchar(64)  DEFAULT '0',
    trace_id        varchar(64) DEFAULT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS t_custom_object (
   id varchar(64) NOT NULL,
   project_id      VARCHAR(64)   NOT NULL,
   workspace_id varchar(64)  NULL,
   name varchar(64)  NULL,
   description varchar(255)  NULL,
   object_schema TEXT,
   creator_id varchar(64)  NULL,
   created_on timestamp NULL,
   updated_on timestamp NULL,
   PRIMARY KEY (id)
);

ALTER TABLE t_custom_object ADD COLUMN IF NOT EXISTS workspace_id varchar(64) NULL;

CREATE TABLE IF NOT EXISTS t_workspace_mapping
(
    id                VARCHAR(64)  NOT NULL,
    workspace_id      VARCHAR(64)  NOT NULL,
    mapping_id        VARCHAR(128) NOT NULL,
    extension_content TEXT         NULL,
    source            VARCHAR(32)  NULL,
    PRIMARY KEY (id)
    );

CREATE TABLE IF NOT EXISTS t_ops_tenant_config (
    domain_id varchar(255) NOT NULL,
    project_id varchar(255) DEFAULT NULL,
    log_group_id varchar(255) DEFAULT NULL,
    log_stream_id varchar(255) DEFAULT NULL,
    PRIMARY KEY (domain_id)
);

CREATE TABLE t_history_mapping
(
    history_id            varchar(64)  NOT NULL,
    mapping_id            varchar(64)  NOT NULL,
    app_id                varchar(64)  NOT NULL,
    app_version           varchar(64)           DEFAULT NULL,
    app_type              varchar(32)  NOT NULL,
    app_sub_type          varchar(100)          DEFAULT NULL,
    sub_type              varchar(100)          DEFAULT NULL,
    app_name              varchar(64)           DEFAULT NULL,
    resource_id           varchar(128) NOT NULL,
    resource_type         varchar(32)  NOT NULL,
    resource_name         varchar(1000)         DEFAULT NULL,
    resource_version      varchar(64)           DEFAULT NULL,
    valid                 BOOLEAN      NOT NULL DEFAULT TRUE,
    resource_desc         varchar(2048) DEFAULT NULL,
    created_on            timestamp    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on            timestamp    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reference_type        varchar(64)           DEFAULT 'direct',
    resource_workspace_id varchar(64)           DEFAULT NULL,
    extends               TEXT,
    app_workspace_id      varchar(64)           DEFAULT NULL,
    PRIMARY KEY (history_id)
);

CREATE TABLE t_history_agent
(
    history_id                  varchar(64) NOT NULL,
    agent_id                    varchar(64) NOT NULL,
    project_id                  varchar(64)          DEFAULT NULL,
    name                        varchar(64)          DEFAULT NULL,
    description                 varchar(1024)        DEFAULT NULL,
    icon                        TEXT,
    icon_name                   varchar(64)          DEFAULT NULL,
    model_deployment_id         varchar(128)         DEFAULT NULL,
    model_name                  varchar(128)         DEFAULT NULL,
    model_config                varchar(256)         DEFAULT NULL,
    instructions                text,
    trigger_list                text,
    memory_variables            text,
    prologue                    varchar(512)         DEFAULT NULL,
    suggest_queries             varchar(4096)        DEFAULT NULL,
    additional_questions_config text,
    voice_interaction           text,
    dsl_path                    varchar(256)         DEFAULT NULL,
    ir_path                     varchar(256)         DEFAULT NULL,
    type                        varchar(32)          DEFAULT NULL,
    sub_type                    varchar(50)          DEFAULT NULL,
    status                      varchar(32)          DEFAULT NULL,
    creator                     varchar(64)          DEFAULT NULL,
    creator_id                  varchar(64)          DEFAULT NULL,
    created_on                  timestamp NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on                  timestamp NULL DEFAULT CURRENT_TIMESTAMP,
    published_on                timestamp NULL DEFAULT NULL,
    model_type                  varchar(64)          DEFAULT NULL,
    knowledge_retrieve_policy   TEXT,
    workflow_switch_enabled     BOOLEAN NOT NULL DEFAULT FALSE,
    scheduling_mode             varchar(32) NOT NULL DEFAULT 'ReAct',
    model                       varchar(64)          DEFAULT NULL,
    content_review              TEXT,
    workspace_id                varchar(64)          DEFAULT NULL,
    trace_id                    varchar(64)          DEFAULT NULL,
    safety_barrier              BOOLEAN DEFAULT NULL,
    domain_id                   varchar(64)          DEFAULT NULL,
    agent_variables             TEXT,
    memory_config               TEXT,
    plan_qa_independent         BOOLEAN DEFAULT NULL,
    plan_model                  varchar(64)          DEFAULT NULL,
    plan_model_deployment_id    varchar(128)         DEFAULT NULL,
    plan_model_name             varchar(128)         DEFAULT NULL,
    plan_model_config           varchar(256)         DEFAULT NULL,
    plan_model_type             varchar(64)          DEFAULT NULL,
    deleted                     BOOLEAN NOT NULL DEFAULT false,
    is_shared                   SMALLINT NOT NULL DEFAULT '0',
    is_share                    SMALLINT NOT NULL DEFAULT '0',
    PRIMARY KEY (history_id)
);

CREATE TABLE t_history_release_version
(
    history_id   varchar(64)   NOT NULL,
    id           varchar(64)   NOT NULL,
    version_id   varchar(64)   NOT NULL,
    version_name varchar(64)   NOT NULL,
    version_note varchar(1024) NOT NULL,
    app_id       varchar(64)   NOT NULL,
    app_type     varchar(32)   NOT NULL,
    status       varchar(32)  DEFAULT NULL,
    dsl_path     varchar(256) DEFAULT NULL,
    ir_path      varchar(256) DEFAULT NULL,
    creator      varchar(64)  DEFAULT NULL,
    creator_id   varchar(64)  DEFAULT NULL,
    app_sub_type varchar(100) DEFAULT NULL,
    sub_type     varchar(100) DEFAULT NULL,
    released_on  timestamp NULL DEFAULT CURRENT_TIMESTAMP,
    extend1      text,
    deleted      BOOLEAN NOT NULL DEFAULT false,
    updated_on   timestamp NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (history_id),
    CONSTRAINT unique_index_app_version_id_delete UNIQUE (app_id,version_id,deleted)
);

CREATE TABLE IF NOT EXISTS t_agent_code (
    id VARCHAR ( 64 ) NOT NULL,
    name VARCHAR ( 64 ) DEFAULT NULL,
    description VARCHAR ( 1024 ) DEFAULT NULL,
    icon_name VARCHAR ( 64 ) DEFAULT NULL,
    type VARCHAR ( 32 ) DEFAULT NULL,
    status VARCHAR ( 32 ) DEFAULT NULL,
    builder_sandbox_urn VARCHAR ( 64 ) DEFAULT NULL,
    dev_sandbox_urn VARCHAR ( 64 ) DEFAULT NULL,
    trace_id VARCHAR ( 64 ) DEFAULT NULL,
    project_id VARCHAR ( 64 ) DEFAULT NULL,
    workspace_id VARCHAR ( 64 ) DEFAULT NULL,
    domain_id VARCHAR ( 64 ) DEFAULT NULL,
    user_id VARCHAR ( 64 ) DEFAULT NULL,
    user_name VARCHAR ( 64 ) DEFAULT NULL,
    created_on TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    published_on TIMESTAMP NULL DEFAULT NULL,
    auto_gen_flag SMALLINT DEFAULT NULL
    );

CREATE TABLE IF NOT EXISTS t_agent_code_session (
    id VARCHAR ( 64 ) NOT NULL,
    agent_id VARCHAR ( 64 ) DEFAULT NULL,
    session_id VARCHAR ( 64 ) DEFAULT NULL,
    trace_id VARCHAR ( 64 ) DEFAULT NULL,
    project_id VARCHAR ( 64 ) DEFAULT NULL,
    workspace_id VARCHAR ( 64 ) DEFAULT NULL,
    created_on TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
    );

CREATE TABLE IF NOT EXISTS t_skill (
    skill_id        VARCHAR(64)   NOT NULL,
    domain_id       VARCHAR(64)   NOT NULL,
    name            VARCHAR(64)   NOT NULL,
    icon            TEXT    NOT NULL,
    status          VARCHAR(32)   NOT NULL,
    source          VARCHAR(32)   NOT NULL,
    description     VARCHAR(1024) NOT NULL,
    creator_id      VARCHAR(64)   NOT NULL,
    creator_name    VARCHAR(64)   NOT NULL,
    created_at      BIGINT        NOT NULL DEFAULT 0,
    updated_at      BIGINT        NOT NULL DEFAULT 0,
    latest_version  VARCHAR(64)   NULL,
    used_version    VARCHAR(64)   NULL,
    workspace_id    VARCHAR(64)   NULL,
    project_id      VARCHAR(64)   NULL,
    tag_id          VARCHAR(64)   NULL,
    published_asset VARCHAR(64)   NOT NULL DEFAULT '0',
    PRIMARY KEY (skill_id)
    );

CREATE TABLE IF NOT EXISTS t_skill_version (
    id             VARCHAR(64)   NOT NULL,
    skill_id       VARCHAR(64)   NOT NULL,
    version_name   VARCHAR(32)   NOT NULL,
    used           SMALLINT    NOT NULL DEFAULT 0,
    name           VARCHAR(64)   NOT NULL,
    description    VARCHAR(1024) NOT NULL,
    obs_path       VARCHAR(1024) NOT NULL,
    creator_id     VARCHAR(64)   NOT NULL,
    creator_name   VARCHAR(64)   NOT NULL,
    created_at     BIGINT        NOT NULL DEFAULT 0,
    PRIMARY KEY (id)
    );

-- memory tables
CREATE TABLE IF NOT EXISTS t_memory_repo (
    id varchar(64) NOT NULL,
    name varchar(64) NOT NULL,
    description VARCHAR(1000),
    icon TEXT NULL,
    time_span INTEGER DEFAULT NULL,
    conversation_round INTEGER DEFAULT NULL,
    long_term_memory_strategies TEXT NOT NULL,
    project_id varchar(64) NOT NULL,
    workspace_id varchar(64) NOT NULL,
    domain_id varchar(64) NOT NULL,
    created_user_id varchar(64) NOT NULL,
    created_user_name varchar(255) NOT NULL,
    last_update_user_id varchar(64) DEFAULT NULL,
    last_update_user_name varchar(255) DEFAULT NULL,
    create_time TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

-- model tables
CREATE TABLE IF NOT EXISTS t_sys_model_service_provider (
    ID varchar(40) NOT NULL,
    PROVIDER_NAME varchar(64) NOT NULL,
    PROVIDER_NAME_EN varchar(64) NOT NULL,
    DESCRIPTION varchar(1024) DEFAULT NULL,
    DESCRIPTION_EN varchar(1024) DEFAULT NULL,
    TAGS varchar(1024) DEFAULT NULL,
    PROVIDER_URL varchar(255) DEFAULT NULL,
    CREATED_DATE bigint DEFAULT NULL,
    LAST_UPDATED_DATE bigint DEFAULT NULL,
    LOGO TEXT,
    STATUS varchar(16) DEFAULT NULL,
    priority int DEFAULT '100',
    PRIMARY KEY (ID)
);

CREATE TABLE IF NOT EXISTS t_user_model_service_provider (
    ID varchar(64) NOT NULL,
    PROVIDER_NAME varchar(256) NOT NULL,
    PROVIDER_NAME_EN varchar(256) NOT NULL,
    DESCRIPTION varchar(1024) DEFAULT NULL,
    TAGS varchar(1024) DEFAULT NULL,
    PROVIDER_URL varchar(255) DEFAULT NULL,
    CREATED_DATE bigint DEFAULT NULL,
    LAST_UPDATED_DATE bigint DEFAULT NULL,
    LOGO TEXT,
    STATUS varchar(16) DEFAULT NULL,
    DOMAIN_ID varchar(40) NOT NULL,
    PROJECT_ID varchar(40) NOT NULL,
    WORKSPACE_ID varchar(40) NOT NULL,
    CREATED_BY_USER varchar(64) DEFAULT NULL,
    LAST_UPDATED_BY_USER varchar(64) DEFAULT NULL,
    IDENTITY_ID varchar(40) DEFAULT NULL,
    PRIMARY KEY (ID)
);

CREATE TABLE IF NOT EXISTS t_user_model_service_provider_backup (
    ID varchar(64) NOT NULL,
    PROVIDER_NAME varchar(256) NOT NULL,
    PROVIDER_NAME_EN varchar(256) NOT NULL,
    DESCRIPTION varchar(1024) DEFAULT NULL,
    TAGS varchar(1024) DEFAULT NULL,
    PROVIDER_URL varchar(255) DEFAULT NULL,
    CREATED_DATE bigint DEFAULT NULL,
    LAST_UPDATED_DATE bigint DEFAULT NULL,
    LOGO TEXT,
    STATUS varchar(16) DEFAULT NULL,
    DOMAIN_ID varchar(40) NOT NULL,
    PROJECT_ID varchar(40) NOT NULL,
    WORKSPACE_ID varchar(40) NOT NULL,
    CREATED_BY_USER varchar(64) DEFAULT NULL,
    LAST_UPDATED_BY_USER varchar(64) DEFAULT NULL,
    IDENTITY_ID varchar(40) DEFAULT NULL,
    PRIMARY KEY (ID)
);

CREATE TABLE IF NOT EXISTS t_provider_auth_metadata (
    ID varchar(64) NOT NULL,
    PROVIDER_ID varchar(64) DEFAULT NULL,
    AUTH_TYPE varchar(32) NOT NULL,
    AUTH_INFO varchar(1024) NOT NULL,
    AUTH_URL varchar(256) DEFAULT NULL,
    CREATED_BY_USER varchar(64) DEFAULT NULL,
    CREATED_DATE bigint DEFAULT NULL,
    LAST_UPDATED_DATE bigint DEFAULT NULL,
    DOMAIN_ID varchar(64) NOT NULL,
    PROJECT_ID varchar(64) NOT NULL,
    WORKSPACE_ID varchar(40) NOT NULL,
    IDENTITY_ID varchar(40) DEFAULT NULL,
    PRIMARY KEY (ID)
);

CREATE TABLE IF NOT EXISTS t_provider_auth_metadata_backup (
    ID varchar(64) NOT NULL,
    PROVIDER_ID varchar(64) DEFAULT NULL,
    AUTH_TYPE varchar(32) NOT NULL,
    AUTH_INFO varchar(1024) NOT NULL,
    AUTH_URL varchar(256) DEFAULT NULL,
    CREATED_BY_USER varchar(64) DEFAULT NULL,
    CREATED_DATE bigint DEFAULT NULL,
    LAST_UPDATED_DATE bigint DEFAULT NULL,
    DOMAIN_ID varchar(64) NOT NULL,
    PROJECT_ID varchar(64) NOT NULL,
    WORKSPACE_ID varchar(40) NOT NULL,
    IDENTITY_ID varchar(40) DEFAULT NULL,
    PRIMARY KEY (ID)
);

CREATE TABLE IF NOT EXISTS t_provider_auth_info (
    ID varchar(64) NOT NULL,
    PROVIDER_ID varchar(64) DEFAULT NULL,
    AUTH_METADATA_ID varchar(64) DEFAULT NULL,
    AUTH_TYPE varchar(32) NOT NULL,
    AUTH_INFO TEXT NULL,
    CREATED_BY_USER varchar(64) NOT NULL,
    CREATED_DATE bigint NOT NULL,
    LAST_UPDATED_DATE bigint NOT NULL,
    DOMAIN_ID varchar(64) NOT NULL,
    PROJECT_ID varchar(64) NOT NULL,
    WORKSPACE_ID varchar(40) NOT NULL,
    IDENTITY_ID varchar(40) DEFAULT NULL,
    SYNC_STATUS varchar(40) default 'finish',
    PRIMARY KEY (ID)
);

CREATE TABLE IF NOT EXISTS t_provider_auth_info_backup (
    ID varchar(64) NOT NULL,
    PROVIDER_ID varchar(64) DEFAULT NULL,
    AUTH_METADATA_ID varchar(64) DEFAULT NULL,
    AUTH_TYPE varchar(32) NOT NULL,
    AUTH_INFO TEXT NULL,
    CREATED_BY_USER varchar(64) NOT NULL,
    CREATED_DATE bigint NOT NULL,
    LAST_UPDATED_DATE bigint NOT NULL,
    DOMAIN_ID varchar(64) NOT NULL,
    PROJECT_ID varchar(64) NOT NULL,
    WORKSPACE_ID varchar(40) NOT NULL,
    IDENTITY_ID varchar(40) DEFAULT NULL,
    SYNC_STATUS varchar(40) default 'finish',
    PRIMARY KEY (ID)
);

CREATE TABLE IF NOT EXISTS t_model_service (
    ID varchar(80) NOT NULL,
    PROVIDER_ID varchar(64) DEFAULT NULL,
    SERVICE_NAME varchar(64) NOT NULL,
    SERVICE_KEY varchar(128) NOT NULL,
    MODEL_NAME varchar(64) NOT NULL,
    MODEL_VERSION varchar(64) NOT NULL,
    MODEL_TYPE varchar(32) NOT NULL,
    MODEL_TAGS text,
    MODEL_DESCRIPTION text,
    MODEL_DESCRIPTION_EN text,
    MODEL_DEPLOY_TYPE varchar(32) NOT NULL,
    DOCUMENT_URL varchar(255) DEFAULT NULL,
    MODEL_SIZE float DEFAULT NULL,
    CONTEXT_LENGTH int DEFAULT NULL,
    MODEL_PRIORITY int DEFAULT NULL,
    DOMAIN_ID varchar(64) NOT NULL,
    PROJECT_ID varchar(64) NOT NULL,
    WORKSPACE_ID varchar(40) NOT NULL,
    CREATED_BY_USER varchar(64) DEFAULT 'SYSTEM',
    LAST_UPDATED_BY_USER varchar(64) DEFAULT 'SYSTEM',
    CREATED_DATE bigint DEFAULT NULL,
    LAST_UPDATED_DATE bigint DEFAULT NULL,
    API_URL varchar(256) NOT NULL DEFAULT '',
    IS_REASONING BOOLEAN DEFAULT NULL,
    IS_SUPPORT_CLOSE_REASONING BOOLEAN DEFAULT NULL,
    IS_NETWORK BOOLEAN DEFAULT NULL,
    IS_SUPPORT_FUNCTION BOOLEAN NOT NULL DEFAULT FALSE,
    INTERFACE_PROTOCOL varchar(32) NOT NULL DEFAULT '',
    IS_SUPPORT_STREAM BOOLEAN NOT NULL DEFAULT TRUE,
    AUTH_METADATA_ID varchar(64) DEFAULT NULL,
    SYSTEM_PROMPT varchar(1024) default null,
    PUBLISH_STATUS varchar(16) NOT NULL DEFAULT 'offline',
    THROTTLING_POLICY int default -1,
    LOGO TEXT,
    STATUS varchar(40) DEFAULT NULL,
    IDENTITY_ID varchar(80) DEFAULT NULL,
    IS_PUBLIC BOOLEAN DEFAULT FALSE,
    SYNC_STATUS varchar(40) default 'finish',
    DISCLAIMER  text DEFAULT NULL,
    DISCLAIMER_EN  text DEFAULT NULL,
    PRIMARY KEY (ID)
);

CREATE TABLE IF NOT EXISTS t_model_service_backup (
    ID varchar(80) NOT NULL,
    PROVIDER_ID varchar(64) DEFAULT NULL,
    SERVICE_NAME varchar(64) NOT NULL,
    SERVICE_KEY varchar(128) NOT NULL,
    MODEL_NAME varchar(64) NOT NULL,
    MODEL_VERSION varchar(64) NOT NULL,
    MODEL_TYPE varchar(32) NOT NULL,
    MODEL_TAGS text,
    MODEL_DESCRIPTION text,
    MODEL_DEPLOY_TYPE varchar(32) NOT NULL,
    DOCUMENT_URL varchar(255) DEFAULT NULL,
    MODEL_SIZE float DEFAULT NULL,
    CONTEXT_LENGTH int DEFAULT NULL,
    MODEL_PRIORITY int DEFAULT NULL,
    DOMAIN_ID varchar(64) NOT NULL,
    PROJECT_ID varchar(64) NOT NULL,
    WORKSPACE_ID varchar(40) NOT NULL,
    CREATED_BY_USER varchar(64) DEFAULT 'SYSTEM',
    LAST_UPDATED_BY_USER varchar(64) DEFAULT 'SYSTEM',
    CREATED_DATE bigint DEFAULT NULL,
    LAST_UPDATED_DATE bigint DEFAULT NULL,
    API_URL varchar(256) NOT NULL DEFAULT '',
    IS_REASONING BOOLEAN DEFAULT NULL,
    IS_NETWORK BOOLEAN DEFAULT NULL,
    IS_SUPPORT_FUNCTION BOOLEAN NOT NULL DEFAULT FALSE,
    INTERFACE_PROTOCOL varchar(32) NOT NULL DEFAULT '',
    IS_SUPPORT_STREAM BOOLEAN NOT NULL DEFAULT TRUE,
    AUTH_METADATA_ID varchar(64) DEFAULT NULL,
    SYSTEM_PROMPT varchar(1024) default null,
    PUBLISH_STATUS varchar(16) NOT NULL DEFAULT 'offline',
    THROTTLING_POLICY int default -1,
    LOGO TEXT,
    STATUS varchar(40) DEFAULT NULL,
    IDENTITY_ID varchar(40) DEFAULT NULL,
    IS_PUBLIC BOOLEAN DEFAULT FALSE,
    SYNC_STATUS varchar(40) default 'finish',
    PRIMARY KEY (ID)
);

CREATE TABLE IF NOT EXISTS t_model_service_metadata (
    ID varchar(64) NOT NULL,
    TYPE varchar(16) NOT NULL,
    ATTR_KEY varchar(64) NOT NULL,
    ATTR_VALUE text NOT NULL,
    PRIMARY KEY (ID)
);

CREATE TABLE IF NOT EXISTS t_free_model_service (
    ID varchar(40) NOT NULL,
    PROVIDER_ID varchar(40) DEFAULT NULL,
    SERVICE_NAME varchar(64) NOT NULL,
    SERVICE_KEY varchar(128) NOT NULL,
    MODEL_NAME varchar(64) NOT NULL,
    MODEL_VERSION varchar(64) NOT NULL,
    MODEL_TYPE varchar(32) NOT NULL,
    MODEL_TAGS text,
    MODEL_DESCRIPTION text,
    MODEL_DEPLOY_TYPE varchar(32) NOT NULL,
    DOCUMENT_URL varchar(255) DEFAULT NULL,
    MODEL_SIZE float DEFAULT NULL,
    CONTEXT_LENGTH int DEFAULT NULL,
    MODEL_PRIORITY int DEFAULT NULL,
    DOMAIN_ID varchar(64) NOT NULL,
    PROJECT_ID varchar(64) NOT NULL,
    WORKSPACE_ID varchar(40) NOT NULL,
    CREATED_BY_USER varchar(64) DEFAULT 'SYSTEM',
    LAST_UPDATED_BY_USER varchar(64) DEFAULT 'SYSTEM',
    CREATED_DATE bigint DEFAULT NULL,
    LAST_UPDATED_DATE bigint DEFAULT NULL,
    API_URL varchar(256) NOT NULL DEFAULT '',
    IS_REASONING BOOLEAN DEFAULT NULL,
    IS_NETWORK BOOLEAN DEFAULT NULL,
    IS_SUPPORT_FUNCTION BOOLEAN NOT NULL DEFAULT FALSE,
    INTERFACE_PROTOCOL varchar(32) NOT NULL DEFAULT '',
    IS_SUPPORT_STREAM BOOLEAN NOT NULL DEFAULT TRUE,
    AUTH_METADATA_ID varchar(64) DEFAULT NULL,
    SYSTEM_PROMPT varchar(1024) default null,
    PUBLISH_STATUS varchar(16) NOT NULL DEFAULT 'offline',
    THROTTLING_POLICY int default -1,
    LOGO TEXT,
    STATUS varchar(40) DEFAULT NULL,
    PRIMARY KEY (ID)
);

CREATE TABLE IF NOT EXISTS t_router_strategy (
    ID varchar(64)  NOT NULL,
    STRATEGY_NAME varchar(64)  NOT NULL,
    STRATEGY_TYPE varchar(32),
    STRATEGY_KEY varchar(128)  NOT NULL,
    STRATEGY_TAGS text  NULL,
    STRATEGY_DESCRIPTION text  NULL,
    SERVICE_ID_LIST text  NULL,
    STRATEGY_TIMEOUT int NULL DEFAULT NULL,
    STRATEGY_RETRY_COUNT int NULL DEFAULT NULL,
    SERVICE_COUNT int NULL DEFAULT NULL,
    PREPARE_ATTRIBUTE text  NULL,
    DOMAIN_ID varchar(64)  NOT NULL,
    PROJECT_ID varchar(64)  NOT NULL,
    WORKSPACE_ID varchar(64)  NOT NULL,
    CREATED_BY_USER_NAME varchar(64)  NULL DEFAULT 'SYSTEM',
    LAST_UPDATED_BY_USER_NAME varchar(64)  NULL DEFAULT NULL,
    CREATED_DATE BIGINT NULL DEFAULT NULL,
    LAST_UPDATED_DATE BIGINT NULL DEFAULT NULL,
    TRACE_ID varchar(64)  NOT NULL,
    PRIMARY KEY (ID) 
);

CREATE TABLE IF NOT EXISTS t_router_strategy_backup (
    ID varchar(64)  NOT NULL,
    STRATEGY_NAME varchar(64)  NOT NULL,
    STRATEGY_TYPE varchar(32),
    STRATEGY_KEY varchar(128)  NOT NULL,
    STRATEGY_TAGS text  NULL,
    STRATEGY_DESCRIPTION text  NULL,
    SERVICE_ID_LIST text  NULL,
    STRATEGY_TIMEOUT int NULL DEFAULT NULL,
    STRATEGY_RETRY_COUNT int NULL DEFAULT NULL,
    SERVICE_COUNT int NULL DEFAULT NULL,
    PREPARE_ATTRIBUTE text  NULL,
    DOMAIN_ID varchar(64)  NOT NULL,
    PROJECT_ID varchar(64)  NOT NULL,
    WORKSPACE_ID varchar(64)  NOT NULL,
    CREATED_BY_USER_NAME varchar(64)  NULL DEFAULT 'SYSTEM',
    LAST_UPDATED_BY_USER_NAME varchar(64)  NULL DEFAULT NULL,
    CREATED_DATE BIGINT NULL DEFAULT NULL,
    LAST_UPDATED_DATE BIGINT NULL DEFAULT NULL,
    PRIMARY KEY (ID) 
);

CREATE TABLE IF NOT EXISTS t_api_keys (
    API_KEY_ID VARCHAR(80) NOT NULL,
    API_KEY_NAME VARCHAR(64) NOT NULL,
    API_KEY_VALUE VARCHAR(256) NOT NULL,
    DOMAIN_ID varchar(64)  NOT NULL,
    PROJECT_ID varchar(64)  NOT NULL,
    WORKSPACE_ID varchar(64)  NOT NULL,
    CREATED_BY_USER_NAME varchar(64)  NULL DEFAULT 'SYSTEM',
    LAST_UPDATED_BY_USER_NAME varchar(64)  NULL DEFAULT NULL,
    CREATED_DATE BIGINT NULL DEFAULT NULL,
    DESCRIPTION VARCHAR(1024) NOT NULL,
    USER_ID VARCHAR(64) NOT NULL,
    PRIMARY KEY (API_KEY_ID) 
);

CREATE TABLE IF NOT EXISTS t_provider_auth_bound_records(
    ID varchar(64) NOT NULL,
    PROVIDER_AUTH_ID varchar(64) NOT NULL,
    DOMAIN_ID varchar(64) NOT NULL,
    PROVIDER_ID varchar(64) DEFAULT NULL,
    CREATED_BY_USER varchar(64) DEFAULT 'SYSTEM',
    CREATED_DATE bigint DEFAULT NULL,
    PRIMARY KEY (ID)
);

CREATE TABLE IF NOT EXISTS t_user_model_subscribe_settings(
    ID varchar(64) NOT NULL,
    DOMAIN_ID varchar(64) NOT NULL,
    PROJECT_ID varchar(64)  DEFAULT NULL,
    IS_AUTO_SUBSCRIBE_NEW_MODEL SMALLINT DEFAULT 0,
    CREATED_DATE bigint DEFAULT NULL,
    LAST_UPDATED_DATE bigint DEFAULT NULL,
    PRIMARY KEY (ID)
);

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
CREATE TABLE IF NOT EXISTS t_pe_task
(
    id            varchar(60) NOT NULL,
    name          varchar(512) NOT NULL,
    description   text NULL,
    iteration_num int NOT NULL DEFAULT 0,
    project_id    varchar(60) NULL DEFAULT NULL,
    industry_id   varchar(36) NULL,
    creator       varchar(36) NOT NULL,
    updater       varchar(36) NULL DEFAULT NULL,
    created_on    timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on    timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    workspace_id  varchar(64) NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS t_pe_tag
(
    id         varchar(36)  NOT NULL,
    name       varchar(128) NOT NULL,
    name_en    varchar(128) NOT NULL,
    created_on timestamp NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on timestamp NULL DEFAULT CURRENT_TIMESTAMP,
    workspace_id varchar(64) NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS t_pe_evaluation_task
(
    id               varchar(36)  NOT NULL,
    name             varchar(255) NOT NULL,
    method           varchar(36)  NOT NULL,
    task_id          varchar(36)  NOT NULL,
    test_set_id      varchar(255) NOT NULL,
    description      text NULL,
    created_on       timestamp NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on       timestamp NULL DEFAULT CURRENT_TIMESTAMP,
    status           varchar(255) NULL DEFAULT NULL,
    creator          varchar(36)  NOT NULL,
    prompts          json NULL,
    regular_expression VARCHAR(64) NULL,
    eval_model_config TEXT NULL,
    workspace_id     varchar(64) NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS t_pe_evaluation_result
(
    id                 varchar(36) NOT NULL,
    evaluation_task_id varchar(36) NOT NULL,
    prompt_id          varchar(36) NOT NULL,
    test_num           int                                                          NOT NULL,
    generate_result    text NOT NULL,
    eval_result        json                                                         NOT NULL,
    eval_failed_reason varchar(255) DEFAULT NULL,
    workspace_id       varchar(64) NULL,
    PRIMARY KEY (id),
    CONSTRAINT pe_pid_etid_tn_ux UNIQUE (evaluation_task_id,prompt_id,test_num),
    CONSTRAINT pe_eval_task_id_fk FOREIGN KEY (evaluation_task_id) REFERENCES t_pe_evaluation_task (id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

CREATE INDEX IF NOT EXISTS pe_eval_task_id_fk ON t_pe_evaluation_result(evaluation_task_id);

CREATE TABLE IF NOT EXISTS t_pe_prompt
(
    id           varchar(36) NOT NULL,
    name         varchar(255) NULL DEFAULT NULL,
    model        varchar(128) NOT NULL,
    model_config json NULL,
    task_id      varchar(600) NULL DEFAULT NULL,
    source       varchar(36) NOT NULL,
    type         SMALLINT NOT NULL,
    question     varchar(4000) NOT NULL,
    answer       text NULL,
    variables    json NULL,
    manual_score SMALLINT NULL DEFAULT NULL,
    creator      varchar(36) NOT NULL,
    updater      varchar(36) NULL DEFAULT NULL,
    created_on   timestamp NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on   timestamp NULL DEFAULT CURRENT_TIMESTAMP,
    workspace_id varchar(64) NULL,
    file_id      varchar(64) NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS t_history_prompt (
    id          VARCHAR(36) NOT NULL,
    name        VARCHAR(255) NULL DEFAULT NULL,
    content     TEXT NULL,
    source      VARCHAR(36) NULL DEFAULT NULL,
    variables   TEXT NULL,
    pt_type     VARCHAR(36) NULL DEFAULT NULL,
    project_id  VARCHAR(36) NULL DEFAULT NULL,
    industry_id VARCHAR(36) NULL DEFAULT NULL,
    description VARCHAR(255) NULL DEFAULT NULL,
    creator     VARCHAR(36) NOT NULL,
    updater     VARCHAR(36) NULL DEFAULT NULL,
    created_on  TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on  TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    workspace_id VARCHAR(64) NULL DEFAULT NULL,
    domain_id   VARCHAR(64) NULL DEFAULT NULL,
    tag_ids     VARCHAR(1024) NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS t_pe_prompt_template
(
    id           varchar(36) NOT NULL,
    question     varchar(4000) NULL DEFAULT NULL,
    answer       text NULL,
    model        varchar(255) NULL DEFAULT NULL,
    model_config json NULL,
    variables    json NULL,
    creator      varchar(36) NOT NULL,
    created_on   timestamp NULL DEFAULT NULL,
    workspace_id varchar(64) NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS t_pe_variable
(
    id             varchar(36)  NOT NULL,
    key            varchar(36)         NOT NULL,
    name           varchar(255) NOT NULL,
    pe_task_id     varchar(36)  NOT NULL,
    relation_count SMALLINT                                                       NOT NULL,
    create_time    bigint                                                        NOT NULL,
    workspace_id   varchar(64) NULL,
    PRIMARY KEY (id),
    CONSTRAINT t_pe_variable_fk_task FOREIGN KEY (pe_task_id) REFERENCES t_pe_task (id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

CREATE TABLE IF NOT EXISTS t_dataset
(
    dataset_id   varchar(64) NOT NULL,
    dataset_name varchar(128) NOT NULL,
    dataset_type varchar(128) NOT NULL,
    project_id   varchar(64) NOT NULL,
    obs_path     varchar(255) NOT NULL,
    create_time  TIMESTAMP NOT NULL,
    update_time  TIMESTAMP NOT NULL,
    description  varchar(512) NULL DEFAULT '',
    workspace_id varchar(64) NULL,
    PRIMARY KEY (dataset_id)
);

CREATE TABLE IF NOT EXISTS t_job_instance
(
    id          varchar(36) NOT NULL,
    name        varchar(128) NULL DEFAULT NULL,
    created_on  timestamp   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on  timestamp NULL DEFAULT NULL,
    job_spec_id varchar(36) NOT NULL,
    context     TEXT NOT NULL,
    retry_time  int NOT NULL,
    status      varchar(16) NOT NULL,
    started_on  timestamp NULL DEFAULT NULL,
    ended_on    timestamp NULL DEFAULT NULL,
    handler_id  varchar(64) NULL DEFAULT NULL,
    account_id  varchar(36) NOT NULL,
    workspace_id varchar(64) NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS t_mapping_pe_task_tag
(
    task_id     varchar(36) NOT NULL,
    tag_id      varchar(36) NOT NULL,
    workspace_id varchar(64) NULL,
    CONSTRAINT     t_mapping_pe_task_tag_fk_tag FOREIGN KEY (tag_id) REFERENCES t_pe_tag (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT     t_mapping_pe_task_tag_fk_task FOREIGN KEY (task_id) REFERENCES t_pe_task (id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

CREATE TABLE IF NOT EXISTS t_job_spec
(
    id         varchar(36) NOT NULL,
    created_on timestamp   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on timestamp NULL DEFAULT NULL,
    name       varchar(32) NOT NULL,
    type       varchar(32) NOT NULL,
    workspace_id varchar(64) NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS t_pe_industry
(
    id          varchar(36)  not NULL,
    name        VARCHAR(128) NOT NULL,
    name_en     varchar(128) NOT NULL,
    description TEXT,
    library_type VARCHAR(50),
    created_on  timestamp NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on  timestamp NULL DEFAULT CURRENT_TIMESTAMP,
    workspace_id varchar(64) NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS t_pe_prompt_library
(
    id          varchar(36) NOT NULL,
    name        varchar(255) NULL DEFAULT NULL,
    content     TEXT NULL DEFAULT NULL,
    source      varchar(36) NULL DEFAULT NULL,
    variables   TEXT NULL DEFAULT NULL,
    pt_type     varchar(36) NULL DEFAULT NULL,
    project_id  varchar(36) NULL DEFAULT NULL,
    industry_id varchar(36) NULL,
    description varchar(255) NULL DEFAULT NULL,
    creator     varchar(36) NOT NULL,
    updater     varchar(36) NULL DEFAULT NULL,
    created_on  timestamp NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on  timestamp NULL DEFAULT CURRENT_TIMESTAMP,
    workspace_id varchar(64) NULL,
    domain_id   varchar(64) NULL,
    is_share    SMALLINT NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    CONSTRAINT fk_pe_prompt_library_industry_id FOREIGN KEY (industry_id) REFERENCES t_pe_industry(id)
);

CREATE TABLE IF NOT EXISTS t_mapping_pe_template_tag
(
    template_id varchar(36) NOT NULL,
    tag_id      varchar(36) NOT NULL,
    workspace_id varchar(64) NULL,
    CONSTRAINT     fk_tag_id FOREIGN KEY (tag_id) REFERENCES t_pe_tag (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT     fk_template_id FOREIGN KEY (template_id) REFERENCES t_pe_prompt_library (id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

CREATE TABLE IF NOT EXISTS t_pe_optimization_task (
    id              VARCHAR ( 36 ) NOT NULL,
    project_id      VARCHAR ( 36 ) NOT NULL,
    task_id         VARCHAR ( 36 ) NOT NULL,
    name            VARCHAR ( 255 ) NOT NULL,
    description     TEXT,
    jiuwen_task_id  VARCHAR ( 128 ) NOT NULL DEFAULT '',
    prompts         json NULL,
    test_set_id     VARCHAR ( 36 ) NOT NULL,
    model_config    TEXT,
    assistant_config TEXT,
    num_iter        INT NOT NULL DEFAULT 3,
    best_prompt     TEXT DEFAULT NULL,
    error_msg       TEXT DEFAULT NULL,
    progress_rate   FLOAT DEFAULT 0,
    status          VARCHAR ( 255 ) DEFAULT NULL,
    creator         VARCHAR ( 36 ) NOT NULL,
    created_on      TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    running_on      TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on      TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    type            VARCHAR(16) NOT NULL DEFAULT 'expansion',
    workspace_id    varchar(64) NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS t_pe_op_task (
    id              VARCHAR(64) NOT NULL,
    jiuwen_task_id  VARCHAR(128) NULL,
    name            VARCHAR(64) NOT NULL,
    "desc"            TEXT NOT NULL,
    pt_type         VARCHAR(32) NULL,
    pt_text         TEXT NULL,
    pt_vars         TEXT NULL,
    exec_time       TIMESTAMP NULL,
    pt_model        VARCHAR(255) NULL,
    exec_object     VARCHAR(255) NULL,
    max_iter_num    INT NULL,
    target_acc      VARCHAR(32) NULL,
    show_case_num   INT NULL,
    target_type     VARCHAR(32) NULL,
    progress_rate   DOUBLE PRECISION NULL DEFAULT NULL,
    message         TEXT NULL,
    score_standard  TEXT NULL,
    back_knowledge  TEXT NULL,
    status          SMALLINT NULL,
    project_id      VARCHAR(64) NULL,
    workspace_id    VARCHAR(64) NULL,
    creator         VARCHAR(64) NULL DEFAULT NULL,
    creator_id      VARCHAR(64) NULL DEFAULT NULL,
    created_time    TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_time    TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    prompt_id       VARCHAR(64) NULL DEFAULT NULL,
    domain_id       varchar(64) NULL,
    algorithm       varchar(32) NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS t_history_op_task (
    id              VARCHAR(64)  NOT NULL,
    jiuwen_task_id  VARCHAR(128) NULL,
    name            VARCHAR(64)  NOT NULL,
    "desc"            TEXT         NOT NULL,
    pt_type         VARCHAR(32)  NULL,
    pt_text         TEXT         NULL,
    pt_vars         TEXT         NULL,
    exec_time       TIMESTAMP    NULL,
    pt_model        VARCHAR(255) NULL,
    exec_object     VARCHAR(255) NULL,
    max_iter_num    INT          NULL,
    target_acc      VARCHAR(32)  NULL,
    show_case_num   INT          NULL,
    target_type     VARCHAR(32)  NULL,
    progress_rate   DOUBLE PRECISION       NULL     DEFAULT NULL,
    message         TEXT         NULL,
    score_standard  TEXT         NULL,
    back_knowledge  TEXT         NULL,
    status          SMALLINT      NULL,
    project_id      VARCHAR(64)  NULL,
    workspace_id    VARCHAR(64)  NULL,
    creator         VARCHAR(64)  NULL,
    creator_id      VARCHAR(64)  NULL,
    created_time    TIMESTAMP    NULL     DEFAULT CURRENT_TIMESTAMP,
    updated_time    TIMESTAMP    NULL     DEFAULT CURRENT_TIMESTAMP,
    prompt_id       VARCHAR(64)  NULL,
    domain_id       VARCHAR(64)  NULL,
    algorithm       varchar(32)  NULL,
    PRIMARY KEY (id)
);

-- tool tables
CREATE TABLE IF NOT EXISTS t_mcp (
    server_id     VARCHAR(64) NOT NULL,
    project_id    VARCHAR(64) NOT NULL,
    server_name   VARCHAR(64) NOT NULL,
    server_name_en VARCHAR(64) NULL,
    server_desc   VARCHAR(1000) NOT NULL,
    icon          TEXT NULL,
    icon_name     VARCHAR(64)   NULL,
    tools         TEXT NOT NULL,
    visibility    VARCHAR(32) NOT NULL DEFAULT 'project',
    url           VARCHAR(256) NOT NULL,
    auth          VARCHAR(4096) NULL,
    type          VARCHAR(32) NOT NULL,
    category      VARCHAR(32) NULL,
    creator       VARCHAR(64) NOT NULL,
    creator_id    VARCHAR(64) NOT NULL,
    created_on    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (server_id)
);

CREATE TABLE IF NOT EXISTS t_mcp_config(
    id          VARCHAR(64) NOT NULL,
    server_id   VARCHAR(64) NOT NULL,
    project_id  VARCHAR(64) NOT NULL,
    auth_keys   VARCHAR(4096) NOT NULL,
    creator_id  VARCHAR(64) NOT NULL,
    created_on  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(id)
);

CREATE TABLE ws_mcp_server_def
(
    id                      varchar(64)       not null primary key,
    server_code             varchar(255)      null,
    icon                    TEXT          null,
    name                    varchar(255)      null,
    name_en                 varchar(255)      null,
    description             varchar(2048)     null,
    description_en          varchar(2048)     null,
    readme                  TEXT          null,
    server_config           TEXT          null,
    tools                   TEXT          null,
    type                    varchar(64)       null,
    org_type                varchar(64)       null,
    deleted                 BOOLEAN default false null,
    tenant_id               varchar(64)       not null,
    dept_code               varchar(64)       null,
    created_date            timestamp         not null DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id      varchar(64)       null,
    last_updated_date       timestamp         not null DEFAULT CURRENT_TIMESTAMP,
    last_updated_by_user_id varchar(64)       null,
    url                     varchar(255)      null,
    install_times           bigint  default 0 null,
    view_times              bigint  default 0 null,
    category                VARCHAR(36) NULL,
    CONSTRAINT fk_ws_mcp_category_industry_id FOREIGN KEY (category) REFERENCES t_pe_industry(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

CREATE TABLE ws_mcp_service_def
(
    id                        varchar(64)       not null primary key,
    name                      varchar(255)      null,
    name_en                   varchar(255)      null,
    description               varchar(2048)     null,
    description_en            varchar(2048)     null,
    fc_instance_url           varchar(255)      null,
    fc_instance_id            varchar(255)       null,
    fc_instance_status        varchar(64)       null,
    fc_region                 varchar(64)       null,
    apig_group_id             varchar(64)       null,
    apig_instance_id          varchar(255)       null,
    deleted                   BOOLEAN default false null,
    tenant_id                 varchar(64)       null,
    dept_code                 varchar(64)       null,
    created_date              timestamp         not null DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id        varchar(64)       null,
    last_updated_date         timestamp         not null DEFAULT CURRENT_TIMESTAMP,
    last_updated_by_user_id   varchar(64)       null,
    readme                    TEXT          null,
    server_config             TEXT          null,
    tools                     TEXT          null,
    deploy_type               varchar(64)       null,
    org_type                  varchar(64)       null,
    function_name             varchar(128)      null,
    server_id                 varchar(64)       null,
    function_urn              varchar(256)      null,
    function_application_name varchar(118)      null,
    domain_id                 varchar(64)       null,
    unique_code               varchar(64)       null,
    project_id                varchar(64) null,
    workspace_id              varchar(64)       null,
    icon                      TEXT          null,
    node_type                 varchar(64)       NOT NULL DEFAULT 'Mcp',
    auth_type                 varchar(64)       null,
    trace_id                  varchar(64)       null,
    visibility                VARCHAR(64) DEFAULT 'workspace' CHECK (visibility IN ('global','workspace','user')),
    auth_info                 TEXT NULL,
    third_resource            varchar(32)       null,
    third_id                  varchar(128)      null,
    third_version_id          varchar(128)      null,
    fail_reason               VARCHAR(500) DEFAULT NULL,
    is_share                  SMALLINT NOT NULL DEFAULT 0
);

CREATE TABLE ws_mcp_server_rating
(
    rating_id    int primary key,
    server_id    varchar(32) not null,
    tenant_id    varchar(32) not null,
    score        SMALLINT     not null,
    created_date TIMESTAMP    not null,
    updated_date TIMESTAMP    null,
    constraint server_id unique (server_id, tenant_id)
);

CREATE TABLE IF NOT EXISTS t_tool (
    tool_id           VARCHAR(84)   NOT NULL,
    project_id        VARCHAR(64) NOT NULL,
    tool_display_name VARCHAR(64)   NOT NULL,
    tool_chinese_name VARCHAR(64)   NULL,
    tool_desc         VARCHAR(600)  NOT NULL,
    icon              TEXT    NULL,
    icon_name         VARCHAR(64)   NULL,
    visibility        VARCHAR(32)   NOT NULL DEFAULT 'project',
    request_info      TEXT    NULL,
    auth_info         TEXT    NULL,
    input_schema      TEXT    NULL,
    output_schema     TEXT    NULL,
    intf_type         TEXT    NULL,
    type              VARCHAR(32)   NOT NULL,
    metadata          VARCHAR(4096) NULL,
    creator           VARCHAR(64)   NULL,
    creator_id        VARCHAR(64) NULL,
    created_on        TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on        TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    test_status       TEXT    NULL,
    last_version_id   VARCHAR(64)   NULL,
    customize_node    SMALLINT    NULL,
    published         SMALLINT    NULL,
    call_mode         VARCHAR(16)   DEFAULT 'api',
    domain_id         varchar(64)   NULL,
    is_input_list     TEXT    NULL,
    is_output_list    TEXT    NULL,
    auth_required     BOOLEAN    NULL DEFAULT FALSE,
    workspace_id      varchar(64)   NULL,
    trace_id          varchar(64)   NULL,
    is_free           SMALLINT    DEFAULT 0,
    label             VARCHAR(32)   NULL DEFAULT 'normal',
    is_share          SMALLINT    NOT NULL DEFAULT 0,
    category          VARCHAR(36) NULL,
    PRIMARY KEY (tool_id),
    CONSTRAINT fk_t_tool_category_industry_id FOREIGN KEY (category) REFERENCES t_pe_industry(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

CREATE TABLE IF NOT EXISTS t_history_tool (
    history_id        VARCHAR(64)   NOT NULL DEFAULT '',
    tool_id           VARCHAR(64)   NOT NULL,
    project_id        VARCHAR(64)   NOT NULL,
    tool_display_name VARCHAR(64)   NOT NULL,
    tool_chinese_name VARCHAR(64)   NULL,
    tool_desc         VARCHAR(600)  NOT NULL,
    icon              TEXT    NULL,
    icon_name         VARCHAR(64)   NULL,
    visibility        VARCHAR(32)   NOT NULL DEFAULT 'project',
    request_info      TEXT    NULL,
    auth_info         TEXT    NULL,
    input_schema      TEXT    NULL,
    output_schema     TEXT    NULL,
    intf_type         TEXT    NULL,
    type              VARCHAR(32)   NOT NULL,
    metadata          VARCHAR(4096) NULL,
    creator           VARCHAR(64)   NULL,
    creator_id        VARCHAR(64)   NULL,
    created_on        TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on        TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    test_status       TEXT    NULL,
    last_version_id   VARCHAR(64)   NULL,
    customize_node    SMALLINT    NULL DEFAULT NULL,
    is_input_list     TEXT    NULL,
    is_output_list    TEXT    NULL,
    auth_required     BOOLEAN    NULL DEFAULT FALSE,
    workspace_id      VARCHAR(64)   NULL,
    trace_id          VARCHAR(64)   NULL,
    published         SMALLINT    NULL,
    call_mode         VARCHAR(16)   NULL DEFAULT 'api',
    is_free           SMALLINT    NULL DEFAULT 0,
    domain_id         VARCHAR(64)   NULL,
    label             VARCHAR(32)   NULL DEFAULT 'normal',
    is_share          SMALLINT    NOT NULL DEFAULT 0,
    category          VARCHAR(36) NULL,
    PRIMARY KEY (history_id)
);

CREATE TABLE IF NOT EXISTS t_mapping_agent_tool
(
    agent_id     VARCHAR(64) NOT NULL,
    tool_id      VARCHAR(64) NOT NULL,
    project_id   VARCHAR(64) NOT NULL,
    resident     SMALLINT NOT NULL DEFAULT 0,
    created_on   TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_on   TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (agent_id, tool_id, project_id)
);

CREATE TABLE IF NOT EXISTS t_mapping_tool_function
(
    id          varchar(36)  NOT NULL,
    function_id varchar(64)  NOT NULL,
    plugin_id   varchar(64)  NOT NULL,
    tool_id     varchar(64)  NOT NULL,
    created_on  timestamp    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator_id  varchar(64)  DEFAULT NULL,
    updated_on  timestamp    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updater_id  varchar(64)  DEFAULT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS t_task (
                                        id                VARCHAR(64)     NOT NULL,
    name              VARCHAR(64)     NOT NULL,
    conversation_id   VARCHAR(64)     NULL,
    user_id           VARCHAR(64)     NULL,
    project_id        VARCHAR(64)     NULL,
    domain_id         VARCHAR(64)     NULL,
    workspace_id      VARCHAR(64)     NULL,
    type              VARCHAR(32)     NULL,
    mode              VARCHAR(32)     NULL,
    app_id            VARCHAR(64)     NULL,
    app_version       VARCHAR(128)    NULL,
    is_published      BOOLEAN      NULL,
    status            VARCHAR(32)     NULL,
    inputs            TEXT      NULL,
    outputs           TEXT      NULL,
    timeout           INTEGER         NULL,
    message           VARCHAR(2048)   NULL,
    create_time       TIMESTAMP       NOT NULL,
    start_time        TIMESTAMP       NULL,
    update_time       TIMESTAMP       NULL,
    finish_time       TIMESTAMP       NULL,
    PRIMARY KEY (id)
    );
CREATE INDEX IF NOT EXISTS idx_t_history_mapping_app_id ON t_history_mapping (app_id);
CREATE INDEX IF NOT EXISTS idx_t_history_mapping_resource_id ON t_history_mapping (resource_id);
CREATE INDEX IF NOT EXISTS idx_t_history_mapping_resource_version ON t_history_mapping (resource_version);
CREATE INDEX IF NOT EXISTS idx_t_history_mapping_app_version ON t_history_mapping (app_version);
CREATE INDEX IF NOT EXISTS index_t_agent_history_agent_id ON t_history_agent (agent_id);
CREATE INDEX IF NOT EXISTS IDX_T_AGENT_HISTORY_PROJECT_AGENT ON t_history_agent (project_id,agent_id,workspace_id);


-- Extracted inline indexes
CREATE UNIQUE INDEX IF NOT EXISTS t_common_license_record_id_uindex ON t_common_license_record (id);
CREATE UNIQUE INDEX IF NOT EXISTS t_common_reource_inst_id_uindex ON t_common_reource_inst (resource_id);
CREATE INDEX IF NOT EXISTS index_t_agent_agent_id ON t_agent (agent_id);
CREATE INDEX IF NOT EXISTS IDX_T_AGENT_PROJECT_AGENT ON t_agent (project_id,agent_id);
CREATE INDEX IF NOT EXISTS index_t_agent_version_version_id ON t_agent_version (version_id);
CREATE INDEX IF NOT EXISTS idx_t_agent_workflow_created_at ON t_agent_workflow (created_at);
CREATE INDEX IF NOT EXISTS idx_t_agent_workflow_updated_at ON t_agent_workflow (updated_at);
CREATE INDEX IF NOT EXISTS idx_t_agent_workflow_published_at ON t_agent_workflow (published_at);
CREATE INDEX IF NOT EXISTS idx_t_history_agent_workflow_updated_at ON t_history_agent_workflow (updated_at);
CREATE INDEX IF NOT EXISTS idx_t_mapping_app_id ON t_mapping (app_id);
CREATE INDEX IF NOT EXISTS idx_t_mapping_resource_id ON t_mapping (resource_id);
CREATE INDEX IF NOT EXISTS idx_t_mapping_resource_version ON t_mapping (resource_version);
CREATE INDEX IF NOT EXISTS idx_t_mapping_app_version ON t_mapping (app_version);
CREATE UNIQUE INDEX IF NOT EXISTS unique_index_app_version_id ON t_release_version (app_id, version_id);
CREATE INDEX IF NOT EXISTS index_t_release_channel_id ON t_release_channel (id);
CREATE INDEX IF NOT EXISTS idx_t_release_channel_app_version ON t_release_channel (app_id, version_id);
CREATE INDEX IF NOT EXISTS event_time ON t_analytics_event (event_time);
CREATE INDEX IF NOT EXISTS event_date ON t_analytics_event (event_date);
CREATE INDEX IF NOT EXISTS app_id ON t_analytics_event (app_id);
CREATE INDEX IF NOT EXISTS idx_t_complex_intent_domain ON t_complex_intent (domain_id);
CREATE INDEX IF NOT EXISTS idx_t_complex_intent_branch_intent ON t_complex_intent_branch (intent_id);
CREATE INDEX IF NOT EXISTS idx_t_credential_updated_on ON t_credential (updated_on);
CREATE INDEX IF NOT EXISTS idx_t_credential_domain_id ON t_credential (domain_id);
CREATE INDEX IF NOT EXISTS idx_t_credential_user_id_workspace_id_resource_id ON t_credential (resource_id, user_id, workspace_id);
CREATE INDEX IF NOT EXISTS index_t_workspace_id ON t_workspace (id);
CREATE INDEX IF NOT EXISTS idx_t_workspace_domain ON t_workspace (domain_id);
CREATE INDEX IF NOT EXISTS idx_member_id ON t_workspace_member (member_id);
CREATE INDEX IF NOT EXISTS idx_member_workspace_status ON t_workspace_member (member_id, workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_t_workspace_member_domain ON t_workspace_member (domain_id);
CREATE INDEX IF NOT EXISTS idx_t_dependency_domain ON t_dependency (domain_id);
CREATE INDEX IF NOT EXISTS idx_t_function_domain ON t_function (domain_id);
CREATE INDEX IF NOT EXISTS t_map_function_id_index ON t_function_dependency_map (function_id);
CREATE INDEX IF NOT EXISTS idx_create_time ON t_task (create_time);
CREATE INDEX IF NOT EXISTS idx_status_time ON t_task (status, create_time);
CREATE INDEX IF NOT EXISTS idx_finish_time ON t_task (finish_time);
CREATE INDEX IF NOT EXISTS index_t_task_domain ON t_task (domain_id);
CREATE INDEX IF NOT EXISTS idx_t_environment_manager_info_domain ON t_environment_manager_info (domain_id);
CREATE INDEX IF NOT EXISTS idx_t_environment_variable_info_env_id ON t_environment_variable_info (env_id);
CREATE INDEX IF NOT EXISTS idx_project_visibility ON t_structured_message (project_id, visibility);
CREATE INDEX IF NOT EXISTS idx_workspace ON t_structured_message (workspace_id);
CREATE INDEX IF NOT EXISTS idx_category ON t_structured_message (category);
CREATE INDEX IF NOT EXISTS index_t_share_resource_domain ON t_share_resource (tenant_id);
CREATE INDEX IF NOT EXISTS idx_t_share_resource_resource_type ON t_share_resource (resource_type);
CREATE INDEX IF NOT EXISTS idx_t_share_resource_resource_name ON t_share_resource (resource_name);
CREATE INDEX IF NOT EXISTS idx_t_share_resource_update_time ON t_share_resource (update_time);
CREATE INDEX IF NOT EXISTS idx_t_share_resource_project_workspace_resource ON t_share_resource (project_id, workspace_id, resource_id);
CREATE INDEX IF NOT EXISTS idx_username ON t_users (username);
CREATE INDEX IF NOT EXISTS idx_external_id ON t_users (external_id);
CREATE INDEX IF NOT EXISTS idx_domain_project ON t_users (domain_id, project_id);
CREATE INDEX IF NOT EXISTS idx_created_time ON t_users (created_time);
CREATE INDEX IF NOT EXISTS idx_session_id ON t_sessions (session_id);
CREATE INDEX IF NOT EXISTS idx_session_user_id ON t_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_session_username ON t_sessions (username);
CREATE INDEX IF NOT EXISTS idx_session_status ON t_sessions (status);
CREATE INDEX IF NOT EXISTS idx_session_login_time ON t_sessions (login_time);
CREATE INDEX IF NOT EXISTS idx_session_expire_time ON t_sessions (expire_time);
CREATE INDEX IF NOT EXISTS idx_session_domain_project ON t_sessions (domain_id, project_id);
CREATE INDEX IF NOT EXISTS idx_mapping_id ON t_workspace_mapping (mapping_id);
CREATE INDEX IF NOT EXISTS index_t_agent_id ON t_agent_code ( id );
CREATE INDEX IF NOT EXISTS index_t_agent_project_agent ON t_agent_code ( project_id, workspace_id, id );
CREATE INDEX IF NOT EXISTS idx_t_skill_domain_id ON t_skill (domain_id);
CREATE INDEX IF NOT EXISTS idx_t_skill_version_skill_id ON t_skill_version (skill_id);
CREATE INDEX IF NOT EXISTS usp_idx_PROJECT_AND_WORKSPACE ON t_user_model_service_provider (PROJECT_ID,WORKSPACE_ID);
CREATE INDEX IF NOT EXISTS PB_USP_IDX_PROJECT_AND_WORKSPACE ON t_user_model_service_provider_backup (PROJECT_ID,WORKSPACE_ID);
CREATE INDEX IF NOT EXISTS idx_auth_metadata_PROVIDER_ID ON t_provider_auth_metadata (PROVIDER_ID);
CREATE INDEX IF NOT EXISTS pm_idx_PROJECT_AND_WORKSPACE ON t_provider_auth_metadata (PROJECT_ID,WORKSPACE_ID);
CREATE INDEX IF NOT EXISTS AMB_IDX_PROVIDER_ID ON t_provider_auth_metadata_backup (PROVIDER_ID);
CREATE INDEX IF NOT EXISTS AMB_PM_IDX_PROJECT_AND_WORKSPACE ON t_provider_auth_metadata_backup (PROJECT_ID,WORKSPACE_ID);
CREATE UNIQUE INDEX IF NOT EXISTS uq_idx_PROJECT_AND_WORKSPACE ON t_provider_auth_info (PROJECT_ID,WORKSPACE_ID,AUTH_METADATA_ID);
CREATE INDEX IF NOT EXISTS idx_PROVIDER_ID ON t_provider_auth_info (PROVIDER_ID);
CREATE INDEX IF NOT EXISTS AUTH_SYNC_STATUS_IDX ON t_provider_auth_info (SYNC_STATUS);
CREATE UNIQUE INDEX IF NOT EXISTS AIB_UQ_IDX_PROJECT_AND_WORKSPACE ON t_provider_auth_info_backup (PROJECT_ID,WORKSPACE_ID,AUTH_METADATA_ID);
CREATE INDEX IF NOT EXISTS AIB_IDX_PROVIDER_ID ON t_provider_auth_info_backup (PROVIDER_ID);
CREATE INDEX IF NOT EXISTS SERVICE_NAME_IDX ON t_model_service (PROJECT_ID,WORKSPACE_ID,SERVICE_NAME);
CREATE INDEX IF NOT EXISTS PROVIDER_ID_INDEX ON t_model_service (PROVIDER_ID);
CREATE INDEX IF NOT EXISTS PUBLIC_TAG_IDX ON t_model_service (IS_PUBLIC);
CREATE INDEX IF NOT EXISTS MODEL_SYNC_STATUS_IDX ON t_model_service (SYNC_STATUS);
CREATE INDEX IF NOT EXISTS MSB_SERVICE_NAME_IDX ON t_model_service_backup (PROJECT_ID,WORKSPACE_ID,SERVICE_NAME);
CREATE INDEX IF NOT EXISTS MSB_PROVIDER_ID_INDEX ON t_model_service_backup (PROVIDER_ID);
CREATE INDEX IF NOT EXISTS PW_ID_INDEX ON t_router_strategy (PROJECT_ID, WORKSPACE_ID);
CREATE INDEX IF NOT EXISTS SB_PW_ID_INDEX ON t_router_strategy_backup (PROJECT_ID, WORKSPACE_ID);
CREATE INDEX IF NOT EXISTS AK_PW_ID_INDEX ON t_api_keys (PROJECT_ID, WORKSPACE_ID);
CREATE UNIQUE INDEX IF NOT EXISTS uniq_t_pe_task_name ON t_pe_task (name, project_id);
CREATE INDEX IF NOT EXISTS idx_creator ON t_pe_task (creator);
CREATE INDEX IF NOT EXISTS idx_updater ON t_pe_task (updater);
CREATE INDEX IF NOT EXISTS idx_project_id ON t_pe_task (project_id);
CREATE UNIQUE INDEX IF NOT EXISTS uniq_t_pe_tag_name ON t_pe_tag (name);
CREATE INDEX IF NOT EXISTS pe_evaluation_task_id ON t_pe_evaluation_task (task_id);
CREATE INDEX IF NOT EXISTS pe_result_test_id ON t_pe_evaluation_result (test_num);
CREATE INDEX IF NOT EXISTS pe_result_prompt_id ON t_pe_evaluation_result (prompt_id);
CREATE INDEX IF NOT EXISTS idx_task ON t_pe_variable (pe_task_id);
CREATE INDEX IF NOT EXISTS UNIQUE_VARIABLE ON t_pe_variable (key,pe_task_id);
CREATE INDEX IF NOT EXISTS index_name ON t_job_instance (name);
CREATE INDEX IF NOT EXISTS idx_tmptt_task ON t_mapping_pe_task_tag (task_id);
CREATE INDEX IF NOT EXISTS idx_tmptt_tag ON t_mapping_pe_task_tag (tag_id);
CREATE INDEX IF NOT EXISTS key_name ON t_pe_prompt_library (name);
CREATE INDEX IF NOT EXISTS key_project_id ON t_pe_prompt_library (project_id);
CREATE INDEX IF NOT EXISTS key_template_id ON t_mapping_pe_template_tag (template_id);
CREATE INDEX IF NOT EXISTS key_tag ON t_mapping_pe_template_tag (tag_id);
CREATE UNIQUE INDEX IF NOT EXISTS uniq_task_id_name ON t_pe_optimization_task (task_id, name);
CREATE INDEX IF NOT EXISTS ix_task_id ON t_pe_optimization_task (task_id);
CREATE INDEX IF NOT EXISTS ix_creator_status ON t_pe_optimization_task (creator,status);
CREATE INDEX IF NOT EXISTS idx_t_pe_op_task_domain_id ON t_pe_op_task (domain_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_t_mcp_project_id_mcp_server_name_en ON t_mcp (project_id, server_name_en);
CREATE INDEX IF NOT EXISTS idx_t_mcp_server_updated_on ON t_mcp (updated_on);
CREATE UNIQUE INDEX IF NOT EXISTS idx_t_mcp_config_creator_id_project_id_server_id ON t_mcp_config (server_id, creator_id, project_id);
CREATE INDEX IF NOT EXISTS idx_t_mcp_config_updated_on ON t_mcp_config (updated_on);
CREATE INDEX IF NOT EXISTS idx_t_tool_updated_on ON t_tool (updated_on);
CREATE INDEX IF NOT EXISTS idx_t_mapping_agent_tool_assistant_id ON t_mapping_agent_tool (agent_id);
CREATE INDEX IF NOT EXISTS idx_t_mapping_agent_tool_project_id ON t_mapping_agent_tool (project_id);
CREATE INDEX IF NOT EXISTS idx_t_mapping_agent_tool_tool_id ON t_mapping_agent_tool (tool_id);
CREATE INDEX IF NOT EXISTS idx_t_mapping_tool_function_updated_on ON t_mapping_tool_function (updated_on);
CREATE INDEX IF NOT EXISTS idx_create_time ON t_task (create_time);
CREATE INDEX IF NOT EXISTS idx_status_time ON t_task (status, create_time);
CREATE INDEX IF NOT EXISTS idx_finish_time ON t_task (finish_time);
