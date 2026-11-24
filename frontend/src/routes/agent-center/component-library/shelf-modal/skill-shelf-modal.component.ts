import { Component, Inject, OnInit } from '@angular/core';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { NZ_MODAL_DATA, NzModalRef } from 'ng-zorro-antd/modal';
import { MODULES } from '@shared/modules';
import { I18N_NAMESPACE } from '@agentcore/constants/common';
import { i18nProviderValue } from '@agentcore/core/i18n.service';
import { AssertSquareTagType } from '@routes/agent-center/app-agent/common-logic-agent';
import { PromptService } from '@services/prompt.service';

/**
 * Skill 上架到资产广场的分类选择表单（FR-06，资源分类 tag 体系）。
 *
 * 分类由后端 t_pe_industry（library_type='skill'）下发，前端不硬编码 ID（#1731）。
 */
@Component({
  selector: 'app-skill-shelf-modal',
  templateUrl: './skill-shelf-modal.component.html',
  standalone: true,
  imports: [MODULES],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: i18nProviderValue([I18N_NAMESPACE.Skill]),
    },
  ],
})
export class SkillShelfModalComponent implements OnInit {
  options: { id: string; name: string }[] = [];
  selectedTagId = '';

  constructor(
    private modalRef: NzModalRef,
    private promptService: PromptService,
    /** 父组件经 nzData 注入的提交回调（确定时直调并发请求，数据由 NZ_MODAL_DATA 通道可靠传递） */
    @Inject(NZ_MODAL_DATA)
    public nzData: { submit: (payload: Record<string, any>) => Promise<any> }
  ) {}

  ngOnInit(): void {
    // 分类由后端 t_pe_industry（library_type='skill'）下发，前端不硬编码 ID（#1731）
    this.promptService
      ?.getAssertTagAsync({ library_type: 'skill' })
      .then((res: AssertSquareTagType[]) => {
        this.options = (res || []).map(tag => ({ id: tag.id, name: tag.name }));
      })
      .catch(() => {});
  }

  onCancel(): void {
    this.modalRef.close();
  }

  onOk(): void {
    const payload: Record<string, any> = {};
    if (this.selectedTagId) {
      payload.tag_id = this.selectedTagId;
    }
    this.nzData
      .submit(payload)
      .catch(() => {})
      .finally(() => this.modalRef.close());
  }
}
