import {
  ChangeDetectorRef,
  Component,
  Input,
  OnDestroy,
  OnInit,
} from '@angular/core';
import { I18nNamespace } from '@i18n';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { AssetFormatIconComponent } from '@shared/components/assets/asset-format-icon/asset-format-icon.component';
import { ArrTypeValidatorDirective } from '@shared/directives/array-type-validator.directive';
import { ClickOutsideDirective } from '@shared/directives/click-outside.directive';
import {
  IntegerStrValidatorDirective,
  NumberStrValidatorDirective,
  RefSelectedRequireDirective,
} from '@shared/directives/common-validator.directive';
import { ObjTypeValidatorDirective } from '@shared/directives/obj-type-validator.directive';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import type { IWorkflowField } from '../../../node.type';
import { UploadFileIconComponent } from '@shared/components/upload-file-icon/upload-file-icon.component';
import {
  UploadFileAccPipe,
  UploadFileDescPipe,
} from 'src/pipes/upload-file.pipe';
import { ParamTreeComponent } from '@routes/agent-center/app-flow/components/param-tree/param-tree.component';
import { NonEmptyValidatorDirective } from '@shared/directives/variable-name-validator.directive';
import { NodeUtils } from '@routes/agent-center/app-flow/components/utils';
import { MonacoEditorModule } from '@materia-ui/ngx-monaco-editor';
import { SetDefaultTipComponent } from '@routes/agent-center/app-flow/components/set-default-tip/set-default-tip.component';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import * as nodeType from '@routes/agent-center/app-flow/node.type';
import { InputTreeSelect } from '@routes/agent-center/app-flow/components/input-tree-select/input-tree-select';

interface IFormObj {
  value?: string;
  desc?: string;
  isClose: boolean;
  display?: string;
}

@Component({
  selector: 'meta-set-value-tip',
  templateUrl: './set-value-tip.component.html',
  styleUrls: ['./set-value-tip.component.less', '../../common-styles.less'],
  standalone: true,
  imports: [
    MODULES,
    IntegerStrValidatorDirective,
    NumberStrValidatorDirective,
    AssetFormatIconComponent,
    ArrTypeValidatorDirective,
    ObjTypeValidatorDirective,
    ClickOutsideDirective,
    UploadFileIconComponent,
    UploadFileAccPipe,
    UploadFileDescPipe,
    ParamTreeComponent,
    NonEmptyValidatorDirective,
    RefSelectedRequireDirective,
    MonacoEditorModule,
    InputTreeSelect,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})

export class SetValueTipComponent
  extends SetDefaultTipComponent
  implements OnInit, OnDestroy
{
  public sourceOptions = [
    { label: this.i18n.transform('ref'), value: 'ref' },
    { label: this.i18n.transform('literal'), value: 'literal' },
  ];

  @Input('nameRefOptions') nameRefOptions: nodeType.IParamRef[] = [];

  constructor(
    public override cdr: ChangeDetectorRef,
    public override i18n: I18NextEagerPipe,
    public override repoServ: AppAgentRepoService,
    configServ: AgentConfigService,
  ) {
    super(cdr, i18n, repoServ, configServ);
  }

  override ngOnInit(): void {
    this.isMulti = Array.isArray(this.param.type);
    const normalWith = this.isShowDesc ? '526px' : '520px';
    const useInnerWidthLogic = this.isNormalWidth ? normalWith : '386px';
    this.width = this.cmpWidth ? this.cmpWidth : useInnerWidthLogic;
    if (this.param.value.type === 'literal') {
      this.value = String(this.param.value.content) ?? '';
    } else {
      this.value = '';
    }
    this.desc = this.param.description ?? '';
    this.initParam();
    if (this.field.value.type === 'generated') {
      this.field.value.type = 'literal';
    }
    NodeUtils.reSelectRefsWithNewOps([this.field], this.nameRefOptions);
  }

  override ngOnDestroy(): void {
    this.close({
      isClose: true,
    });
  }

  override onClickOutside(e: Event) {
    if (
      (e?.target as HTMLElement)?.tagName?.toLowerCase() === 'nz-popover'
    ) {
      return;
    }

    if (this.isUploading) {
      return;
    }
    if (
      this.param.type.includes('file') ||
      this.param.type.includes('array<file>')
    ) {
      this.fileList2Value();
    }

    if (this.valueForm?.form?.invalid) {
      this.value = '';
    }
    const emitObj: IFormObj = {
      value: this.value,
      display: this.display,
      isClose: true,
    };

    if (this.isShowDesc) {
      emitObj.desc = this.desc;
    }
    if (this.field.value.type === 'literal') {
      this.close(emitObj);
    }else{
      this.close({
        isClose: true,
      });
    }
  }

  onParamTypeChange(row: any) {
    row.value.content = NodeUtils.getChangeContent(row.value.type);
  }
}
