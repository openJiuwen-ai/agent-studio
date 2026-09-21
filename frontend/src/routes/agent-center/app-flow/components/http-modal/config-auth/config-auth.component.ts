import { Component, EventEmitter, Input, Output, ViewChild } from '@angular/core';
import { NgForm } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import {
  NonEmptyValidatorDirective,
  ValueValidityValidatorDirective,
} from '@shared/directives/variable-name-validator.directive';
import { NoCnDirective } from '@shared/directives/common-validator.directive';
import { MODULES } from '@shared/modules';
import { IServAuthKV, type IHttpConfig } from '../../../node.type';
import { AccBlockComponent } from '../../acc-block/acc-block.component';

@Component({
  selector: 'meta-config-auth',
  standalone: true,
  imports: [MODULES, NonEmptyValidatorDirective, ValueValidityValidatorDirective, NoCnDirective, AccBlockComponent],
  templateUrl: './config-auth.component.html',
  styleUrl: './config-auth.component.less',
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: I18nNamespace.AGENT_CENTER,
    },
  ],
})
export class ConfigAuthComponent {
  @Input() configs!: IHttpConfig;

  @ViewChild('authkeyForm') authkeyForm!: NgForm;

  @Output() valueChange = new EventEmitter<void>();
  @Output() inputChange = new EventEmitter<void>();
  @Output() updateTimeChange = new EventEmitter<void>();

  authMethods: { label: string; value: string }[] = [];

  auth = 'none';

  authDomains = [
    { label: 'Header', value: 'HEADERS' },
    { label: 'Query', value: 'QUERY' },
  ];

  apiKeyAuthArgs: IServAuthKV[] = [];
  apiAuthArgsLimit = 4;

  constructor(private i18n: I18NextEagerPipe) {
    this.authMethods = [
      { label: this.i18n.transform('no_auth'), value: 'none' },
      { label: 'API Key', value: 'api' },
    ];
  }

  ngOnInit(): void {
    if (this.configs.auth_info?.domain) {
      this.auth = 'api';
      this.apiKeyAuthArgs = this.configs.auth_info.auth_keys || [];
    } else {
      this.auth = 'none';
    }
  }

  changeAuth(auth: string): void {
    if (auth === 'none') {
      this.configs.auth_info = {};
    } else {
      this.configs.auth_info = {
        scope: 'SERVICE',
        domain: 'HEADERS',
        auth_keys: [{ auth_key: '', target_name: '' }],
      };
      this.apiKeyAuthArgs = this.configs.auth_info.auth_keys!;
    }
    this.onValueChange();
  }

  deleteArgs(i: number): void {
    this.apiKeyAuthArgs.splice(i, 1);
    this.onValueChange();
  }

  addArgs(): void {
    this.apiKeyAuthArgs.push({ auth_key: '', target_name: '' });
    this.onValueChange();
  }

  getKeyNames(index: number): { existingValues: string[]; isHttp: boolean } {
    const names = this.apiKeyAuthArgs.map((p) => p.target_name);
    names.splice(index, 1);
    return { existingValues: names, isHttp: true };
  }

  onParamsChange(): void {
    this.configs.auth_info = {
      scope: 'SERVICE',
      // 保留当前已选鉴权域：此处整对象重建，若硬编码 HEADERS 会在用户
      // 编辑 Key/Value 时把 Query 域选择静默重置
      domain: this.configs.auth_info?.domain || 'HEADERS',
      auth_keys: this.apiKeyAuthArgs,
    };
    this.updateTimeChange.emit();
  }

  onValueChange(): void {
    this.valueChange.emit();
  }

  onInputSave(): void {
    this.inputChange.emit();
  }
}
