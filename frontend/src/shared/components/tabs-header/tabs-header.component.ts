import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MODULES } from '@shared/modules';
import { NzTabsModule } from 'ng-zorro-antd/tabs';

export interface ITabHeader {
  id: string;
  title: string;
  active: boolean;
  disabled?: boolean;
  tips?: string;
  show?: boolean;
}

@Component({
  selector: 'tabs-header',
  template: `
    <nz-tabs id="cmp-tabs-header" [nzSelectedIndex]="selectedIndex" (nzSelectedIndexChange)="onSelectedIndexChange($event)">
      @for (tab of tabs; track tab.id) {
        @if (tab.show !== false) {
          <nz-tab [nzTitle]="tab.title" [nzDisabled]="tab?.disabled"> </nz-tab>
        }
      }
    </nz-tabs>
  `,
  styles: [
    `
      ::ng-deep {
        #cmp-tabs-header {
          .ant-tabs-nav {
            border-bottom-color: transparent !important;
          }

          .ant-tabs-content {
            height: calc(100% - 34px) !important;
          }
        }
      }
    `,
  ],
  standalone: true,
  imports: [MODULES, NzTabsModule],
})
export class TabsHeaderComponent {
  @Input() tabs: ITabHeader[];

  @Output() activeChange = new EventEmitter<string>();

  get selectedIndex(): number {
    const index = this.tabs.findIndex(tab => tab.active);
    return index >= 0 ? index : 0;
  }

  onSelectedIndexChange(index: number) {
    const tab = this.tabs[index];
    if (tab && !tab.disabled) {
      this.activeChange.emit(tab.id);
    }
  }
}
