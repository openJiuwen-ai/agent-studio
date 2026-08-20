import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  OnInit,
  ViewChild,
  TemplateRef,
  OnDestroy,
} from "@angular/core";
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from "angular-i18next";
import { MODULES } from "@shared/modules";
import { I18nNamespace } from "@i18n";
import { FormBuilder, FormGroup, Validators } from "@angular/forms";
import { CommonValidation } from "@shared/validation/commonValidation";
import { KnowledgeRepoService } from "@services/agent-center/knowledge.service";
import { AgentConfigService } from "@routes/agent-center/agent-config.service";
import { IKnowledgeDefaultConfigConnection } from "@routes/agent-center/app-knowledge/knowledge.types";
import { NzSwitchModule } from 'ng-zorro-antd/switch';
import { NzRadioModule } from 'ng-zorro-antd/radio';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzDrawerModule, NzDrawerService, NzDrawerRef } from 'ng-zorro-antd/drawer';
import { NzMessageService } from 'ng-zorro-antd/message';

@Component({
  selector: "meta-default-config-modal",
  imports: [MODULES, NzSwitchModule, NzRadioModule, NzFormModule, NzDrawerModule],
  templateUrl: "./default-config-modal.component.html",
  styleUrls: ["./default-config-modal.component.scss"],
  standalone: true,
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.COMMON, I18nNamespace.KNOWLEDGE]
    }
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DefaultConfigModalComponent implements OnInit, OnDestroy {
  @ViewChild('defaultConfigModal', { static: true }) defaultConfigModal: TemplateRef<any>;
  drawerRef: NzDrawerRef;
  public form: FormGroup;
  ocrEnableText = this.i18n.transform('closed');
  modeList: Array<{ label: string; value: string }> = [
    {
      label: 'Basic',
      value: 'basic',
    },
    {
      label: 'None',
      value: 'none',
    },
  ];
  modeSelected = 'basic';
  connectionId = '';
  oldConnection = {
    auth_mode: 'basic',
    endpoint: '',
    ocr_enable: false,
    authorization: '******',
  }
  showAuth = true;
  isOpenJiuwen = false;
  openjiuwenEnabled = false;
  kbTypeList: Array<{ label: string; value: string }> = [
    { label: 'OpenJiuwen', value: 'OpenjiuwenInside' },
    { label: 'Other', value: 'LakeSearchInside' },
  ];
  kbTypeSelected = 'LakeSearchInside';
  constructor(
    private fb: FormBuilder,
    private i18n: I18NextEagerPipe,
    private knowledgeService: KnowledgeRepoService,
    private drawerService: NzDrawerService,
    private nzMessage: NzMessageService,
    private cdr: ChangeDetectorRef,
    private configServ: AgentConfigService
  ) {
    this.form = this.fb.group({
      auth_mode: ['basic'],
      endpoint: [
        '',
        [
          Validators.required,
          CommonValidation.customVerify(
            '^(?:(?:https?):\\/\\/)?(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z]{2,}|localhost|\\d{1,3}(?:\\.\\d{1,3}){3})(?::\\d{1,5})?$',
            this.i18n.transform('enter_correct_service_address'),
          ),
        ],
      ],
      authorization: ['', [Validators.required, Validators.maxLength(100)]],
      ocr_enable: [false],
    });
  }

  ngOnInit(): void {}

  public dismiss(): void {
    this.drawerRef.close();
  }

  public closeAndSaveConfig(): void {
    if (this.isOpenJiuwen) {
      this.saveOpenJiuwenConfig();
      return;
    }
    let isValid = true;
    isValid = this.validateSpecificFields(['auth_mode', 'ocr_enable', 'endpoint']);
    if (!isValid) {
      return;
    }
    if (this.showAuth) {
      isValid = this.validateSpecificFields(['authorization']);
      if (!isValid) {
        return;
      }
    }
    const param: IKnowledgeDefaultConfigConnection = {
      connector_id: 'LakeSearchInside',
      params: [
        { code: 'auth_mode', value: this.form.get('auth_mode').value },
        { code: 'ocr_enable', value: this.form.get('ocr_enable').value.toString() },
        { code: "endpoint", value: this.form.get('endpoint').value },
      ],
    };
    if (this.showAuth) {
      param.params.push({ code: "authorization", value: this.form.get("authorization").value });
    } else {
      param.params.push({ code: "authorization", value: '' });
    }
    if (this.connectionId) {
      param.changed = false;
      if (this.oldConnection.auth_mode !== this.form.get('auth_mode').value ||
        this.oldConnection.endpoint !== this.form.get('endpoint').value ||
        (this.showAuth && this.oldConnection?.authorization !== this.form.get('authorization')?.value)) {
        isValid = this.validateSpecificFields(['authorization']);
        param.changed = true;
        if (!isValid) {
          return;
        }
      }
      this.setOtherParams(param);
      this.knowledgeService.updateKnowLedgeDefaultConfig(param, this.connectionId).then(res => {
        this.nzMessage.success(this.i18n.transform('modify_default_config_success'));
        this.drawerRef.close();
      });
    } else {
      this.setOtherParams(param);
      this.knowledgeService.createKnowLedgeDefaultConfig(param).then(res => {
        this.nzMessage.success(this.i18n.transform('create_default_config_success'));
        this.drawerRef.close();
      });
    }
  }

  private saveOpenJiuwenConfig(): void {
    const param: IKnowledgeDefaultConfigConnection = {
      connector_id: 'OpenjiuwenInside',
      params: [
        { code: 'auth_mode', value: 'openjiuwen' },
      ],
    };
    if (this.connectionId) {
      param.changed = true;
      this.knowledgeService.updateKnowLedgeDefaultConfig(param, this.connectionId).then(res => {
        this.nzMessage.success(this.i18n.transform('modify_default_config_success'));
        this.drawerRef.close();
      });
    } else {
      this.knowledgeService.createKnowLedgeDefaultConfig(param).then(res => {
        this.nzMessage.success(this.i18n.transform('create_default_config_success'));
        this.drawerRef.close();
      });
    }
  }

  private setOtherParams(param: IKnowledgeDefaultConfigConnection) {
    param.params.push({ code: "cluster_ips", value: "" });
    param.params.push({ code: "port", value: "" });
    param.params.push({ code: "protocol", value: "" });
    param.params.push({ code: "user_keytab_file", value: "" });
    param.params.push({ code: "krb5_file", value: "" });
  }

  ngOnDestroy(): void {
  }

  public open(connectionId: string) {
    this.openjiuwenEnabled = this.configServ.openjiuwenKbEnable();
    if (connectionId) {
      this.connectionId = connectionId;
      this.showAuth = false;
      this.knowledgeService.getKnowledgeDefaultConfigDetail(connectionId).then(res => {
        if (res?.knowledge_base_connection_detail?.params) {
          const detail = res.knowledge_base_connection_detail;
          const params = detail.params;
          const connectorId = detail.connector_id;
          if (this.openjiuwenEnabled && connectorId === 'OpenjiuwenInside') {
            this.isOpenJiuwen = true;
            this.kbTypeSelected = 'OpenjiuwenInside';
            this.openDrawer();
            this.cdr.markForCheck();
            return;
          }
          this.isOpenJiuwen = false;
          this.kbTypeSelected = 'LakeSearchInside';
          const authModeInfo = params.find(item => item.code === 'auth_mode');
          const endpointInfo = params.find(item => item.code === 'endpoint');
          const ocrEnableInfo = params.find(item => item.code === 'ocr_enable');
          this.form.patchValue({
            auth_mode: authModeInfo?.value ?? 'basic',
            endpoint: endpointInfo?.value ?? '',
            ocr_enable: ocrEnableInfo?.value === 'true',
            authorization: '******',
          });
          this.modeSelected = authModeInfo?.value ?? 'basic';
          this.oldConnection = {
            auth_mode: authModeInfo?.value,
            endpoint: endpointInfo?.value,
            ocr_enable: ocrEnableInfo?.value === 'true',
            authorization: '******',
          }
          this.showAuth = this.oldConnection.auth_mode === 'basic';
          this.openDrawer();
          this.cdr.markForCheck();
        }
      })
    } else {
      this.connectionId = '';
      if (this.openjiuwenEnabled) {
        this.isOpenJiuwen = true;
        this.kbTypeSelected = 'OpenjiuwenInside';
        this.showAuth = false;
      } else {
        this.isOpenJiuwen = false;
        this.kbTypeSelected = 'LakeSearchInside';
        this.showAuth = true;
      }
      this.openDrawer();
      this.cdr.markForCheck();
    }
  }

  private openDrawer(): void {
    this.drawerRef = this.drawerService.create({
      nzContent: this.defaultConfigModal,
      nzWidth: '700px',
      nzPlacement: 'right',
      nzClosable: true,
      nzMaskClosable: true,
      nzTitle: null,
      nzFooter: null,
    });
  }

  changeOcrEnable(event) {
    this.ocrEnableText = event ? this.i18n.transform('status_open') : this.i18n.transform('closed');
  }

  private validateSpecificFields(fieldNames?: string[]){
    if (!fieldNames) {
      Object.values(this.form.controls).forEach(control => {
        if (control.invalid) {
          control.markAsDirty();
          control.updateValueAndValidity({ onlySelf: true });
        }
      });
      return this.form.valid;
    }

    let isValid = true;
    fieldNames.forEach((fieldName) => {
      const control = this.form.get(fieldName);
      if (!control) {
        return;
      }
      // 触发 ng-zorro 表单标红
      control.markAsDirty();
      control.updateValueAndValidity({ onlySelf: true });
      if (control.invalid) {
        isValid = false;
      }
    });
    return isValid;
  }

  changeMode(event) {
    this.modeSelected = event;
    this.showAuth = event === 'basic';
  }

  changeKbType(event) {
    this.kbTypeSelected = event;
    this.isOpenJiuwen = event === 'OpenjiuwenInside';
    if (this.isOpenJiuwen) {
      this.showAuth = false;
    } else {
      this.form.patchValue({
        auth_mode: 'basic',
        endpoint: '',
        ocr_enable: false,
        authorization: '',
      });
      this.modeSelected = 'basic';
      this.showAuth = true;
    }
    this.cdr.markForCheck();
  }

  testConnection() {
    if (this.isOpenJiuwen) {
      this.nzMessage.success(this.i18n.transform('connection_success'));
      return;
    }
    if (this.connectionId) {
      if (this.oldConnection.auth_mode !== this.form.get('auth_mode').value || this.oldConnection.endpoint !== this.form.get('endpoint').value) {
        let isValid = this.validateSpecificFields();
        if (!isValid) {
          return;
        }
        this.testConnectionByParams();
      } else {
        this.knowledgeService.testKnowLedgeDefaultConfigById(this.connectionId).then(res => {
          this.nzMessage.success(this.i18n.transform('connection_success'));
        })
      }
    } else {
      this.testConnectionByParams();
    }
  }

  private testConnectionByParams() {
    const param: IKnowledgeDefaultConfigConnection = {
      connector_id: "LakeSearchInside",
      params: [
        { code: "auth_mode", value: this.form.get("auth_mode").value },
        { code: "ocr_enable", value: this.form.get("ocr_enable").value.toString() },
        { code: "endpoint", value: this.form.get("endpoint").value },
        { code: "authorization", value: this.form.get("authorization").value }
      ]
    };
    this.setOtherParams(param);
    this.knowledgeService.testKnowLedgeDefaultConfig(param).then(res => {
      this.nzMessage.success(this.i18n.transform('connection_success'));
    });
  }
}
