import {
  ChangeDetectorRef,
  Component,
  HostListener,
  Input,
  OnDestroy,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChatSourceComponent } from '@routes/agent-center/app-agent/components/chat-source/chat-source.component';
import {
  SourceFileDetailComponent
} from '@routes/agent-center/app-agent/components/source-file-detail/source-file-detail.component';
import { KnowledgeRepoService } from '@services/agent-center/knowledge.service';
import { KbAnswerResolverService } from '@services/knowledge-center/kb-answer-resolver.service';
import { MODULES } from '@shared/modules';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { agentCommonLogic } from '../../../app-agent/common-logic-agent';
import {
  ConversationContent,
  FuncCallItem,
  TimeConsumption,
  TimeConsumptionStr,
} from '@routes/agent-center/types/my-workspace.types';
import { AppMarkdownAnswerComponent } from '@shared/components/app-markdown-answer/app-markdown-answer.component';
import { AssetFstLatencyIconComponent } from '@shared/components/assets/asset-fst-latency-icon/asset-fst-latency-icon.component';
import { AssetPluginLatencyIconComponent } from '@shared/components/assets/asset-plugin-latency-icon/asset-plugin-latency-icon.component';
import { AssetColorUserIconComponent } from '@shared/components/assets/asset-color-user-icon/asset-color-user-icon.component';
import { AssetQuoteIconComponent } from '@shared/components/assets/asset-quote-icon/asset-quote-icon.component';
import { CustomPopconfirmComponent } from '@shared/components/custom-popconfirm/custom-popconfirm.component';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { ActivatedRoute } from '@angular/router';
import { ContextService } from '@services/context.service';
import { ToolCallIOComponent } from '@shared/components/tool-call-IO/tool-call-IO.component';
import { AssetCallSuccessIconComponent } from '@shared/components/assets/asset-call-success-icon/asset-call-success-icon.component';
import {
  FLOW_DEFAULT_ICON_BASE64_STR,
  KNOWLEDGE_ICON_BASE64_STR,
  MCP_DEFAULT_ICON_BASE64_STR,
  PLUGIN_DEFAULT_ICON_BASE64_STR,
} from '@shared/config/default-icons-base64';
import { AssetThinkLoadingIconComponent } from '@shared/components/assets/asset-think-loading-icon/asset-think-loading-icon.component';
import { AssetThinkCompletedIconComponent } from '@shared/components/assets/asset-think-completed-icon/asset-think-completed-icon.component';
import { MessageComponent } from '@shared/services/cfdata.service';
import {
  FeedbackType,
  getFileExtension,
  messageSourceFileMap,
} from './chat-item.enum';
import { ClickOutsideDirective } from '@shared/directives/click-outside.directive';
import { UploadFileIconComponent } from '@shared/components/upload-file-icon/upload-file-icon.component';
import { Subject, takeUntil } from 'rxjs';
import { TtsPlayerService, TtsState } from '@services/tts-player.service';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzCollapseModule } from 'ng-zorro-antd/collapse';
import { AiAnswerListService } from "@routes/agent-center/app-agent/components/chat-item/ai-answer.component.service";
import { CommonUtils } from 'src/utils/common.util';
import { isDevelpor } from "src/utils/utils";
import { SessioMgnService } from '@services/agent-observatory/session-service';
import {AppFlowRepoService} from "@services/agent-center/app-flow-repo.service";
import {PreviewDebugService} from "@routes/agent-center/app-agent/components/preview-debug/preview-debug.service";

@Component({
  selector: 'chat-item',
  templateUrl: './chat-item.component.html',
  styleUrls: ['./chat-item.component.scss'],
  imports: [
    CommonModule,
    MODULES,
    ToolCallIOComponent,
    CustomPopconfirmComponent,
    AppMarkdownAnswerComponent,
    AssetFstLatencyIconComponent,
    AssetColorUserIconComponent,
    AssetQuoteIconComponent,
    AssetCallSuccessIconComponent,
    AssetThinkLoadingIconComponent,
    ClickOutsideDirective,
    AssetThinkCompletedIconComponent,
    UploadFileIconComponent,
    NzIconModule,
    NzButtonModule,
    NzToolTipModule,
    NzCollapseModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.TRACE],
    },
    TtsPlayerService,
  ],
})
export class ChatItemComponent implements OnDestroy {
  @Input() agentIcon: string;

  @Input() data: ConversationContent[];

  @Input() conversationId: string;

  @Input() messageId: number;

  @Input() isError: boolean;

  @Input() agentName: string;

  @Input() isQuestionsLoading: boolean;

  public headClass: string = 'headClass';
  public bodyClass: string = 'bodyClass';

  public dialogHistoryDeal: Array<
    (ConversationContent | FuncCallItem) & {
      timeConsumptionStr: TimeConsumptionStr;
    }
  >;

  public cdnUrl = cdnAssetUrl;

  public isF1 = this.ctxServ.isF1ReqList();

  public supportFeedback = this.configServ.getConfigs()?.feedback_enable ?? false;

  public supportAnnotation = this.configServ.getConfigs()?.agentops_evaluation_display && this.configServ.getConfigs().agentops_menu_display;

  public agentId = '';

  public isDevelporFlag = isDevelpor();

  public defaultIconMap: Record<string, string> = {
    mcp: MCP_DEFAULT_ICON_BASE64_STR,
    plugin: PLUGIN_DEFAULT_ICON_BASE64_STR,
    workflow: FLOW_DEFAULT_ICON_BASE64_STR,
    kenowledge: KNOWLEDGE_ICON_BASE64_STR,
  };

  public voiceEnable = false;

  public soundState = TtsState.Idle;

  public destroy$ = new Subject<void>();

  constructor(
    public route: ActivatedRoute,
    public agentCommonLogic: agentCommonLogic,
    public agentRepoServe: AppAgentRepoService,
    public ctxServ: ContextService,
    public cdr: ChangeDetectorRef,
    public i18n: I18NextEagerPipe,
    public ttsPlayerServe: TtsPlayerService,
    public agentDataServe: AgentDataService,
    public configServ: AgentConfigService,
    public nzModal: NzModalService,
    public aiAnswerListService : AiAnswerListService,
    public kbAnswerResolverService : KbAnswerResolverService,
    public sessioMgnService : SessioMgnService,
    public knowledgeRepoService: KnowledgeRepoService,
    public appFlowServe: AppFlowRepoService,
    public previewDebugServ: PreviewDebugService
  ) {
    this.route.queryParams.subscribe((params) => {
      this.agentId = params.agentId;
    });

    this.voiceEnable = this.configServ.voiceEnable();

    this.ttsPlayerServe.state$
      .pipe(takeUntil(this.destroy$))
      .subscribe((state) => (this.soundState = state));
  }
  sourceFiles = [];

  showFileList = false;

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.data) {
      const data = changes.data.currentValue;
      // 过滤掉 role 等于 "followUpQuestions" 的对象
      const filteredData = data?.filter(
        (item) => item.role !== 'followUpQuestions',
      );
      this.dialogHistoryDeal = this.dealCvList(filteredData);
      this.aiAnswerListService.setFileSource(this.dialogHistoryDeal);
      this.sourceFiles = this.aiAnswerListService.filterSourceFile(this.dialogHistoryDeal);
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.showFileList = false;
    this.kbAnswerResolverService.clear();
  }

  public getDefaultIcon(content) {
    let type = content.toolType;
    if (type === 'plugin' && content.request.name === 'retrieval') {
      type = 'kenowledge';
    }
    return this.defaultIconMap[type];
  }

  public isConversationContent(
    item: ConversationContent | FuncCallItem,
  ): item is ConversationContent {
    return typeof item === 'object' && item !== null;
  }

  public isFuncCallItem(
    item: ConversationContent | FuncCallItem,
  ): item is FuncCallItem {
    return typeof item === 'object' && item !== null;
  }

  public dealCvList(list: any[]) {
    list = [...new Set(list)];
    let newList: Array<
      (ConversationContent | FuncCallItem) & {
        timeConsumptionStr: TimeConsumptionStr;
      }
    > = [];
    for (let i = 0; i < list.length; i++) {
      const item = list[i];
      const { event, plugin, type, latency } = item || {};
      if (event === 'plugin_start') {
        const data = {} as FuncCallItem & {
          timeConsumptionStr: TimeConsumptionStr;
        };
        data.pluginName = plugin?.name;
        data.toolType = type;
        data.collapsed = true;
        data.allCollapsed = false;
        if (plugin) {
          const { memory_variables, icon, ...rest } = item.plugin;
          data.request = rest;
          data.icon = icon
        }
        const time_consumption: TimeConsumption & { totalEx?: number } =
          latency;
        const next = list[i + 1];
        if (next && next.role === 'function') {
          data.isRunning = false;
          data.response = next?.content;
          data.status = next?.status;
          time_consumption.plugin_latency = next.latency?.plugin || 0;
          time_consumption.overall_latency = next.latency?.overall || 0;
        } else if (item.role === 'memorySet') {
          data.title = this.i18n.transform('setting_memory_completed');
          data.memory_variables = Object.keys(plugin?.memory_variables).map(
            (key) => ({ key, value: plugin?.memory_variables[key] }),
          );
        } else {
          if (data.toolType !== 'plugin') {
            data.title = `${this.i18n.transform('calling_workflow')} ${
              data.pluginName
            }`;
          } else {
            if (data.pluginName === 'retrieval') {
              data.title = this.i18n.transform('querying_knowledge');
            } else {
              data.title = `${this.i18n.transform('calling_plugin')} ${
                data.pluginName
              }`;
            }
          }
          data.isRunning = true;
        }
        if (item.role === 'memorySet') {
          data.role = 'memorySet';
        } else {
          data.role = 'functionRole';
        }
        data.time_consumption = time_consumption;
        data.timeConsumptionStr = this.getTimeDelayStr(time_consumption);
        newList[i] = data;
      } else if (item?.role === 'user') {
        const data = item as ConversationContent & {
          timeConsumptionStr: TimeConsumptionStr;
        };
        data.content = item.content;
        newList[i] = data;
      } else {
        if (
          item.event !== 'function_call_end' &&
          item.event !== 'api_exec_data'
        ) {
          const data = item as ConversationContent & {
            timeConsumptionStr: TimeConsumptionStr;
          } ;
          data.timeConsumptionStr = this.getTimeDelayStr(data.time_consumption);
          if(item?.role?.startsWith('think')){
            data.collapsed = false;
          }
          newList[i] = data;
        }
      }
    }
    newList = newList.filter((item) => item?.role !== 'function');
    return newList;
  }

  /** 处理Agent流式接口调用插件/工作流能力的3种颜色变化 */
  public getColor(content: any): string {
    return this.agentCommonLogic.getColor(content);
  }

  public changeCollapsedState(content: any, key: 'collapsed' | 'allCollapsed') {
    content[key] = !content[key];
  }

  public getTrimmedQuestion(question: string) {
    return question.trim();
  }

  public getTimeDelayStr(
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
      timeDelayRes.overall_str = `${this.i18n.transform('run_time')} ${
        time_consumption.overall
      }s `;
    } else {
      timeDelayRes.overall_str = '';
    }

    if (
      time_consumption.plugin_latency !== undefined &&
      time_consumption.plugin_latency !== null
    ) {
      timeDelayRes.plugin_latency_str = `${time_consumption.plugin_latency}s `;
    } else {
      timeDelayRes.plugin_latency_str = '';
    }

    return timeDelayRes;
  }

  public getText(content: any): string {
    return content?.content?.trim() ?? '';
  }

  public onSoundOut(content: any) {
    if (this.soundState === TtsState.Playing) {
      this.ttsPlayerServe.stop();
      return;
    }
    const { language, timbre, domain } = this.agentDataServe.getVoiceConfig();
    this.ttsPlayerServe.play(this.getText(content), {
      property: `${language}_${timbre}_${domain}`,
    });
  }

  /** 点赞按钮 */
  public likeAnswer(content: any) {
    // 检查当前想点赞的回答是否已经点赞，如果是，则取消点赞
    if (content?.isLikeClicked) {
      this.cancelFeedback(content);
    } else {
      const params = {
        rating: FeedbackType.UPVOTE,
        app_name: this.agentName,
      };
      this.agentRepoServe.conversationFeedback(this.agentId, this.conversationId, this.messageId, 'agent', params,
        ).then(() => {
          // 将点赞按钮设置为实心状态
          content.isLikeClicked = true;
          content.isDislikeClicked = false;
          this.cdr.detectChanges();
        });
    }
  }

  /** 点踩抽屉的取消按钮 */
  public cancelDislike() {
    document.dispatchEvent(new Event('scroll'));
  }

  /** 点踩按钮 - 踩 or 取消踩 */
  public submitDislike(content: any) {
    const assistantItem = this.dialogHistoryDeal.find(
      (item) => item.role === 'assistant',
    ) as any;
    if (assistantItem) {
      // 检查当前想点踩的回答是否已经点赞，如果是，则取消点赞
      if (assistantItem.isDislikeClicked) {
        this.cancelFeedback(assistantItem);
      } else {
        const params = {
          rating: FeedbackType.DOWNVOTE,
          app_name: this.agentName,
        };
        this.agentRepoServe
          .conversationFeedback(
            this.agentId,
            this.conversationId,
            this.messageId,
            'agent',
            params,
          )
          .then((res) => {
            assistantItem.isLikeClicked = false;
            assistantItem.isDislikeClicked = true;
          });
      }
    }
    this.cdr.detectChanges();
  }

  /** 当调用点踩接口完成时，关闭Tip弹窗 */
  public closeDislikeTip() {
    document.dispatchEvent(new Event('scroll'));
  }

  /** 点踩后提交反馈问题 */
  public submitDisLikeFeedback(params) {
    const { selected, suggestions } = params;
    if (!selected?.length && !suggestions) {
      return;
    }
    const feedback = {
      rating: FeedbackType.DOWNVOTE,
      reason: {
        tags: selected?.map((item) => item.label) || [],
        content: suggestions,
      },
      app_name: this.agentName,
    };
    this.agentRepoServe
      .conversationFeedback(
        this.agentId,
        this.conversationId,
        this.messageId,
        'agent',
        feedback,
      )
      .then((res) => {
        MessageComponent.showSuccess(
          this.i18n.transform('feedback_successful'),
        );
        this.closeDislikeTip();
      });
  }

  /** 取消反馈 */
  public cancelFeedback(content:any) {
    this.agentRepoServe
      .cancelFeedback(this.agentId, this.conversationId, this.messageId)
      .then(() => {
        content.isDislikeClicked = false;
        content.isLikeClicked = false;
        this.cdr.detectChanges();
      });
  }

  show(sourceFileDetail): void {
    this.nzModal.create({
      nzContent: SourceFileDetailComponent,
      nzData: {
        sourceFileDetail,
      }
    });
  }

  downloadSourceFileFn(file) {
    const { file_id, knowledge_base_id, type } = file;
    if (file_id && knowledge_base_id) {
      if (type === 'faq') {
        this.knowledgeRepoService.downloadFaqFileFetch(knowledge_base_id, file_id).then((res) => {
          CommonUtils.downloadFile(new Blob([res.data]), res.headers.get('Content-Disposition'));
        });
      } else {
        this.knowledgeRepoService.downloadFileFetch(knowledge_base_id, file_id).then((res) => {
          CommonUtils.downloadFile(new Blob([res.data]), res.headers.get('Content-Disposition'));
        });
      }
    }
  }

  public showAllSourceFile() {
    this.nzModal.create({
      nzContent: ChatSourceComponent,
      nzClassName: 'chat-source',
      nzData: {
        sourceFiles: this.sourceFiles,
      }
    });
  }

  protected readonly messageSourceFileMap = messageSourceFileMap;
  protected readonly getFileExtension = getFileExtension;

  tipContext: any = {};

  public like(e, row) {
    e.stopPropagation();
    let param = {
      span_Id: row.executionId,
      vote: row.vote === 1 ? 0 : 1,
      data_type: 'trace',
    };
    this.sessioMgnService.vote(param).then((res) => {
      row.vote = row.vote === 1 ? 0 : 1;
    });
  }

  public disLike(e, row) {
    e.stopPropagation();
    let param = {
      span_Id: row.executionId,
      vote: row.vote === -1 ? 0 : -1,
      data_type: 'trace',
    };
    this.sessioMgnService.vote(param).then((res) => {
      row.vote = row.vote === -1 ? 0 : -1;
    });
  }

  public copy(text) {
    // 使用 textarea 保留换行符，确保 markdown 结构完整
    const el = document.createElement('textarea');
    el.value = text;
    el.style.position = 'fixed';
    el.style.opacity = '0';
    document.body.appendChild(el);
    el.select();
    document.execCommand('copy');
    document.body.removeChild(el);
    MessageComponent.showSuccess(this.i18n.transform('copy_success'), 3000);
  }
}
