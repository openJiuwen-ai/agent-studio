import { Component, Inject, OnInit } from '@angular/core';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { NZ_MODAL_DATA, NzModalRef } from 'ng-zorro-antd/modal';
import { I18nNamespace } from '@i18n';
import { MODULES } from '@shared/modules';
import { PromptService } from '@services/prompt.service';

/**
 * 插件上架到资产广场补充表单（FRS-091 增强：页面统一发布最新发布版本，另行业分类可选）
 */
@Component({
  selector: 'app-plugin-shelf-modal',
  templateUrl: './plugin-shelf-modal.component.html',
  standalone: true,
  imports: [MODULES],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.COMMON],
    },
  ],
})
export class PluginShelfModalComponent implements OnInit {
  categoryId = '';
  categoryOptions: any[] = [];

  constructor(
    private promptService: PromptService,
    private modalRef: NzModalRef,
    /** 父组件经 nzData 注入的提交回调（确定时直调并发请求） */
    @Inject(NZ_MODAL_DATA)
    public nzData: { submit: (payload: Record<string, any>) => Promise<any> }
  ) {}

  ngOnInit(): void {
    this.promptService
      ?.getAssertTagAsync({ library_type: 'plugin' })
      .then(res => {
        this.categoryOptions = res || [];
      })
      .catch(() => {});
  }

  onCancel(): void {
    this.modalRef.close();
  }

  onOk(): void {
    this.nzData
      .submit({ category: this.categoryId || undefined })
      .catch(() => {})
      .finally(() => this.modalRef.close());
  }
}