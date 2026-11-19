import { signal, WritableSignal } from '@angular/core';

import { autoProp, prop } from '@agentcore/shared/decorators/prop';

export type CustomTreeNode = {
  label: string;
  isDir: boolean;
  content?: any;
  children?: CustomTreeNode[];
  fileIcon?: string;
  language?: string;
  path: string;
  expanded?: boolean;
  selected?: boolean;
  isLeaf?: boolean;
};

export enum SkillResourceType {
  ALL = 'all',
  GENERAL = 'general',
  EFFENCY = 'effency',
  TOOL = 'tool',
  DESIGN = 'design',
  CREATE = 'create',
}

export const SKILL_RESOURCE_TYPE_CONFIG: Record<`${SkillResourceType}`, { i18key: string; id: string }> = {
  all: {
    i18key: 'skill.resource.tag.all',
    id: undefined,
  },
  general: {
    i18key: 'skill.resource.tag.general',
    id: 'dsa79d76-c26a-4dad-92s7-a46dcs2271eb',
  },
  effency: {
    i18key: 'skill.resource.tag.effency',
    id: 'sda9e07a-9e2t-44cx-85c5-400cews28a6b',
  },
  tool: {
    i18key: 'skill.resource.tag.tool',
    id: 'b4baa07a-9b86-443e-85c5-4ksc1e2azxcb',
  },
  design: {
    i18key: 'skill.resource.tag.design',
    id: 'b4bzxsa-9ss6-4wq7e-asc5-400c1e2a8a6b',
  },
  create: {
    i18key: 'skill.resource.tag.create',
    id: 'b4b9e07a-9b86-447e-85c5-400casdasdd',
  },
};

export enum SkillEditorTab {
  MD = 'MD',
  CODE = 'CODE',
}

export enum SkillDetailFromPage {
  SKILL = 'skill',
  RESOURCE = 'resource',
}

export class SkillVersionDetail {
  @autoProp()
  versionId: string;

  @autoProp()
  obsUrl: string;

  @autoProp()
  createdAt: number;

  @autoProp()
  creatorName: string;

  @autoProp()
  skillId: string;

  @autoProp()
  skillName: string;

  @autoProp()
  versionName: string;

  @autoProp()
  used: boolean;

  @autoProp()
  description: string;

  @prop({ name: 'viewMode' })
  viewMode?: boolean;

  operators?: any[];
}

export class SkillVersionListRes {
  @autoProp({ instances: SkillVersionDetail })
  items: SkillVersionDetail[];

  @autoProp()
  total = 0;
}

export const SkillStatusTag: Record<
  `${SkillDetailStatus}`,
  {
    labelKey: string;
    color: string;
  }
> = {
  developing: {
    labelKey: 'skill.detail.statusTag.developing',
    color: 'blue',
  },
  developed: {
    labelKey: 'skill.detail.statusTag.developed',
    color: 'green',
  },
};

export enum SkillDetailStatus {
  DEVELPING = 'developing',
  DEVELOPED = 'developed',
}

export const SkillSourceTag: Record<
  `${SkillDetailSource}`,
  {
    labelKey: string;
    color: string;
  }
> = {
  custom: {
    labelKey: 'skill.detail.sourceTag.custom',
    color: 'blue',
  },
  import: {
    labelKey: 'skill.detail.sourceTag.import',
    color: 'orange',
  },
};

export enum SkillDetailSource {
  CUSTOM = 'custom',
  IMPORT = 'import',
}

export class SkillDetail {
  @autoProp()
  skillId: string;

  @autoProp()
  skillName: string;

  @autoProp()
  icon = '';

  @autoProp()
  status: SkillDetailStatus;

  @autoProp()
  source: SkillDetailSource;

  @autoProp()
  description: string;

  @autoProp()
  createdTime: string;

  @autoProp()
  creatorName: string;

  @autoProp()
  updatedTime: string;

  @autoProp()
  obsUrl: string;

  @autoProp()
  domainId: string;

  @autoProp()
  latestVersion: string;

  @autoProp()
  usedVersion: string;

  @autoProp()
  usedVersionName: string;

  @autoProp()
  tagId?: string;

  @prop({ name: 'viewMode' })
  viewMode?: boolean;

  @prop({ name: 'versionName' })
  versionName: string;

  @autoProp()
  publishedAsset?: number;

  @autoProp()
  plazaSource?: string;

  @autoProp()
  isOwner?: boolean;
}

export class SkillDetailRes {
  @autoProp({ instance: SkillDetail })
  skillInfo: SkillDetail;
}

export class SkillListRes {
  @autoProp({ instances: SkillDetail })
  items: SkillDetail[];

  @autoProp()
  total = 0;
}

export const skillDetailSignal: WritableSignal<SkillDetail | null> = signal(null);
