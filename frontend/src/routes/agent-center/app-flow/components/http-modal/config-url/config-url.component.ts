import { Component, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { NgForm } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { NonEmptyValidatorDirective } from '@shared/directives/variable-name-validator.directive';
import { UrlValidatorDirective } from '@shared/directives/common-validator.directive';
import { MODULES } from '@shared/modules';
import type { IHttpConfig } from '../../../node.type';
import { AccBlockComponent } from '../../acc-block/acc-block.component';

@Component({
  selector: 'meta-config-url',
  standalone: true,
  imports: [MODULES, NonEmptyValidatorDirective, UrlValidatorDirective, AccBlockComponent],
  templateUrl: './config-url.component.html',
  styleUrl: './config-url.component.less',
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: I18nNamespace.AGENT_CENTER,
    },
  ],
})
export class ConfigUrlComponent implements OnInit {
  @Input() configs!: IHttpConfig;

  @ViewChild('apiForm') apiForm!: NgForm;

  @Output() valueChange = new EventEmitter<void>();
  @Output() updateTimeChange = new EventEmitter<void>();

  methodOptions = [
    { label: 'GET', value: 'GET' },
    { label: 'POST', value: 'POST' },
  ];

  prefix = '/';
  path = '';

  ngOnInit(): void {
    // 加载即归一为与 onPathChange 一致的规范形态（单个前导 '/' 或空串）：
    // 历史数据/API 直写的 path 可能不带前导 '/'（UI 写入必经 onPathChange 归一），
    // 只展示不回写会让 IR 构建层的 endpoint+path 纯拼接产出 endpointabc；
    // 无条件 slice(1) 又会丢首字符。归一化幂等，对已规范值无副作用
    const p = (this.configs.path || '').replace(/^\/+/, '');
    this.configs.path = p ? `/${p}` : '';
    this.path = p;
  }

  onPathChange(): void {
    // 归一化用户输入：剥掉前导斜杠再拼接，避免 '//x' 双斜杠进入最终 URL
    // （IR 构建层 endpoint+path 直接字符串拼接）；空输入存 '' 而非 '/'
    const p = (this.path ?? '').replace(/^\/+/, '');
    this.configs.path = p ? `/${p}` : '';
    this.onSaveChange();
  }

  onSaveChange(): void {
    this.valueChange.emit();
  }

  changeUpdateTime(): void {
    this.updateTimeChange.emit();
  }
}
