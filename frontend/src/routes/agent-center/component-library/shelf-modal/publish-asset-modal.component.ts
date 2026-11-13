import { Component, Inject, OnInit } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { NZ_MODAL_DATA, NzModalRef } from 'ng-zorro-antd/modal';
import { I18nNamespace } from '@i18n';
import { MODULES } from '@shared/modules';
import { SkillApi } from '@agentcore/api/skill.api';
import { MCPService } from '@services/agent-center/mcp.service';
import { AppPluginRepoService } from '@services/agent-center/app-plugin-repo.service';
import { PromptService } from '@services/prompt.service';
import { MessageComponent } from '@shared/services/cfdata.service';
import { I18N_NAMESPACE } from '@agentcore/constants/common';
import { i18nProviderValue } from '@agentcore/core/i18n.service';
import { SKILL_RESOURCE_TYPE_CONFIG, SkillResourceType } from '@agentcore/constants/skill.model';

export type PublishAssetType = 'skill' | 'plugin' | 'mcp';

@Component({
  selector: 'app-publish-asset-modal',
  templateUrl: './publish-asset-modal.component.html',
  standalone: true,
  imports: [MODULES],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.AGENT_CENTER,
        I18nNamespace.COMMON,
        ...i18nProviderValue([I18N_NAMESPACE.Skill]),
      ],
    },
  ],
})
export class PublishAssetModalComponent implements OnInit {
  assetType: PublishAssetType = 'skill';
  assets: any[] = [];
  selectedAssetId = '';
  loading = false;
  submitting = false;
  form!: FormGroup;
  showCategory = false;
  showTag = false;
  showReadme = false;
  categoryOptions: any[] = [];
  skillTags: { id: string; i18key: string }[] = [];

  constructor(
    private fb: FormBuilder,
    private modalRef: NzModalRef,
    private skillApi: SkillApi,
    private mcpService: MCPService,
    private appPluginRepoServ: AppPluginRepoService,
    private promptService: PromptService,
    @Inject(NZ_MODAL_DATA)
    public nzData: {
      assetType: PublishAssetType;
      onPublished?: () => void;
    },
    private i18n: I18NextEagerPipe
  ) {}

  ngOnInit(): void {
    this.assetType = this.nzData.assetType;
    this.form = this.fb.group({
      tag_id: [''],
      category: [''],
      readme: [''],
    });
    this.showTag = this.assetType === 'skill';
    this.showCategory = this.assetType === 'plugin';
    this.showReadme = this.assetType === 'mcp';
    if (this.assetType === 'skill') {
      this.skillTags = (Object.keys(SKILL_RESOURCE_TYPE_CONFIG) as SkillResourceType[])
        .filter(key => key !== 'all')
        .map(key => ({
          id: SKILL_RESOURCE_TYPE_CONFIG[key].id,
          i18key: SKILL_RESOURCE_TYPE_CONFIG[key].i18key,
        }));
    }
    if (this.assetType === 'plugin') {
      this.promptService
        ?.getAssertTagAsync({ library_type: 'plugin' })
        .then(res => {
          this.categoryOptions = res || [];
        })
        .catch(() => {});
    }
    this.loadAssets();
  }

  private getWorkspaceId(): string {
    return this.skillApi.request.getWorkspaceId();
  }

  private loadAssets(): void {
    this.loading = true;
    const ws = this.getWorkspaceId();
    if (this.assetType === 'skill') {
      this.skillApi
        .querySkillList({ workspace_id: ws, limit: 100, offset: 0, language: 'ZH' })
        .subscribe({
          next: (res: any) => {
            this.assets = (res?.items || []).filter(
              (s: any) => s.published_asset !== 1 && s.status === 'developed'
            );
            this.loading = false;
          },
          error: () => {
            this.loading = false;
          },
        });
    } else if (this.assetType === 'plugin') {
      this.appPluginRepoServ
        .getPluginList({ workspace_id: ws, type: 'custom', published: 1 } as any)
        .then((res: any) => {
          this.assets = (res?.plugin_list || []).filter(
            (p: any) => p.platform_published !== 1
          );
          this.loading = false;
        })
        .catch(() => {
          this.loading = false;
        });
    } else if (this.assetType === 'mcp') {
      this.mcpService
        .getServiceList({ workspace_id: ws, limit: 100 }, {})
        .then((res: any) => {
          this.assets = (res?.mcps || []).filter(
            (m: any) =>
              m.fc_instance_status === 'success' && m.platform_published !== 1
          );
          this.loading = false;
        })
        .catch(() => {
          this.loading = false;
        });
    }
  }

  getAssetName(asset: any): string {
    if (this.assetType === 'skill') return asset.skill_name || asset.name || '';
    if (this.assetType === 'plugin') return asset.plugin_chinese_name || asset.plugin_display_name || '';
    return asset.name || asset.name_en || '';
  }

  getAssetId(asset: any): string {
    if (this.assetType === 'skill') return asset.skill_id;
    if (this.assetType === 'plugin') return asset.plugin_id;
    return asset.id;
  }

  onAssetSelect(assetId: string): void {
    // 二次上架默认回显第一次上架时填写的展示信息（FRS-091）
    const asset = this.assets.find(a => this.getAssetId(a) === assetId);
    if (!asset || !this.form) {
      return;
    }
    if (this.assetType === 'skill') {
      this.form.patchValue({ tag_id: asset.tag_id || '' });
    } else if (this.assetType === 'plugin') {
      this.form.patchValue({ category: asset.category || '' });
    } else if (this.assetType === 'mcp') {
      this.form.patchValue({ readme: asset.readme || '' });
    }
  }

  onCancel(): void {
    this.modalRef.close();
  }

  onOk(): void {
    if (!this.selectedAssetId) {
      return;
    }
    this.submitting = true;
    const value = this.form?.value || {};
    const promise = this.doPublish(this.selectedAssetId, value);
    if (promise) {
      promise
        .then(() => {
          MessageComponent.showSuccess(this.i18n.transform('plaza_onshelf_success'));
          this.nzData.onPublished?.();
          this.modalRef.close(true);
        })
        .catch(() => {})
        .finally(() => {
          this.submitting = false;
        });
    }
  }

  private doPublish(assetId: string, value: any): Promise<any> | null {
    if (this.assetType === 'skill') {
      return this.skillApi
        .publishSkill(assetId, value.tag_id || undefined)
        .toPromise();
    }
    if (this.assetType === 'plugin') {
      return this.appPluginRepoServ.publishPlugin(
        assetId,
        undefined,
        value.category || undefined
      );
    }
    if (this.assetType === 'mcp') {
      return this.mcpService.publishServer(
        assetId,
        undefined,
        value.readme || undefined
      );
    }
    return null;
  }
}