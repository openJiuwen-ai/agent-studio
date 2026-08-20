import {
  Component,
  computed,
  effect,
  EventEmitter,
  Input,
  OnDestroy,
  Output,
  signal,
  SimpleChanges,
  ViewChild,
  ChangeDetectorRef,
} from '@angular/core';
import { MODULES } from '@shared/modules';
import {
  I18NEXT_NAMESPACE,
  I18NextEagerPipe,
  I18NextModule,
} from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { Router } from '@angular/router';
import { NzModalService, NzModalRef, NzModalModule } from 'ng-zorro-antd/modal';
import { cdnAssetUrl } from '../../../../../single-spa/assets-url';
import { ModelManagementService } from '@services/repositories/model-management-new';
import { ModelType } from '@enums/jiuwen-model.enum';
import { CommonService } from '@services/common.service';
import * as angularI18next from 'angular-i18next';
import { AuthModalComponent } from '@routes/model-management/components/auth-modal/auth-modal.component';
import { ModelModalComponent } from '@routes/model-square/components/model-modal/model-modal.component';
import { AgentConfigService } from "@routes/agent-center/agent-config.service";

@Component({
  selector: 'llm-select',
  templateUrl: './llm-select.component.html',
  styleUrls: ['./llm-select.component.less'],
  standalone: true,
  imports: [MODULES, I18NextModule, NzModalModule],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.AGENT_CENTER,
        I18nNamespace.JIUWEN_MODEL,
        I18nNamespace.MODEL_ACCESS,
      ],
    },
    NzModalService,
  ],
})
export class LLMSelectComponent implements OnDestroy {
  //仅路由策略处用到
  @Input() index?: number;
  @Input() filter?: object;
  @Input() from?: string;
  @Input() clearable?: boolean = true;

  @Input() modelType?: string;
  @Input() panelAlign?: 'left' | 'right' = 'right';
  @Input() panelWidth?: 'justified' | 'auto' = 'auto';

  @Input() addRouterStrategies?: boolean;
  modelOptions = [];

  @Input() modelValidation?;

  @Input() selectedModel: string = '';
  public searchValue: string = '';

  @Input() showError?: boolean = false;

  @Input() refreshSubscribe = true;

  public serviceMap: object = {};
  public selectedModelInfo = {
    logo: '',
    service_name: '',
  };

  @Output() update = new EventEmitter<any>();
  @Output() showOptions = new EventEmitter<any>();
  @ViewChild('authTipContent', {static: false})
  authTipContentRef;

  @ViewChild('debugTipContent', {static: false})
  debugTipContentRef;

  @ViewChild('tipContent', {static: false})
  tipContentRef;

  public controller = new AbortController();

  public changeUrl = cdnAssetUrl;

  public isFirstPlatform = false;

  public authTipInfo: any = {
    tip: '',
    btn: '',
  };

  public debugTipInfo: any = {
    tip: '',
    btn: '',
  };

  public showDebugIcon: boolean = true;
  public showStatus: boolean = false;
  public image: string = this.changeUrl('assets/images/tag/test.svg');
  tagsMap = {
    is_support_function: {
      name: this.i18n.transform('llmselectcomponent_426', {
        ns: I18nNamespace.AGENT_CENTER,
      }),
      icon: this.changeUrl('assets/images/tag/tool.svg'),
    },
    is_reasoning: {
      name: this.i18n.transform('llmselectcomponent_427', {
        ns: I18nNamespace.AGENT_CENTER,
      }),
      icon: this.changeUrl('assets/images/tag/think.svg'),
    },
    is_network: {
      name: this.i18n.transform('llmselectcomponent_428', {
        ns: I18nNamespace.AGENT_CENTER,
      }),
      icon: this.changeUrl('assets/images/tag/network.svg'),
    },
    view: {
      name: this.i18n.transform('llmselectcomponent_429', {
        ns: I18nNamespace.AGENT_CENTER,
      }),
      icon: this.changeUrl('assets/images/tag/view.svg'),
    },
    text: {
      name: this.i18n.transform('llmselectcomponent_430', {
        ns: I18nNamespace.AGENT_CENTER,
      }),
      icon: this.changeUrl('assets/images/tag/text.svg'),
    },
    embed: {
      name: this.i18n.transform('llmselectcomponent_431', {
        ns: I18nNamespace.AGENT_CENTER,
      }),
      icon: this.changeUrl('assets/images/tag/embed.svg'),
    },
    sort: {
      name: this.i18n.transform('llmselectcomponent_432', {
        ns: I18nNamespace.AGENT_CENTER,
      }),
      icon: this.changeUrl('assets/images/tag/sort.svg'),
    },
  };
  public modelTagMap = {
    LLM: [
      {
        id: 'text',
      },
    ],
    'IMAGE-TO-TEXT': [
      {
        id: 'text',
      },
      {
        id: 'view',
      },
    ],
    'Text-Embedding': [
      {
        id: 'embed',
      },
    ],
    RERANK: [
      {
        id: 'sort',
      },
    ],
  };

  private _modelOptions = signal([]);
  private _subscribeMap = signal(new Map());

  constructor(
    private i18n: angularI18next.I18NextEagerPipe,
    private modelManagementService: ModelManagementService,
    private commonService: CommonService,
    private nzModal: NzModalService,
    private router: Router,
    private configServ: AgentConfigService,
    private cdr: ChangeDetectorRef,
  ) {
    effect(() => {
      const map = this._subscribeMap();
      const options = this._modelOptions().map(o => {
        return {
          ...o,
          children: o.children?.map(c => {
            const isSubscribed = o.isFirstPlatform ? (map.get(c.model_name) || c.is_subscribed) : undefined;
            return {
              ...c,
              ...(o.isFirstPlatform ? {
                isSubscribed,
                disabled: c.type === 'button' ? false : !isSubscribed && !c.is_in_free_trial
              } : {})
            };
          })
        }
      });
      this.modelOptions = options;
      if (this.modelOptions.length) {
        this.showOptions.emit(this.modelOptions);
      }
      this.cdr.detectChanges();
    });
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.modelType && changes.modelType.previousValue) {
      this.getModelOptions();
    }
    if (changes.selectedModel && changes.selectedModel.currentValue) {
      this.selectedModel = changes.selectedModel.currentValue;
      if(this.serviceMap[this.selectedModel]){
        this.updateSelectedModelInfo(this.serviceMap[this.selectedModel]);
      }
    }
  }

  ngOnInit() {
    const {display_show_model_status} = this.configServ.getConfigs();
    if (display_show_model_status) {
      this.showStatus = display_show_model_status
    }

    this.authTipInfo.tip = this.i18n.transform('auth_tip.tip_4');
    this.authTipInfo.btn = this.i18n.transform('square_btn.setting');
    this.debugTipInfo.tip = this.i18n.transform('auth_tip.tip_5');
    this.debugTipInfo.btn = this.i18n.transform('square_btn.test_now');
    this.getModelOptions();
    this.getMaaSModalSubscribe();
    this.showDebugIcon = window.location.href.indexOf('/model-test') <= 0
  }

  getModelStatus(is_connecting) {
    if (is_connecting === 'success') {
      return this.i18n.transform('success_1', {
        ns: I18nNamespace.AGENT_CENTER,
      });
    } else if (is_connecting === 'fail') {
      return this.i18n.transform('validation_failed', {
        ns: I18nNamespace.AGENT_CENTER,
      });
    }
    return this.i18n.transform('not_validated', {
      ns: I18nNamespace.AGENT_CENTER,
    });
  }

  getModelOptions(params?: any) {
    this.isFirstPlatform = false;
    // model_type:'LLM,IMAGE-TO-TEXT'
    if (this.controller) {
      this.controller.abort();
    }

    this.controller = new AbortController();
    this.modelManagementService
      .getAvailableModelList(
        {
          groupby: 'provider',
          publish_status: 'online',
          model_type: this.modelType ? this.modelType : 'LLM,IMAGE-TO-TEXT',
          ...params,
          ...this.filter,
          with_router:
            this.modelType === ModelType.LLM ||
            this.addRouterStrategies !== false,
        },
        this.controller.signal,
      )
      .then((res) => {
        this.modelOptions = [];
        const {platform_provider_id} = this.configServ.getConfigs();

        let provider_id = platform_provider_id || '100';
        const options = [];
        res?.data.forEach((item, index) => {
          this.getServiceMap(item.models, item.provider_name);
          const isFirstPlatform = !this.isFirstPlatform && item.id === provider_id;
          options.push({
            isFirstPlatform: isFirstPlatform,
            provider_name: item.provider_name,
            id: item.id,
            children: item.models ?? [],
          });
          if (isFirstPlatform) {
            this.isFirstPlatform = true;
          }
        });
        this._modelOptions.set(options);
        if(this.selectedModel){
          this.updateSelectedModelInfo(this.serviceMap[this.selectedModel]);
        }
        this.cdr.detectChanges();
      });
  }

  getServiceMap(models, providerName) {
    models.forEach((item) => {
      item.selfProviderName = providerName;
      this.serviceMap[item.id] = item;
    });
  }

  changeSelect(modelId: string) {
    //模型调测 需要返回模型对象 & index
    //路由策略需要加index

    // 先设置选中模型的图标信息
    if (this.serviceMap[modelId]) {
      this.updateSelectedModelInfo(this.serviceMap[modelId]);
    } else {
      this.selectedModelInfo = {
        logo: '',
        service_name: '',
      };
    }

    if (this.modelType) {
      this.update.emit({
        modelInfo: this.serviceMap[modelId],
        index: this.index,
      });
    } else {
      this.update.emit({
        id: modelId,
        index: this.index,
        modelInfo: this.serviceMap[modelId],
      });
    }

    this.cdr.detectChanges();
  }

  onBeforeSearch(searchWord: string) {
    this.searchValue = searchWord;
    if (searchWord) {
      this.updateSelectedModelInfo(this.serviceMap[this.selectedModel]);
    }
    this.getModelOptions(searchWord ? {service_name: searchWord} : {});
    if (!searchWord) {
      return;
    }
  }

  private updateSelectedModelInfo(model?: { logo?: string; service_name?: string }): void {
    this.selectedModelInfo = {
      logo: model?.logo || this.image,
      service_name: model?.service_name || '',
    };
  }

  ngOnDestroy(): void {
    if (this.controller) {
      this.controller.abort();
    }
  }

  public showAuthModal(item) {
    const {provider_id, selfProviderName} = item;
    const modalRef = this.nzModal.create({
      nzTitle: '',
      nzContent: AuthModalComponent,
      nzWidth: 500,
      nzFooter: null,
      nzClosable: true,
      nzCloseOnNavigation: false,
    });
    modalRef.componentInstance.id = item?.id;
    modalRef.componentInstance.provider_info = {
      ...item,
      id: provider_id,
      provider_name: selfProviderName,
    };
  }

  public openMore(e) {
    e.stopPropagation();
    this.nzModal.create({
      nzTitle: this.i18n.transform('resource_insufficient'),
      nzContent: ModelModalComponent,
      nzWidth: 500,
      nzFooter: null,
      nzClosable: true,
      nzCloseOnNavigation: false,
    });
  }

  getTipContentRef(selectedItem) {
    const {status, is_auth_configured = true} = selectedItem;
    const isKnownStatus = ['success', 'fail'].includes(status);

    // 未鉴权tip
    if (status === 'fail' && is_auth_configured === false) {
      return this.authTipContentRef;
    }

    // 调测tip
    if (!isKnownStatus && is_auth_configured === true && this.showDebugIcon) {
      return this.debugTipContentRef;
    }

    if (!isKnownStatus && is_auth_configured === false) {
      return this.tipContentRef;
    }

    return undefined;
  }

  gotoDebug(item) {
    this.router.navigate(['/home//model/model-test'], {
      queryParams: {
        id: item?.id,
        modelType: item?.model_type,
      }
    })
  }

  /**
   * 查询MaaS模型的开通状态
   */
  private getMaaSModalSubscribe() {
    this.modelManagementService.getMaaSModalSubscribe(this.refreshSubscribe).then(res => {
      this._subscribeMap.set(res);
    });
  }
}
