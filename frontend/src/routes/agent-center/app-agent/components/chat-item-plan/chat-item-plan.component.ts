import {
  Component, EventEmitter,
  Input,
  OnDestroy, Output,
  SimpleChanges, ViewChild,
} from '@angular/core';
import {CommonModule} from '@angular/common';
import {MODULES} from '@shared/modules';
import {I18nNamespace} from '@i18n';
import {I18NEXT_NAMESPACE} from 'angular-i18next';
import {
  ConversationContent,
  FuncCallItem,
  TimeConsumption,
  TimeConsumptionStr,
} from '@routes/agent-center/types/my-workspace.types';
import {AppMarkdownAnswerComponent} from '@shared/components/app-markdown-answer/app-markdown-answer.component';
import {AssetQuoteIconComponent} from '@shared/components/assets/asset-quote-icon/asset-quote-icon.component';
import {CustomPopconfirmComponent} from '@shared/components/custom-popconfirm/custom-popconfirm.component';
import {ClickOutsideDirective} from '@shared/directives/click-outside.directive';
import {UploadFileIconComponent} from '@shared/components/upload-file-icon/upload-file-icon.component';
import {TtsPlayerService} from '@services/tts-player.service';
import {ChatItemComponent} from "@routes/agent-center/app-agent/components/chat-item/chat-item.component";
import {SafeHtmlPipe} from "../../../../../pipes/safehtml.pipe";
import {cdnAssetUrl} from "../../../../../single-spa/assets-url";
import {InputNodeParamsComponent} from "@shared/components/input-node-params/input-node-params.component";

@Component({
  selector: 'chat-item-plan',
  templateUrl: './chat-item-plan.component.html',
  styleUrls: ['./chat-item-plan.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    CustomPopconfirmComponent,
    AppMarkdownAnswerComponent,
    AssetQuoteIconComponent,
    ClickOutsideDirective,
    UploadFileIconComponent,
    SafeHtmlPipe,
    InputNodeParamsComponent,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.TRACE],
    },
    TtsPlayerService,
  ],
})
export class ChatItemPlanComponent extends ChatItemComponent implements OnDestroy {

  public curAnswer: (ConversationContent | FuncCallItem)

  public collapsed: boolean = true

  public thoughtFinished: boolean = false
  public dialogHistoryUpdate: any;

  public printText:string=''
  @Input() isFinished: boolean = false;

  // 本轮是否已有答案正文，控制停止提示的展示位置
  public roundHasAnswer = false;

  @ViewChild('inputNodeParams')
  inputNodeParamsComp!: InputNodeParamsComponent;

  @Input() index:number = 0
  @Output('confirm') confirm = new EventEmitter<any>();
  @Output('resendQuestionItem') resendQuestionItem = new EventEmitter<void>();
  public hasTool:boolean=false

  override ngOnChanges(changes: SimpleChanges): void {
    if (changes.data) {

      const data = changes.data.currentValue;
      // 过滤掉 role 等于 "followUpQuestions" 的对象
      const filteredData = data?.filter(
        (item) => item.role !== 'followUpQuestions',
      );
      this.dialogHistoryUpdate = this.dealCvList(filteredData);
      this.sourceFiles = this.aiAnswerListService.filterSourceFile(this.dialogHistoryUpdate);
    }
  }

  override changeCollapsedState(answer?:any) {
    if(answer){
      answer.collapsed = !answer.collapsed
    }else{
      this.collapsed = !this.collapsed
    }

  }


  override dealCvList(list: any[]) : any{
    list = [...new Set(list)];
    let newList: Array<
      (ConversationContent | FuncCallItem) & {
      timeConsumptionStr: TimeConsumptionStr;
    }
    > = [];

    // 本轮是否已有答案正文（有的话停止提示只显示在答案底部，避免计划区重复显示）
    this.roundHasAnswer = list.some(
      (item) => item?.role === 'assistant' && item?.content && item?.event !== 'error'
    );

    for (let i = 0; i < list.length; i++) {
      const item = list[i];
      if (
        item.event !== 'function_call_end' &&
        item.event !== 'api_exec_data'
      ) {
        if (item.event) {
          this.hasTool = true
        }
        const data = item as ConversationContent & {
          timeConsumptionStr: TimeConsumptionStr;
        };
        data.timeConsumptionStr = this.getTimeDelayStr(data.time_consumption);
        data.dialogId = this.index.toString()
        newList.push(data)
      }
    }
    return [...newList];
  }


  override getTimeDelayStr(
    time_consumption: (TimeConsumption & { totalEx?: number }) | undefined,
  ) {
    let timeDelayRes = {} as TimeConsumptionStr;
    if (time_consumption === undefined) {
      return timeDelayRes;
    }
    if (
      time_consumption.overall_latency !== undefined &&
      time_consumption.overall_latency !== null
    ) {
      timeDelayRes.total_latency_str = `${this.i18n.transform(
        'total_latency',
      )} ${time_consumption.overall_latency}s `;
    } else {
      timeDelayRes.total_latency_str = '';
    }

    if (
      time_consumption.overall !== undefined &&
      time_consumption.overall !== null
    ) {
      timeDelayRes.overall_str = `${this.i18n.transform('run_time')} <span style='color:#000'>${
        time_consumption.overall
      }s</span>`;
    } else {
      timeDelayRes.overall_str = '';
    }

    return timeDelayRes;
  }
  public handleCollapsedChat(item) {
    item.collapsed = !item?.collapsed
  }

  public onFileUploadStatus(state: string, ans: any) {
    if (state === 'loading') {
      ans.isConfirmed = 'not-prepared';
    } else if (state === 'failed') {
      ans.isConfirmed = 'failed';
    } else {
      ans.isConfirmed = ans?.inputList.some((inputItem) => inputItem.failed)
        ? 'failed'
        : 'not-confirmed';
    }
  }

  public onConfirm(ans: any, item: any) {
    // 根据输入节点必填 非必填，动态进行校验
    let isInputNodeParamsPass = true;

    let inputs;
    if (ans?.inputList && ans?.inputList.length > 0) {
          inputs = ans?.inputList;
    }
    isInputNodeParamsPass = this.inputNodeParamsComp
      ? this.inputNodeParamsComp.checkInput(inputs)
      : true;
    if (!isInputNodeParamsPass) {
      return;
    }
    ans.isConfirmed = 'confirmed';
    this.previewDebugServ.setSendMeta(true)
    const inputData = this.inputNodeParamsComp?.getDynamicParams(this.index.toString());
    const keys = Object?.keys(inputData || {});
    keys.forEach((key) => {
      const param = inputData[key];
      if (param instanceof Array) {
        inputData[key] = JSON.stringify(inputData[key].map((obj) => obj.url));
      }
    });
    this.confirm.emit({ role:'user',content: this.getFormattedData(inputData) })

  }
  protected readonly cdnAssetUrl = cdnAssetUrl;

  /** 获取输入节点的表单key-value，并转换为包含:和\n的字符串，作为run接口的入参 */
  protected getFormattedData(inputData: any) {
    const entries = Object.entries(inputData ?? {}).map(([key, value]) => {
      const formattedValue = value === null ? '' : value;
      return `${key}:${formattedValue}`;
    });
    return entries.join('\n');
  }

  resendQuestion() {
    this.resendQuestionItem.emit();
  }
}
