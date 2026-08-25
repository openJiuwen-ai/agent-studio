import { CommonModule } from '@angular/common';
import { Component, ViewChild, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { v4 as uuidV4 } from 'uuid';
import { ModelType } from '@enums/jiuwen-model.enum';
import { I18nNamespace } from '@i18n';
import { Network } from '@model';
import { LLMSelectComponent } from "@routes/agent-center/app-flow/components/llm-select/llm-select.component";
import { Image2textOutputComponent } from '@routes/model-management/online-test/components/image2text/image2text-output/image2text-output.component';
import { TextEmbeddingComponent } from '@routes/model-management/online-test/components/text-embedding/text-embedding.component';
import { TextRerankComponent } from '@routes/model-management/online-test/components/text-rerank/text-rerank.component';
import { getNewServiceKeyList } from "@routes/model-management/router-policy-detail/router-common";
import { EnvManagementService } from '@routes/platform-management/environment-management/env-management.service';
import { EnvironmentVariablesManagementService } from '@routes/platform-management/environment-variables-management/environment-variables-management.service';
import { ModelManagementService } from "@services/repositories/model-management-new";
import { ModelRouterStrategiesService } from '@services/repositories/model-router-strategies';
import { JiuwenModelService } from '@services/jiuwen-model/jiuwen-model.service';
import { MODULES } from '@shared/modules';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { cdnAssetUrl } from '../../../single-spa/assets-url';
import { CommonUtils } from "../../../utils/common.util";
import { ModelServiceCompareRouter } from './components/model-service-compare-router/model-service-compare-router.component';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzSwitchModule } from 'ng-zorro-antd/switch';
import { NzRadioModule } from 'ng-zorro-antd/radio';
import { NzSliderModule } from 'ng-zorro-antd/slider';
import { NzInputNumberModule } from 'ng-zorro-antd/input-number';
import { NzUploadModule, NzUploadFile } from 'ng-zorro-antd/upload';
import { NzGridModule } from 'ng-zorro-antd/grid';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzInputModule } from 'ng-zorro-antd/input';
import { FormsModule } from '@angular/forms';
import { NzMessageService } from 'ng-zorro-antd/message';

@Component({
  selector: 'meta-online-test',
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    ModelServiceCompareRouter,
    Image2textOutputComponent,
    TextEmbeddingComponent,
    TextRerankComponent,
    LLMSelectComponent,
    FormsModule,
    NzButtonModule,
    NzSwitchModule,
    NzRadioModule,
    NzSliderModule,
    NzInputNumberModule,
    NzUploadModule,
    NzGridModule,
    NzSpinModule,
    NzIconModule,
    NzToolTipModule,
    NzInputModule
  ],
  templateUrl: './online-test.component.html',
  styleUrls: ['./online-test.component.scss'],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.MODEL_ACCESS],
    },
  ],
})
export class OnlineTestComponent implements OnInit, OnDestroy {
  public isLoading = false;

  constructor(
    private modelRouterStrategiesService: ModelRouterStrategiesService,
    private jiuwenModelServ: JiuwenModelService,
    private route: ActivatedRoute,
    private i18n: I18NextEagerPipe,
    private sidebarVisibilityServ: SetSidebarVisibilityService,
    private modelManagementService: ModelManagementService,
    private message: NzMessageService,
    private envManagementServ: EnvManagementService,
    private envVariablesMgmtServ: EnvironmentVariablesManagementService,
    private cdr: ChangeDetectorRef,
  ) {}

  public providerInfo: any = {};
  public routerPolicyInfo: any = {};
  public serviceTypeOptions: any = [
    {
      value: ModelType.LLM,
      text: this.i18n.transform('LLM'),
      icon: `${Network.ASSETS_PATH}model/chat.svg`,
    },
    {
      value: ModelType.IMAGE_TO_TEXT,
      text: this.i18n.transform('IMAGE-TO-TEXT'),
      icon: `${Network.ASSETS_PATH}model/image2text.svg`,
    },
    {
      value: ModelType.Text_Embedding,
      text: this.i18n.transform('Text-Embedding'),
      icon: `${Network.ASSETS_PATH}model/text-embedding.svg`,
    },
    {
      value: ModelType.RERANK,
      text: this.i18n.transform('RERANK'),
      icon: `${Network.ASSETS_PATH}model/reRank.svg`,
    },
  ];
  public modelType: string = ModelType.LLM;
  public model_list_options: Array<any> = [
    { label: this.i18n.transform('model_service_api'), children: [] },
    { label: this.i18n.transform('preset_model_api'), children: [] },
    { label: this.i18n.transform('my_model_api'), children: [] },
    { label: this.i18n.transform('my_route_policy'), children: [] },
  ];
  public radioList: Array<any> = [
    { id: '1', label: this.i18n.transform('non_streaming'), value: false, disabled: false },
    { id: '2', label: this.i18n.transform('streaming'), value: true, disabled: false },
  ];
  public envPlaceholderVars: Array<{name: string, value: string}> = [];
  /** 缓存的环境变量值Map，避免每次变更检测都重新创建 */
  public envVarValuesMap: Record<string, string> = {};
  // 匹配后台返回格式${_env.plugin_url_params.VAR_NAME}提取变量名
  private readonly ENV_PLACEHOLDER_REGEX = /\$\{_env\.plugin_url_params\.([a-zA-Z_$][a-zA-Z0-9_$]*)\}/g;

  /** 默认环境 id（缓存，组件生命周期内复用）；undefined=无默认环境或未加载 */
  public defaultEnvId: string | undefined;
  /** 默认环境的变量名集合（缓存）；undefined=未加载，空 Set=已加载但无变量 */
  public defaultEnvVarNames: Set<string> | undefined;
  /** 是否正在加载/校验默认环境变量 */
  public defaultEnvChecking = false;

  public mySelected: any;
  public selectedMap: any = {
    '0': { id: '' },
    '1': { id: '' }
  };
  public serviceMap: any = {};
  public isMultiple = true;
  public limit = 2;
  public uniKey = 'id';
  public stream_val = true;
  public showThink = false;
  public settingInfo = {
    stream_val: true,
    securityVerify: false,
    thinking: true,
  };
  filterInfo = {
    publish_status: 'all',
  }
  public isManage = true;

  configs: Array<any> = [
    {
      name: 'max_tokens',
      value: 2048,
      inputValue: 2048,
      min: 100,
      max: 32768,
      step: 1,
      scales: [100, 32768],
      title: this.i18n.transform('limit_max_tokens'),
      desc: this.i18n.transform('max_tokens_desc')
    },
    {
      name: 'temperature',
      title: this.i18n.transform('temperature'),
      min: 0.01,
      max: 2,
      step: 0.01,
      value: 0.5,
      inputValue: 0.5,
      scales: [0.01, 2],
      desc: this.i18n.transform('temperature_desc'),
    },
    {
      name: 'top_p',
      title: this.i18n.transform('diversity'),
      min: 0,
      max: 1,
      step: 0.1,
      value: 0.5,
      inputValue: 0.5,
      scales: [0, 1],
      desc: this.i18n.transform('top_p_desc'),
    },
    {
      name: 'presence_penalty',
      title: this.i18n.transform('exist_penalty'),
      min: -2,
      max: 2,
      step: 0.1,
      value: 0,
      inputValue: 0,
      scales: [-2, 2],
      desc: this.i18n.transform('presence_penalty'),
    },
    {
      name: 'frequency_penalty',
      title: this.i18n.transform('frequency_penalty'),
      min: -2,
      max: 2,
      step: 0.1,
      value: 0,
      inputValue: 0,
      scales: [-2, 2],
      desc: this.i18n.transform('frequency_penalty_desc'),
    },
  ];

  toggleModel = false;

  changeServiceType(item: any) {
    if(item?.value !== ModelType.Text_Embedding){
      this.textEmbeddingParam.content = '';
    }
    if(item?.value !== ModelType.RERANK){
      this.textRerankParam = {
        textsToRerank: [{ content: '' }],
        numOfDisplay: 1,
        question: '',
      }
    }

    if (item?.value !== ModelType.IMAGE_TO_TEXT) {
      this.image2textParam = {
        uploadData: [],
        content: '',
      };
      this.fileList = [];
    }

    this.toggleModel = !this.toggleModel;
    this.modelType = item?.value;
    this.initModelOption();
  }

  onPageBack() {
    window.history.back();
  }

  initModelOption() {
    this.isMultiple = this.modelType === ModelType.LLM;
    this.mySelected = null;
    this.serviceMap = {};
    this.filterModelList();

    if(this.modelType === 'IMAGE-TO-TEXT'){
      this.settingInfo.stream_val = false;
    }
  }

  getRouterPolicyDetail() {
    const serviceId = this.route?.snapshot?.queryParams?.id;
    if (!serviceId) return;

    this.modelRouterStrategiesService.getModelRouterStrategiesDetail(serviceId).then((res: any) => {
      res.last_updated_date = CommonUtils.getDateToString(res.last_updated_date);
      res.created_date = CommonUtils.getDateToString(res.created_date);
      const _service_key_list = getNewServiceKeyList(res.service_list);
      res.service_key_list = _service_key_list.join(' | ');
      this.routerPolicyInfo = res ?? {};
    });
  }

  filterModelList() {
    let with_router = false;
    if (this.modelType === ModelType.LLM) {
      with_router = true;
    }
    this.modelManagementService.getAvailableModelList(
      { model_type: this.modelType, with_router: with_router }).then((res) => {

      const _services = res.data ?? [];
      if(_services.length){
        _services.forEach((service) => {
          const _id = service[this.uniKey];
          this.serviceMap[_id] = {...service, name: service.service_name};
        });
        const serviceId = this.route?.snapshot?.queryParams?.id;
        if (serviceId) {
          this.mySelected = this.isMultiple ? [this.serviceMap[serviceId]] : this.serviceMap[serviceId];
          this.selectedMap[0] = this.serviceMap[serviceId];
        }
        for (let services of _services) {
          if (this.mySelected !== null) break;

          if (_services.length > 0) {
            let serviceInfo = {..._services[0], name: _services[0].service_name};
            this.mySelected = this.isMultiple ? [serviceInfo] : serviceInfo;
            this.selectedMap[0] = serviceInfo;
            break;
          }
        }
        this.initThinking();
        this.extractEnvPlaceholders();
      }
    });
  }

  generateOptions(service) {
    return {
      label: service.service_name,
      name: service.service_name,
      logo: service.logo ?? `${Network.ASSETS_PATH}model/assist.svg`,
      id: service[this.uniKey],
      service_name: service.service_name,
      service_key: service.service_key,
      is_support_function: service.is_support_function,
    };
  }

  generateStrategyOptions(service) {
    return {
      label: service.strategy_name,
      name: service.strategy_name,
      logo: service.logo ?? `${Network.ASSETS_PATH}model/assist.svg`,
      id: service[this.uniKey],
      service_key: service.strategy_key,
    };
  }

  getProvidersInfo(source: string, id: string) {
    this.jiuwenModelServ.getModelProvidersInfo(source, id).then((res) => {
      this.providerInfo = res;
    });
  }

  /**
   * 图像理解
   */
  @ViewChild('image2text') image2text: Image2textOutputComponent;
  @ViewChild('textEmbedding') textEmbedding: TextEmbeddingComponent;
  @ViewChild('textRerank') textRerank: TextRerankComponent;

  fileList: NzUploadFile[] = [];

  image2textParam: any = {
    uploadData: [],
    content: '',
  };

  get Image2TextButtonTip(){
    if(this.hasInvalidEnvVar()){
      return this.i18n.transform('env_var_not_ready_tip')
    }
    if(!this.mySelected?.id){
      return this.i18n.transform('select_model_first')
    }
    if(this.image2textParam.uploadData.length === 0){
      return this.i18n.transform('upload_image_first')
    }

    if(!this.image2textParam.content){
      return this.i18n.transform('input_prompt_content')
    }
    return ''
  }

  get EmbeddingButtonTip(){
    if(this.hasInvalidEnvVar()){
      return this.i18n.transform('env_var_not_ready_tip')
    }
    if(!this.mySelected?.id){
      return this.i18n.transform('select_model_first')
    }
    if(this.textEmbeddingParam.content.length === 0){
      return this.i18n.transform('please_input_text')
    }
    return ''
  }

  get RerankButtonTip(){
    if(this.hasInvalidEnvVar()){
      return this.i18n.transform('env_var_not_ready_tip')
    }
    if(!this.mySelected?.id){
      return this.i18n.transform('select_model_first')
    }
    if(this.textRerankParam?.question.trim() === ''){
      return this.i18n.transform('please_input_question')
    }

    let hasEmptyText = false;
    for (let item of this.textRerankParam.textsToRerank) {
      if (item.content?.trim() === '') {
        hasEmptyText = true;
      }
    }
    if (hasEmptyText) {
      return this.i18n.transform('please_input_text_to_sort_1')
    }
    return ''
  }

  triggerImage2Text() {
    if (this.hasInvalidEnvVar()) {
      this.message.warning(this.i18n.transform('env_var_not_ready_tip'));
      return;
    }
    this.image2text.sendQuestion();
  }

  beforeUploadImage2Text = (file: NzUploadFile): boolean => {
    const isValidType = file.type === 'image/jpeg' || file.type === 'image/png';
    if (!isValidType) {
      this.message.error(this.i18n.transform("unsupported_file_type"));
      return false;
    }
    const isValidSize = file.size! / 1024 / 1024 < 4;
    if (!isValidSize) {
      this.message.error(this.i18n.transform("unsupported_file_type_1"));
      return false;
    }

    const reader = new FileReader();
    reader.readAsDataURL(file as any);
    reader.onload = () => {
      const url = reader.result;
      const uuid = uuidV4();
      file.uid = uuid;
      this.image2textParam.uploadData.push({
        url,
        type: file.type,
        uuid,
      });
      this.fileList = [...this.fileList, file];
    };
    return false;
  };

  onRemoveItemsNz = (file: NzUploadFile): boolean => {
    const index = this.image2textParam.uploadData.findIndex((d: any) => d.uuid === file.uid);
    if (index !== -1) {
      this.image2textParam.uploadData.splice(index, 1);
    }
    return true;
  };

  changeValue(config) {
    config.inputValue = config.value;
  }

  changeInputValue(config) {
    if (config.inputValue > config.max) {
      config.inputValue = config.max;
    }
    if (config.inputValue < config.min) {
      config.inputValue = config.min;
    }
    config.value = config.inputValue;
    this.configs = JSON.parse(JSON.stringify(this.configs));
  }

  /**
   * 文本向量化
   */
  textEmbeddingParam = {
    content: '',
  };
  textEmbeddingTips = this.i18n.transform('embedding_example');

  triggerTextEmbedding() {
    if (this.hasInvalidEnvVar()) {
      this.message.warning(this.i18n.transform('env_var_not_ready_tip'));
      return;
    }
    this.textEmbedding.sendQuestion();
  }

  /**
   * 文本排序
   */
  maxTextRerankNum = 10;

  textRerankParam: any = {
    textsToRerank: [{ content: '' }],
    numOfDisplay: 1,
    question: '',
  };

  triggerTextRerank() {
    if (this.hasInvalidEnvVar()) {
      this.message.warning(this.i18n.transform('env_var_not_ready_tip'));
      return;
    }
    this.textRerank.sendQuestion();
  }

  addTextToRerankItem() {
    if (this.textRerankParam.textsToRerank.length >= this.maxTextRerankNum) return;
    this.textRerankParam.textsToRerank.push({ content: '' });
  }

  removeTextToRerankItem(targetIndex: number) {
    if (this.textRerankParam.textsToRerank.length <= 1) return;
    this.textRerankParam.textsToRerank.splice(targetIndex, 1);
  }

  ngOnInit() {
    const _value = '_value';
    this.modelType = this.route.queryParams[_value].modelType || ModelType.LLM;
    this.initModelOption();
    if (!this.isManage) {
      this.sidebarVisibilityServ.setSidebarsVisibilityByState('init');
    }
  }

  ngOnDestroy() {
    if (!this.isManage) {
      this.sidebarVisibilityServ.setSidebarsVisibilityByState('destroy');
    }
  }

  public updateModel(item: any) {
    this.mySelected = [];
    if(item.modelInfo){
      this.selectedMap[item.index] = {
        name: item.modelInfo.service_name,
        ...item.modelInfo
      };
    } else {
      this.selectedMap[item.index].id = '';
    }

    Object.entries(this.selectedMap).forEach((key, data) => {
      if(this.selectedMap[data as any].id){
        const { logo } = this.selectedMap[data as any];
        this.mySelected.push({
          ...this.selectedMap[data as any],
          logo: logo || cdnAssetUrl('assets/model/default_model_detail.svg')
        });
      }
    });

    if(this.isMultiple){
      this.mySelected = [...this.mySelected];
    } else {
      this.mySelected = this.mySelected[0];
    }
    this.extractEnvPlaceholders();
    this.initThinking();
  }

  /**
   * 从选中的模型api_url中提取环境变量占位符
   */
  extractEnvPlaceholders() {
    const varSet = new Set<string>();
    const models = Array.isArray(this.mySelected) ? this.mySelected : (this.mySelected ? [this.mySelected] : []);

    models.forEach(model => {
      if (!model?.api_url) return;
      let match;
      const regex = new RegExp(this.ENV_PLACEHOLDER_REGEX.source, 'g');
      while ((match = regex.exec(model.api_url)) !== null) {
        varSet.add(match[1]);
      }
    });

    this.envPlaceholderVars = Array.from(varSet).map(name => ({
      name,
      value: '',
    }));
    // 占位符变量值由后端按「默认环境」自动解析，前端不再收集手填值。
    this.envVarValuesMap = {};

    // 选中含占位符的模型时，异步加载默认环境上下文（取默认环境 id + 变量名集合），
    // 完成后据变量名是否在默认环境，渲染「自动注入」或「未配置」提示。
    if (this.envPlaceholderVars.length > 0) {
      this.ensureDefaultEnvContext();
    }
  }

  /**
   * 懒加载默认环境上下文（幂等）：取默认环境 id → 取其变量名集合。
   * 无默认环境时 defaultEnvId=undefined、defaultEnvVarNames=空 Set，不报错。
   */
  ensureDefaultEnvContext() {
    // 已加载过则直接返回
    if (this.defaultEnvVarNames !== undefined) {
      return;
    }
    this.defaultEnvChecking = true;
    this.envManagementServ.getEnvironmentList({ offset: 0, limit: 99 }).then((res: any) => {
      const defaultEnv = (res?.env_info || []).find((e: any) => e.isDefault);
      this.defaultEnvId = defaultEnv?.id;
      if (!this.defaultEnvId) {
        // 无默认环境：变量名集合置空 Set（已加载），所有占位符变量都判为「未配置」
        this.defaultEnvVarNames = new Set<string>();
        this.defaultEnvChecking = false;
        this.cdr.markForCheck();
        return;
      }
      // 取默认环境的变量名集合（name 不脱敏，可用于判断存在性）
      this.envVariablesMgmtServ.getEnvVariablesDetail(this.defaultEnvId).then((varRes: any) => {
        this.defaultEnvVarNames = new Set<string>((varRes?.variables || []).map((v: any) => v.name));
        this.defaultEnvChecking = false;
        this.cdr.markForCheck();
      }).catch(() => {
        this.defaultEnvVarNames = new Set<string>();
        this.defaultEnvChecking = false;
        this.cdr.markForCheck();
      });
    }).catch(() => {
      this.defaultEnvVarNames = new Set<string>();
      this.defaultEnvChecking = false;
      this.cdr.markForCheck();
    });
  }

  /**
   * 占位符变量名是否在默认环境中配置（将由后端按默认环境自动解析）。
   * defaultEnvVarNames 未加载完成时返回 false（保守，期间 hasMissingEnvVar 会判为缺失并禁用发送）。
   */
  isVarInDefaultEnv(name: string): boolean {
    return this.defaultEnvVarNames?.has(name) ?? false;
  }

  /**
   * 是否存在「未在默认环境配置」的占位符变量（任一缺失即禁用发送，引导用户去默认环境配置）。
   */
  hasMissingEnvVar(): boolean {
    return this.envPlaceholderVars.length > 0 &&
      this.envPlaceholderVars.some(item => !this.isVarInDefaultEnv(item.name));
  }

  /**
   * 环境变量是否就绪（免填方案下的发送守卫）：存在缺失变量、或默认环境上下文仍在加载时为 true。
   * 保留原方法名以复用现有发送守卫/按钮禁用/[envVarReady] 绑定，语义由「URL非法」改为「默认环境未就绪」。
   */
  hasInvalidEnvVar(): boolean {
    return this.hasMissingEnvVar() || this.defaultEnvChecking;
  }

  initThinking(){
    this.showThink = false;
    this.settingInfo.thinking = true;
    Object.entries(this.selectedMap).forEach((key, data) => {
      if(this.selectedMap[data as any].is_support_close_reasoning){
        this.showThink = true;
      }
    });
  }

  protected readonly ModelType = ModelType;
  protected readonly changeUrl = cdnAssetUrl;
}
