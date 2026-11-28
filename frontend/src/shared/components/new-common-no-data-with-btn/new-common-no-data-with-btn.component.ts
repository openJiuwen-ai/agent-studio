import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { CommonService } from '@services/common.service';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { HttpService } from '@services/http.service';

const tutorialTypeMapUrl = {
  mcp: 'help_add_mcp',
  plugin: 'help_add_plugin',
};


@Component({
  selector: 'app-new-common-no-data-with-btn',
  templateUrl: './new-common-no-data-with-btn.component.html',
  styleUrls: ['./new-common-no-data-with-btn.component.less'],
  imports: [MODULES],
  standalone: true,
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.PROMPT_PLATFORM,
        I18nNamespace.COMMON,
        I18nNamespace.AGENT_CENTER,
        I18nNamespace.MODEL_ACCESS,
        I18nNamespace.TRACE,
        I18nNamespace.REVIEW,
        I18nNamespace.MEMORY_LIB,
      ],
    },
  ],
})
export class NewCommonNoDataWithBtnComponent {
  @Input() isOnlyShowBtn = false; // 无数据时只显示按钮
  @Input() btn_list = [];
  @Input() tutorialType = '';
  @Input() type = 'noData';
  @Input() noDataStr = '';
  @Input() createStr = '';
  @Input() extraStr = '';
  @Input() noDataBtnStr = '';
  @Input() firstLineData = '';
  @Input() secondLineData = '';
  @Input() secondLineClickData = '';
  @Input() hideSecondLineData = false;
  @Input() filterNoData = this.i18n.transform('no_data_matched');
  @Input() filterNoSecondData = this.i18n.transform('no_matching_data_found');
  @Input() filterBtn = this.i18n.transform('clear_filters');
  @Output() create = new EventEmitter<void>();
  @Output() clear = new EventEmitter();

  resourceTypeMapUrl = {
    agentTitle:this.i18n.transform('agent_title'),
    defaultTitle:this.i18n.transform(''),
    tagTitle:this.i18n.transform('tag_mgn'),
    datasetTitle:this.i18n.transform('dataset_title'),
    evalTaskTitle:this.i18n.transform('evaluation_task'),
    assessorSubTitle:this.i18n.transform('evaluator_title'),
    mcp: 'MCP',
    plugin: this.i18n.transform('plugin'),
    workflow: this.i18n.transform('workflow'),
    high: this.i18n.transform('high'),
    DataProcess: this.i18n.transform('processing_node'),
    DataSynthesis: this.i18n.transform('newcommonnodatawithbtncomponent_53'),
    singleQuestion: this.i18n.transform('single_agent'),
    multiQuestion: this.i18n.transform('multiple_agent'),
    messageTem: this.i18n.transform('message_template'),
    prompt: this.i18n.transform('prompt'),
    optimizationTask: this.i18n.transform('optimize_task'),
    modelSupplier: this.i18n.transform('model_supplier'),
    routPolicy: this.i18n.transform('route_policy'),
    knowledgeBase: this.i18n.transform('knowledge_base'),
    objectTem:this.i18n.transform('object_template'),
    memoryLib: this.i18n.transform('memory.management.title'),
  }

  ThirdLineData = '';
  tutorialUrl = '';
  subscribeBtnStatus = this.commonService.getSubscribeStatus();
  private subscribeBtnStatusSubscription:Subscription

  is_white_list = false;

  get extraBuyResource() {
    //排除不需要加载购买资源的按钮的页面
    return ['modelSupplier', 'routPolicy'].includes(this.tutorialType);
  }
  constructor(
    public commonService: CommonService,
     private router: Router,
    private readonly http: HttpService,
    private i18n: I18NextEagerPipe,
  ) {
    this.subscribeBtnStatusSubscription = this.http.getResourceWhiteList().subscribe(res=>{
      this.is_white_list = res
    })
  }
  ngOnInit(): void {
    if (this.tutorialType) {

      this.firstLineData = this.i18n.transform('no_resource_available',{type:this.resourceTypeMapUrl[this.tutorialType]});
      this.secondLineData = this.i18n.transform('no_data_available_create_resource',{type:this.resourceTypeMapUrl[this.tutorialType]});
    }
  }
  ngOnDestroy() {
    if(this.subscribeBtnStatusSubscription){
      this.subscribeBtnStatusSubscription.unsubscribe()
    }
  }

  goTutorial() {
    window.open(this.tutorialUrl, '_blank');
  }


  onCreate() {
    this.create.emit();
  }

  onClear() {
    this.clear.emit();
  }

  goToBuy() {

  }
  btn_list_fn(info){
    this.create.emit(info);
  }
}
