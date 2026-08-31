import { Component } from '@angular/core';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { Subject, catchError, forkJoin, from, of, switchMap } from 'rxjs';
import { CommonModule } from '@angular/common';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { ModelManagementService } from '@services/repositories/model-management-new';
import { MarkdownComponent } from 'ngx-markdown';
import { ActivatedRoute, Router } from '@angular/router';
import { CommonUtils } from '../../../utils/common.util';
import { convertModelApiUrlToUserFormat, hasEnvPlaceholder } from '../../../utils/model-api-url.util';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { statusNewMap } from '@constants/status';
import { DeleteModalComponent } from '@routes/model-management/delete-modal/delete-modal.component';
import { AddModelComponent } from '@routes/model-management/components/add-model/add-model.component';
import { CommonService } from '@services/common.service';
import { HttpService } from '@services/http.service';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { ModelSquareService } from '@routes/model-square/model-square.service';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzDrawerService } from 'ng-zorro-antd/drawer';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzTagModule } from 'ng-zorro-antd/tag';

@Component({
  selector: 'model-detail',
  templateUrl: './model-detail.component.html',
  styleUrls: ['./model-detail.component.scss'],
  standalone: true,
  imports: [CommonModule, MODULES, MarkdownComponent, NzToolTipModule, NzIconModule, NzTagModule],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.COMMON, I18nNamespace.AGENT_CENTER, I18nNamespace.MODEL_ACCESS, I18nNamespace.JIUWEN_MODEL],
    },
  ],
})
export class ModelDetailComponent {
  public activeName: string = '';
  // 是否来自于开发者空间
  public isFromDevelopSpace: boolean = false;
  public lang = CommonUtils.getLanguage();
  private readonly destroy$ = new Subject<void>();
  public changeUrl = cdnAssetUrl;
  public iconNoneEmpty = cdnAssetUrl('assets/model/default_model_detail.svg');
  public modelId = '';
  prefix: string = '/v1';
  public infoDetail: any = {
    model_name: '',
    logo: '',
    readme: '',
    service_name: '',
    last_updated_date: '',
    created_date: '',
    created_by_user: '',
    model_type: '',
    interface_protocol: '',
    api_url: '',
    is_support_stream: false,
    is_support_function: false,
    model_description: '',
    model_tags: '',
    domain_id: '',
    throttling_policy: 0,
    publish_status: '',
    is_network: false,
    is_reasoning: false,
    auth_id: '',
    provider_id: '',
    is_public: false,
    provider_name: '',
    provider_name_en: '',
  };
  newTypeMeta = {
    LLM: this.i18n.transform('LLM'),
    'Text-Embedding': this.i18n.transform('Text-Embedding'),
    'TEXT-TO-IMAGE': this.i18n.transform('TEXT-TO-IMAGE'),
    'IMAGE-TO-TEXT': this.i18n.transform('IMAGE-TO-TEXT'),
    'AUDIO-TO-TEXT': this.i18n.transform('AUDIO-TO-TEXT'),
    'RERANK': this.i18n.transform('RERANK'),
    'TEXT-TO-AUDIO': this.i18n.transform('TEXT-TO-AUDIO'),
    'TEXT-TO-VIDEO': this.i18n.transform('TEXT-TO-VIDEO'),
    'Text-Multimodal-Embedding': this.i18n.transform(`${I18nNamespace.PLATFORM_MANAGEMENT}:model_multimodal_embedding`),
  };

  public tagMap = {
    'is_support_function': {
      name: this.i18n.transform('tag_tool'),
      color: 'rgb(255,235,209)',
      text_color: 'rgb(217,105,0)',
      icon: 'assets/images/tag/is_tool.svg',
    },
    'is_reasoning': {
      name: this.i18n.transform('tag_reasoning'),
      color: 'rgb(244,224,252)',
      text_color: 'rgb(131,47,214)',
      icon: 'assets/images/tag/is_think.svg',
    },
    'is_network': {
      name: this.i18n.transform('tag_network'),
      color: 'rgb(222,236,255)',
      text_color: 'rgb(20,118,255)',
      icon: 'assets/images/tag/is_network.svg',
    },
  };

  public loading = false;

  public _value = '_value';
  public isOpAccount = false;
  protocolMap = {};
  public options2 = [];
  subscribeBtnStatus = this.commonService.getSubscribeStatus();

  constructor(
    private readonly i18n: I18NextEagerPipe,
    private route: ActivatedRoute,
    private router: Router,
    private modal: NzModalService,
    private drawer: NzDrawerService,
    private message: NzMessageService,
    private modelManagementService: ModelManagementService,
    private sidebarVisibilityServ: SetSidebarVisibilityService,
    private readonly commonService: CommonService,
    private readonly http: HttpService,
    private configServ: AgentConfigService
  ) {}

  ngOnInit() {
    this.sidebarVisibilityServ.setSidebarsVisibilityByState('init');
    this.modelId = this.route.queryParams[this._value].id;

    this.getApiProtocol();
    this.getDetail();
    this.route.queryParams.subscribe(params => {
      if (params.from && params.from === 'develop-space') {
        this.isFromDevelopSpace = true;
      }
      this.getDetail();
    });
  }

  ngOnDestroy(): void {
    this.sidebarVisibilityServ.setSidebarsVisibilityByState('destroy');
    this.destroy$.next();
    this.destroy$.complete();
  }

  getProviderName() {
    if (this.lang === 'zh-cn') {
      return this.infoDetail.provider_name;
    } else {
      return this.infoDetail.provider_name_en;
    }
  }
  onPageBack() {
    window.history.back();
  }
  gotoModelList() {
    if (this.infoDetail?.domain_id) {
      this.router.navigate(['/home/model-square']);
      return;
    }
    if (this.isFromDevelopSpace) {
      this.router.navigate(['/home/develop-space'], {
        state: {
          currentNavigator: 'model',
        },
      });
      return;
    }
    this.router.navigate(['/home/model/management']);
  }

  setSystemTuneDisable(is_subscribed, is_in_free_trial): boolean {
    if (!this.subscribeBtnStatus) {
      return true;
    }
    if (is_in_free_trial) {
      return false;
    }
    if (this.infoDetail?.auth_id) {
      return !is_subscribed;
    }

    //无鉴权& 无免费token -- true
    return !this.infoDetail?.auth_id && !is_in_free_trial;
  }

  getDetail() {
    const { platform_provider_id } = this.configServ.getConfigs();
    const provider_id = platform_provider_id || '100';
    //  系统模型，需要通过列表接口，查询是否已开通
    from(this.modelManagementService.getModelInfo(this.modelId))
      .pipe(
        switchMap(modelInfo => {
          if (modelInfo.domain_id !== 'SYSTEM') {
            return of([modelInfo, null]);
          }
          return forkJoin([
            of(modelInfo),
            from(this.modelManagementService.getModelList({ service_name: modelInfo.service_name, provider_id })).pipe(catchError(err => of({}))),
          ]);
        })
      )
      .subscribe(([res, modelList]) => {
        res.last_updated_date = CommonUtils.getDateToString(res.last_updated_date);
        res.created_date = CommonUtils.getDateToString(res.created_date);
        // 将api_url转换为用户友好的{VAR}格式显示
        res.api_url = convertModelApiUrlToUserFormat(res.api_url);
        this.infoDetail = res ?? {};
        const selectModel = modelList?.data?.find(item => item.id === this.modelId);

        this.infoDetail.created_by_user = this.route.queryParams[this._value].activeName;
        if (res.domain_id === 'SYSTEM') {
          this.activeName = 'PLATFORM';
          this.options2 = ModelSquareService.NOT_ALLOW_TEST_TYPE.includes(this.infoDetail.model_type)
            ? []
            : [
                {
                  label: this.i18n.transform('tune_model'),
                  disabled: this.setSystemTuneDisable(selectModel?.is_subscribed, selectModel?.is_in_free_trial),
                  key: 'onlineTest',
                  disIcon: cdnAssetUrl('assets/model/test_model_gray.svg'),
                  icon: cdnAssetUrl('assets/model/test_model.svg'),
                },
              ];
        } else {
          this.activeName = 'CUSTOM';
          this.options2 = [
            {
              label: this.i18n.transform('tune_model'),
              disabled: !this.infoDetail.auth_id,
              key: 'onlineTest',
              disIcon: cdnAssetUrl('assets/model/test_model_gray.svg'),
              icon: cdnAssetUrl('assets/model/test_model.svg'),
            },
            {
              label: statusNewMap[this.infoDetail?.publish_status]?.operateText ?? statusNewMap.offline.operateText,
              key: 'stopGray',
              disabled: res.provider_id.startsWith('cdi-'),
              icon: cdnAssetUrl('assets/images/model/publish_b.svg'),
              disIcon: cdnAssetUrl('assets/images/model/dis_publish.svg'),
            },
            {
              label: this.i18n.transform('edit'),
              key: 'edit',
              icon: cdnAssetUrl('assets/images/model/edit_b.svg'),
              disIcon: cdnAssetUrl('assets/images/model/editGray.svg'),
              disabled: this.infoDetail?.publish_status === 'online',
            },
            {
              label: this.i18n.transform('delete'),
              key: 'delete',
              icon: cdnAssetUrl('assets/images/model/delete_b.svg'),
              disIcon: cdnAssetUrl('assets/images/model/deleteGray.svg'),
              disabled: this.infoDetail?.publish_status === 'online',
            },
          ];
        }
      });
  }

  public onSelect(event, item) {
    if (event.disabled) {
      return;
    }
    if (event.key === 'onlineTest') {
      this.goModelTest(item);
    } else if (event.key === 'stopGray') {
      this.changeModelStatus(item);
    } else if (event.key === 'edit') {
      this.openHalfModel(item);
    } else if (event.key === 'delete') {
      this.deleteModal(item);
    }
  }

  openHalfModel(model?) {
    const drawerRef = this.drawer.create({
      nzContent: AddModelComponent,
      nzWidth: '700px',
      nzPlacement: 'right',
      nzData: {
        title: model?.id ? this.i18n.transform('edit_model') : this.i18n.transform('add_model'),
        model_id: model?.id,
        provider_id: this.infoDetail.provider_id,
        context: {
          close: (): void => {
            this.getDetail();
            drawerRef.close();
          },
          dismiss: (): void => {
            drawerRef.close();
          },
        },
      },
    });

    drawerRef.afterClose.subscribe(() => {
      this.getDetail();
    });
  }

  changeModelStatus(data) {
    let query = {};
    if (data.publish_status === 'offline') {
      // 带环境变量占位符的模型，URL 运行期才解析，发布期可用性探测无意义，跳过 available_check
      query = hasEnvPlaceholder(data.api_url) ? {} : { available_check: true };
    }
    this.modelManagementService.publishModelInfo(data.id, data.publish_status === 'online' ? 'offline' : 'online', query).then((res: any) => {
      this.getDetail();
      this.message.success(
        data.publish_status === 'online' ? this.i18n.transform('model_service_unpublish_success') : this.i18n.transform('model_service_publish_success'),
        { nzDuration: 3000 }
      );
    });
  }

  public deleteModal(item) {
    const modalRef = this.modal.create({
      nzContent: DeleteModalComponent,
      nzWidth: '400px',
      nzFooter: null,
      nzData: {
        context: {
          id: item.id,
          title: this.i18n.transform('delete_model'),
          tip: `${this.i18n.transform('confirm_delete_model_service')} ${item.service_name}`,
          fnName: 'deleteModel',
          close: () => {
            this.message.success(this.i18n.transform('model_service_delete_success'), { nzDuration: 3000 });
            history.back();
            modalRef.close();
          },
        },
      },
    });
  }

  goModelTest(row) {
    this.router.navigate(['/home/development-configuration'], {
      queryParams: {
        activeName: row?.domain_id === 'SYSTEM' ? 'PLATFORM' : 'CUSTOM',
        providerId: row.provider_id,
        id: row.id,
        modelType: row.model_type,
        previousUrl: 'model-test',
      },
    });
  }

  getApiProtocol() {
    this.modelManagementService.getInterfaceProtocoList().then(res => {
      this.handelProtocoMap(res.data);
    });
  }

  handelProtocoMap(data) {
    data.forEach(item => {
      this.protocolMap[item.protocol] = this.lang === 'zh-cn' ? item.zh_name : item.en_name;
    });
  }
}
