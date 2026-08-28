import { Injectable } from '@angular/core';
import { I18NextEagerPipe } from 'angular-i18next';
import { CommonUtils } from 'src/utils/common.util';
import { WORKFLOW_DEFAULT_ICON_BASE64_STR } from '@routes/agent-center/app-flow/components/create-workflow/default-icon-base64';
import {
  MCP_DEFAULT_ICON_BASE64_STR,
  PLUGIN_DEFAULT_ICON_BASE64_STR,
} from '@shared/config/default-icons-base64';
import {
  IGuide,
  ISceneData,
  ISkillChildrenOption,
  ISkillOption,
  SCENARIO_FIELD_ID,
  SKILL_TYPE,
  SkillSet,
} from './scenario-guide-modal.constant';

@Injectable({
  providedIn: 'root',
})
export class ScenarioGuideModalService {
  public lang = CommonUtils.getLanguage();
  constructor(private i18n: I18NextEagerPipe) {}

  public initSkillOptions(skillSet: SkillSet): ISkillOption[] {
    return [
      {
        label: skillSet.mcpServersAdded?.title,
        skillType: SKILL_TYPE.MCP,
        children: (skillSet.mcpServersAdded?.list || []).map((item) =>
          this.getSkillOption(item, SKILL_TYPE.MCP),
        ),
      },
      {
        label: skillSet.pluginAdded?.title,
        skillType: SKILL_TYPE.PLUGIN,
        children: (skillSet.pluginAdded?.list || []).map((item) =>
          this.getSkillOption(item, SKILL_TYPE.PLUGIN),
        ),
      },
      {
        label: skillSet.flowAdded?.title,
        skillType: SKILL_TYPE.WORK_FLOW,
        children: (skillSet.flowAdded?.list || []).map((item) =>
          this.getSkillOption(item, SKILL_TYPE.WORK_FLOW),
        ),
      },
    ].filter((item) => item.children.length);
  }

  public getSkillOption(item, skillType: SKILL_TYPE): ISkillChildrenOption {
    if (skillType === SKILL_TYPE.MCP) {
      return {
        id: item.server_id,
        label: item.name || item.server_id,
        avatar: this.getSkillAvatar(item.avatar, MCP_DEFAULT_ICON_BASE64_STR),
        disabled: !item.valid,
        skillType: SKILL_TYPE.MCP,
        name: item.name,
      };
    }
    if (skillType === SKILL_TYPE.PLUGIN) {
      return {
        id: item.id || item.tool_id,
        label: this.getPluginLabel(item),
        avatar: this.getSkillAvatar(item.icon, PLUGIN_DEFAULT_ICON_BASE64_STR),
        disabled: !this.getPluginOrFloValid(item),
        skillType: SKILL_TYPE.PLUGIN,
        name: item.plugin_display_name,
      };
    }

    return {
      id: item.workflow_id,
      label: item.workflow_name || item.workflow_id,
      avatar: this.getSkillAvatar(
        item.avatar,
        WORKFLOW_DEFAULT_ICON_BASE64_STR,
      ),
      disabled: !this.getPluginOrFloValid(item),
      skillType: SKILL_TYPE.WORK_FLOW,
      name: item.code,
    };
  }

  /**
   * 获取插件名（国际化）
   */
  public getSkillAvatar(avatar: string, defaultIcon: string): string {
    if (!avatar) {
      return defaultIcon;
    }
    if (avatar.startsWith('data:image/')) {
      return avatar;
    }
    return `data:image/png;base64,${avatar}`;
  }

  public getPluginLabel(pluginItem): string {
    return `${this.getPluginName(pluginItem)}/${this.getToolName(pluginItem)}`;
  }

  public getPluginOrFloValid(item): boolean {
    return item.app_last_version_obj?.valid ?? true;
  }

  /**
   * 获取插件名（国际化）
   */
  public getPluginName(pluginItem) {
    if (this.lang === 'zh-cn') {
      return pluginItem?.plugin_chinese_name ?? '--';
    } else {
      return pluginItem?.plugin_display_name ?? '--';
    }
  }

  /**
   * 获取工具名（国际化）
   */
  public getToolName(pluginItem): string {
    if (this.lang === 'zh-cn') {
      return pluginItem?.tool_chinese_name ?? '--';
    } else {
      return pluginItem?.tool_display_name ?? '--';
    }
  }

  public getModalData(modalFormGroup, originData: ISceneData): ISceneData {
    const formValue = modalFormGroup.value;
    const modalData: ISceneData = {
      name: formValue[SCENARIO_FIELD_ID.SCENE_NAME],
      description: formValue[SCENARIO_FIELD_ID.SCENE_DESC],
      guidelines: formValue[SCENARIO_FIELD_ID.GUIDE_CONFIG_LIST].map(
        (item, index) => this.getSaveGuideData(item, index),
      ),
    };

    if (originData?.id) {
      modalData.id = originData.id;
    }

    const relations = formValue[SCENARIO_FIELD_ID.DEPENDENCY_LIST];
    if (relations?.length) {
      // 防御：过滤掉依赖项/被依赖项未选择完整的行，避免空值取 priority 报错
      modalData.relations = relations
        .filter(
          (item) =>
            item?.[SCENARIO_FIELD_ID.DEPEND_ITEM] &&
            item?.[SCENARIO_FIELD_ID.BE_DEPENDED_ITEM],
        )
        .map((item) => ({
          type: 'dependency',
          src: item[SCENARIO_FIELD_ID.DEPEND_ITEM].priority,
          tgt: item[SCENARIO_FIELD_ID.BE_DEPENDED_ITEM].priority,
        }));
    }

    return modalData;
  }

  public getSaveGuideData(formData, index: number): IGuide {
    return {
      id: this.getPriorityByIndex(index),
      condition: formData[SCENARIO_FIELD_ID.TRIGGER_CONDITION],
      action: formData[SCENARIO_FIELD_ID.PERFORM_ACTION],
      tools: (formData[SCENARIO_FIELD_ID.SKILL_SET] || []).map((item) => ({
        id: item.id,
        name: item.name,
        type: item.skillType,
      })),
    };
  }

  public getPriorityByIndex(index: number): number {
    return index + 1;
  }

  public getGuideFormDataByOrigin(originData: ISceneData) {
    const guidelines = (originData?.guidelines || []).sort(
      (a, b) => a.id - b.id,
    );
    return guidelines.map((item) => ({
      [SCENARIO_FIELD_ID.TRIGGER_CONDITION]: item.condition,
      [SCENARIO_FIELD_ID.PERFORM_ACTION]: item.action,
      [SCENARIO_FIELD_ID.SKILL_SET]: (item.tools || [])
        .map((tool) => {
          return tool.skillOption;
        })
        .filter((skillOption) => skillOption),
    }));
  }
}