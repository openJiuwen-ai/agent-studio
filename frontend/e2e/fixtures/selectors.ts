/**
 * i18n 文案与路由常量（zh-CN，源自 assets/i18n/zh-CN/model-access.json）。
 * 文案为 i18n 驱动，若切换语言包需同步更新此处。
 * 对应 i18n key 标注于注释，便于回溯。
 */

export const I18N = {
  importModels: '导入模型', // import_models（列表页/详情页导入按钮）
  export: '导出', // export（列表页 hover 第4按钮、详情页 ellipsis 菜单项）
  confirmImport: '确认导入', // import_model_confirm
  chooseFile: '点击选择 .jsonl 文件', // import_model_choose_file
  fileTypeInvalid: '仅支持 .jsonl 文件', // import_model_file_type_invalid
  previewTotal: '总数', // import_preview_total
  previewConflict: '冲突', // import_preview_conflict
  skip: '同名跳过', // conflict_strategy_skip
  cover: '同名覆盖', // conflict_strategy_cover
  coverWarn: '覆盖将删除目标环境同名旧记录，请谨慎操作', // conflict_strategy_cover_warn
  importResult: '导入结果', // import_result
  importResultSucceed: '成功', // import_result_succeed
  importResultFailed: '失败', // import_result_failed
  importComplete: '导入完成', // import_model_success_tip
  importModelPartial: '导入完成，成功', // import_model_partial_tip 前缀
  importModelFailed: '导入失败', // import_model_failed
  previewFailed: '预检失败', // import_model_preview_failed
  cancel: '取消', // cancel
  ok: '确定', // ok
  supplierDetail: '供应商详情', // supplier_detail
} as const;

/**
 * 前端路由（Angular）。若实际路由带 project 作用域前缀，在此统一调整。
 * TODO: 确认 detail 路由的精确形态（如 /model-management/:providerId）。
 */
/**
 * 前端路由（Angular HashLocationStrategy，URL 形如 /openjiuwen/#/home/...）。
 * 注意：平台用 hash 路由，不要写成绝对 /path（会丢失 #/home 前缀被踢回首页）。
 * baseURL 应为 http://localhost:4200/openjiuwen/（末尾斜杠），此处用相对路径 goto 即可拼接。
 *   列表页：model-management 模块入口（ModalManagementComponent，带左侧菜单）
 *   详情页：activeName=CUSTOM 表示"自定义模型"tab；queryFilter 保持分页默认；provider_id 为 query 参数
 */
export const ROUTES = {
  listPage: '#/home/model/management',
  detailPage: (providerId: string) =>
    `#/home/model/management-detail?activeName=CUSTOM&provider_id=${providerId}&queryFilter=%7B%22page_num%22:1,%22page_size%22:12%7D`,
} as const;

/**
 * 后端 API 路径匹配（page.route 谓词）。
 * 前端服务层 prefix = `${baseUrl}/model-manager`，故路径含 /model-manager/model-services/...。
 * 用 URL.pathname 精确匹配，避免 /import 与 /import/preview 互串。
 */
export const URL_PATTERNS = {
  export: (u: URL) => u.pathname.endsWith('/model-services/export'),
  preview: (u: URL) => u.pathname.endsWith('/model-services/import/preview'),
  import: (u: URL) => u.pathname.endsWith('/model-services/import'),
} as const;
