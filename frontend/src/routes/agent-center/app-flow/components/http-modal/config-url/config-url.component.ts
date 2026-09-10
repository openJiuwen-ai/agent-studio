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
    this.path = this.configs.path ? this.configs.path.slice(1) : '';
  }

  onPathChange(): void {
    this.configs.path = `/${this.path}`;
    this.onSaveChange();
  }

  onSaveChange(): void {
    this.valueChange.emit();
  }

  changeUpdateTime(): void {
    this.updateTimeChange.emit();
  }
}
