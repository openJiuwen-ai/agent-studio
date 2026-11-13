import { Component, Inject } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { NZ_MODAL_DATA, NzModalRef } from 'ng-zorro-antd/modal';
import { I18nNamespace } from '@i18n';
import { MODULES } from '@shared/modules';

/**
 * MCP 服务实例上架补充表单（服务说明可选；行业分类仅接口预留，前端不展示——精选 MCP 无行业维度）
 */
@Component({
  selector: 'app-mcp-shelf-modal',
  templateUrl: './mcp-shelf-modal.component.html',
  standalone: true,
  imports: [MODULES],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.COMMON],
    },
  ],
})
export class McpShelfModalComponent {
  form: FormGroup;

  constructor(
    private fb: FormBuilder,
    private modalRef: NzModalRef,
    /** 父组件经 nzData 注入的提交回调（确定时直调并发请求） */
    @Inject(NZ_MODAL_DATA)
    public nzData: { submit: (payload: Record<string, any>) => Promise<any> }
  ) {
    this.form = this.fb.group({
      readme: [''],
    });
  }

  onCancel(): void {
    this.modalRef.close();
  }

  onOk(): void {
    const value = this.form?.value || {};
    this.nzData
      .submit({ readme: value.readme || undefined })
      .catch(() => {})
      .finally(() => this.modalRef.close());
  }
}