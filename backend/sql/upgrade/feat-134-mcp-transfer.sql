-- FEAT-134 MCP服务导入导出与重载：数据库增量
-- 依据：设计文档/mcp导入导出和重载/FEAT-134-L2-MCP服务导入导出与重载详细设计.md §7.1
-- 所有变更向后兼容：新增列带默认值、新增表，老实例无新字段值时按默认行为。

-- 1. 服务表新增并发控制与导入待补配标记
ALTER TABLE ws_mcp_service_def
    ADD COLUMN snapshot_revision BIGINT NOT NULL DEFAULT 0 COMMENT '快照与配置相关写入的并发修订号';
ALTER TABLE ws_mcp_service_def
    ADD COLUMN active_mcp_operation_id VARCHAR(64) NULL COMMENT '同服务活动操作声明（与ws_mcp_operation.id对应）';
ALTER TABLE ws_mcp_service_def
    ADD COLUMN import_config_pending TINYINT(1) NOT NULL DEFAULT 0 COMMENT '导入后待补配提示标记（不改鉴权scope）';
ALTER TABLE ws_mcp_service_def
    ADD COLUMN import_config_paths TEXT NULL COMMENT '待补配的JSON Pointer路径清单（仅路径不含值）';

-- 2. 操作主表
CREATE TABLE IF NOT EXISTS ws_mcp_operation (
    id VARCHAR(64) NOT NULL COMMENT '操作ID（UUID）',
    operation_type VARCHAR(16) NOT NULL COMMENT 'IMPORT / RELOAD',
    tenant_id VARCHAR(64) NOT NULL,
    project_id VARCHAR(64) NOT NULL,
    workspace_id VARCHAR(64) NOT NULL,
    creator_id VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL COMMENT 'RUNNING / SUCCESS / PARTIAL_SUCCESS / FAILED / INTERRUPTED',
    total INT NOT NULL DEFAULT 0,
    created_count INT NOT NULL DEFAULT 0,
    success_count INT NOT NULL DEFAULT 0,
    failed_count INT NOT NULL DEFAULT 0,
    created_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_date TIMESTAMP NULL DEFAULT NULL,
    deadline_date TIMESTAMP NOT NULL COMMENT '受理时固定的执行期限',
    PRIMARY KEY (id),
    KEY idx_ws_mcp_operation_ws (tenant_id, project_id, workspace_id, created_date),
    KEY idx_ws_mcp_operation_deadline (status, deadline_date)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT 'MCP导入/重载操作主表';

-- 3. 操作逐项表
CREATE TABLE IF NOT EXISTS ws_mcp_operation_item (
    operation_id VARCHAR(64) NOT NULL,
    item_index INT NOT NULL,
    service_id VARCHAR(64) NULL COMMENT '新建/目标服务ID',
    original_name VARCHAR(64) NULL,
    actual_name VARCHAR(64) NULL,
    status VARCHAR(32) NOT NULL COMMENT 'PENDING / SUCCESS / FAILED',
    refresh_status VARCHAR(32) NULL COMMENT '导入项工具刷新结果',
    source_snapshot LONGTEXT NULL COMMENT '清理后的源工具声明（只读参考，终态保留7天）',
    result_json TEXT NULL COMMENT '工具计数、增删名称及提示',
    error_code VARCHAR(64) NULL,
    safe_reason VARCHAR(512) NULL COMMENT '脱敏后的失败原因',
    started_date TIMESTAMP NULL DEFAULT NULL,
    finished_date TIMESTAMP NULL DEFAULT NULL,
    PRIMARY KEY (operation_id, item_index)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT 'MCP导入/重载操作逐项表';
