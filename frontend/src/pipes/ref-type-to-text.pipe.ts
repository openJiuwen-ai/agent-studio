import { Pipe, PipeTransform } from '@angular/core';
import { I18NextEagerPipe } from 'angular-i18next';

@Pipe({
  name: 'refTypeToText',
  standalone: true,
})
export class RefTypeToTextPipe implements PipeTransform {
  constructor(private i18n: I18NextEagerPipe) {}

  transform(value: string): string {
    switch (value) {
      case 'workflow':
        return this.i18n.transform('workflow');
      case 'agent':
        return this.i18n.transform('app');
      case 'controller':
        return this.i18n.transform('multiple_agent');
      default:
        return '--';
    }
  }
}
