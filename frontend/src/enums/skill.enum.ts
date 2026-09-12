export const SKILL_MAX_COUNT = 50;
 
/** 添加skill弹窗中的2个Tab Id */
export enum SkillTabId {
  // skill广场
  SKILL_MARKET = 'SKILL_MARKET',
  // 组件库SKILL
  SKILL_LIBRARY = 'SKILL_LIBRARY',
}
 
export enum SkillStatus {
  // 可用
  DEVELOPED = 'developed',
  // 开发中
  DEVELOPING = 'developing',
}
 
export enum SkillSource {
  // 自定义
  CUSTOM = 'custom',
  // 外部导入
  IMPORT = 'import',
}
 
export enum SkillPublishedAsset {
  // 专家·技能预置数据
  PUBLISHED = 1,
  // 组件库自定义数据
  NOT_PUBLISHED = 0,
}
