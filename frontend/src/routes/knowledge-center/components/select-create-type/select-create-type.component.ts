import {
  Component,
  EventEmitter,
  OnInit,
  Output,
  ViewChild,
} from '@angular/core';
import { I18nNamespace } from '@i18n';
import { KbAbilitiesService } from '@services/knowledge-center/kb-abilities.service';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { NzModalRef, NzModalService } from 'ng-zorro-antd/modal';
import { KnowledgeRepoService } from '@services/agent-center/knowledge.service';
import { CommonService } from '@services/common.service';
import { ContextService } from '@services/context.service';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { KnowledgeBaseExceedModalComponent } from '@routes/knowledge-center/components/knowledge-base-exceed-modal/knowledge-base-exceed-modal.component';

@Component({
  selector: 'select-create-type',
  templateUrl: './select-create-type.component.html',
  styleUrls: ['./select-create-type.component.less'],
  standalone: true,
  imports: [MODULES, KnowledgeBaseExceedModalComponent],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.KNOWLEDGE,
        I18nNamespace.COMMON,
        I18nNamespace.AGENT_CENTER,
      ],
    },
  ],
})
export class SelectCreateTypeComponent implements OnInit {
  @ViewChild('selectCreateType') selectCreateType: any;
  @ViewChild('selectCreateTitle') selectCreateTitle: any;
  @ViewChild('selectCreateFooter') selectCreateFooter: any;
  @ViewChild('exceedModal') exceedModal: KnowledgeBaseExceedModalComponent;
  @Output() openDefaultKnowledgeBase = new EventEmitter<string>();
  @Output() openThirdPartyKnowledgeBase = new EventEmitter<string>();
  @Output() openAccessKnowledgeBase = new EventEmitter<string>();
  @Output() openDefaultConfigModal = new EventEmitter<string>();
  accessDataTotal = 0;
  isDoneDefaultConfig = false;
  connectorId = '';
  modalRef: NzModalRef;
  constructor(
    private nzModalService: NzModalService,
    private knowledgeBaseService: KnowledgeRepoService,
    private commonService: CommonService,
    public contextService: ContextService,
    private agentRepoService: AppAgentRepoService,
    public kbAbilitiesService: KbAbilitiesService,
    private i18n: I18NextEagerPipe,
  ) {
    this.isDoneDefaultConfig = false;
    if (this.kbAbilitiesService.isPermitKBDefaultConfig()) {
      this.knowledgeBaseService
        .getKnowledgeDefaultConfigDetail(
          'default_lakesearch_inside_connection_id',
        )
        .then((res) => {
          this.isDoneDefaultConfig =
            !res?.knowledge_base_connection_detail?.params?.length;
        });
    }
  }

  ngOnInit(): void {}

  public typeItems = [
    {
      title: this.i18n.transform('default'),
      content: this.i18n.transform('internal_knowledge_base'),
      iconName: 'cloud-centos',
      key: 'default',
    },
    {
      title: this.i18n.transform('third_party'),
      content: this.i18n.transform('external_knowledge_base_import'),
      iconName: 'cloud-debian',
      key: 'third',
      disabled: true,
    },
  ];
  public selectedType = this.typeItems[0];

  openDefaultModal(event) {
    event.stopPropagation();
    this.openDefaultConfigModal.emit(this.connectorId);
    if (this.modalRef) {
      this.modalRef.close();
    }
  }

  onCancel(): void {
    if (this.modalRef) {
      this.modalRef.close();
    }
  }

  async onOk(): Promise<void> {
    if (this.selectedType.key === 'default') {
      const res = await this.isResourceExceed('knowledgeBase', false);
      if (res) {
        return;
      }
      this.openDefaultKnowledgeBase.emit();
    } else if (this.selectedType.key === 'third') {
      const res = await this.isResourceExceed(
        'thirdPartyKnowledgeBase',
        true,
      );
      if (res) {
        return;
      }
      this.openThirdPartyKnowledgeBase.emit();
    }
    if (this.modalRef) {
      this.modalRef.close();
    }
  }
  show() {
    this.selectedType = this.typeItems[0];
    if (this.isDoneDefaultConfig) {
      this.knowledgeBaseService
        .getKnowledgeDefaultConfigDetail(
          'default_lakesearch_inside_connection_id',
        )
        .then((res) => {
          if (res?.knowledge_base_connection_detail?.params?.length > 0) {
            const params = res.knowledge_base_connection_detail.params;
            const authMode = params.find((item) => item.code === 'auth_mode');
            if (authMode.value) {
              this.connectorId = 'default_lakesearch_inside_connection_id';
            }
          }
          this.openSelectTypeModal();
        });
    } else {
      this.openSelectTypeModal();
    }
  }

  private openSelectTypeModal() {
    this.knowledgeBaseService
      .getThirdPartyKnowledgeBaseList({
        limit: 1000,
        offset: 0,
      })
      .then((result) => {
        this.accessDataTotal = result.total;
        this.typeItems[1].disabled = this.accessDataTotal === 0;
        this.modalRef = this.nzModalService.create({
          nzTitle: this.selectCreateTitle,
          nzFooter: this.selectCreateFooter,
          nzContent: this.selectCreateType,
          nzWidth: 500,
          nzClosable: true,
          nzMaskClosable: false,
        });
      });
  }

  async isResourceExceed(type: string, isThird: boolean) {
    const res = await this.agentRepoService.getResourceQuantity(type);
    if (res) {
      const { isExceedLimit, totalAmount } = res;
      if (isExceedLimit) {
        const params = { totalAmount, type: isThird ? 'third' : 'default' };
        this.exceedModal.show(params);
        return Promise.resolve(true);
      }
    }
    return Promise.resolve(false);
  }
}
