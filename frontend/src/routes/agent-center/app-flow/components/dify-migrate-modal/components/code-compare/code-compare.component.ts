import {Component, Input} from '@angular/core';
import {I18NEXT_NAMESPACE, I18NextEagerPipe} from "angular-i18next";
import { MonacoEditorModule } from '@materia-ui/ngx-monaco-editor';
import { Base64 } from 'js-base64';
import {NzIconModule} from "ng-zorro-antd/icon";
import {NzButtonModule} from "ng-zorro-antd/button";
import {NzDropDownModule} from "ng-zorro-antd/dropdown";
import {NzToolTipModule} from "ng-zorro-antd/tooltip";

import {MigrateCompareRowComponent} from "@routes/agent-center/app-flow/components/dify-migrate-modal/components/migrate-compare-row/migrate-compare-row.component";
import {CommonModule, NgIf} from "@angular/common";
import {MODULES} from "@shared/modules";
import {I18nNamespace} from "@i18n";
import type {ICodeNode} from "@routes/agent-center/app-flow/node.type";
import {AppFlowRepoService} from "@services/agent-center/app-flow-repo.service";
import {cdnAssetUrl} from "../../../../../../../single-spa/assets-url";
import {AgentConfigService} from "@routes/agent-center/agent-config.service";
import {DEFAULT_CODE} from "@routes/agent-center/constants/workflow-http-response-code.const";
import {DifyMigrateService} from "@routes/agent-center/app-flow/components/dify-migrate-modal/dify-migrate.service";
import {convertToSandboxFormat} from "@routes/agent-center/app-flow/utils/dify-code-format.util";

@Component({
  selector: 'code-compare',
  templateUrl: './code-compare.component.html',
  styleUrls: ['../common-compare.less', './code-compare.component.less'],
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    NzIconModule,
    NzButtonModule,
    NzDropDownModule,
    NzToolTipModule,
    MigrateCompareRowComponent,
    MonacoEditorModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class CodeCompareComponent {
  @Input() node: ICodeNode;

  public commonCodeOptions = {
    theme: 'vs',
    minimap: {
      enabled: false,
    },
    scrollbar: {
      horizontalScrollbarSize: 0,
      verticalScrollbarSize: 0,
      verticalSliderSize: 8,
      horizontalSliderSize: 8,
      useShadows: false,
    }
  }

  public oldCode = '';
  public oldCodeOptions = {
    ...this.commonCodeOptions,
    language: 'json',
    readOnly: true,
  };

  public fgId: string;
  public fgDetails;
  public fgObj;

  public fgCodeOptions = {
    ...this.commonCodeOptions,
    language: 'python',
    readOnly: true,
  };
  public fgCode;

  public sandBoxCode = DEFAULT_CODE;
  public sandBoxOptions = {
    ...this.commonCodeOptions,
    language: 'python',
    readOnly: false,
  };

  public menuItems: Array<any> = [
    {
      id: 'edit',
      label: this.i18n.transform('edit'),
    }
  ];

  public changeUrl = cdnAssetUrl;
  public showFunctionGraph = false;

  public get fgEditHeight() {
    return this.fgCodeOptions.readOnly ? '346px' : '382px';
  }

  constructor(
    private i18n: I18NextEagerPipe,
    private appFlowRepoServ: AppFlowRepoService,
    private configServ: AgentConfigService,
    private difyMigrateService: DifyMigrateService,
  ) { }

  ngOnInit(): void {
    this.oldCode = this.node.configs.code;
    this.showFunctionGraph = this.isShowFunctionGraph();

    if(!this.showFunctionGraph) {
      // 平台未配置 FunctionGraph 时强制转沙箱执行：把 Dify 原代码转换为沙箱兼容
      // 格式（main(变量...) → main(args) + 按变量名解包），保留业务逻辑。
      // 转换判定/分层回退规则见 convertToSandboxFormat 注释；原码为空才用默认模板
      // （此前无条件用 DEFAULT_CODE 覆盖导致 Dify 代码丢失，见 bugfix 文档）。
      const variableNames = (this.node.inputs ?? [])
        .map(field => field.name)
        .filter((name): name is string => !!name);
      this.sandBoxCode = this.oldCode
        ? convertToSandboxFormat(this.oldCode, variableNames)
        : DEFAULT_CODE;
      this.node.configs.code = this.sandBoxCode;
      this.node.configs.exec_env = 'sandbox';
    }
  }

  public onSandboxChange() {
    this.node.configs.code = this.sandBoxCode;
  }

  public onFgCodeBoxChange() {
    if(this.fgCodeOptions.readOnly) {
      return;
    }

    Base64.extendString();
    this.node.configs.code = this.fgCode;
    this.difyMigrateService.fgUpdateMap.set(
      this.node.id,
      {
        id: this.fgId,
        dependencies: this.fgDetails.function_graph_info.dependencies,
        description: this.fgDetails.description,
        function_input: this.fgDetails.function_input,
        function_name: this.fgDetails.function_name,
        function_output: this.fgDetails.function_output,
        runtime: this.fgDetails.runtime,
        status: 1,
        type: 'function',
        handler: 'mssi.handler',
        memory_size: 128,
        time_out: 30,
        concurrent_num: 1,
        function_code: {
          ...this.fgDetails.function_graph_info.function_code,
          code_file: this.fgCodeOptions.language === 'python' ? 'index.py' : 'index.js',
          code_type: 'inline',
          func_code: (this.fgCode as any).toBase64()
        },
      }
    );
  }

  public showAddFgModal() {
  }

  public showSelectFgModal(e?) {
  }

  public updateFg(paramData: any) {
  }

  public editCodeFun() {
    this.handleFg('edit');
  }

  handleFg(fromBtn) {
    if(!this.fgCodeOptions.readOnly) {
      this.editCode();
      return;
    }

    const params = {
      offset: 0,
      limit: 100,
      resource_type: 'functiongraph',
    };
    this.appFlowRepoServ
      .getCitationList(params, this.fgId)
      .then((resData: any) => {
        const citationTotalNumber = resData.count;

        if (!citationTotalNumber) {
          if (fromBtn === 'edit') {
            this.editCode();
          }
        } else {
          this.openReferenceModal(fromBtn);
        }
      })
      .finally(() => {});
  }

  public unbindFgModal(e) {
    this.fgId = '';
    this.setCurFgDetail();
    e.stopPropagation();
  }

  public listSelectAction(e: any) {
    if (e.id === 'edit') {
      this.showAddFgModal();
    }
  }

  private openReferenceModal(fromBtn) {
  }

  private editCode() {
    this.fgCodeOptions = {
      ...this.fgCodeOptions,
      readOnly: false,
    }
  }

  private setCurFgDetail() {
  }

  private isShowFunctionGraph() {
    const codeOptions = this.configServ.getConfigs().code_env_options;
    return codeOptions.includes('fg');
  }
}
