import { Component, EventEmitter, Output, ViewChild, TemplateRef, ChangeDetectorRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { I18NextEagerPipe, I18NextModule, I18NEXT_NAMESPACE } from 'angular-i18next';
import { NzModalRef, NzModalService } from 'ng-zorro-antd/modal';
import { NzRadioModule } from 'ng-zorro-antd/radio';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { I18nNamespace } from '@i18n';

@Component({
  selector: 'select-memory-create-type',
  templateUrl: './select-memory-create-type.component.html',
  styleUrls: ['./select-memory-create-type.component.less'],
  standalone: true,
  imports: [FormsModule, I18NextModule, NzRadioModule, NzButtonModule],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.MEMORY_LIB, I18nNamespace.COMMON],
    },
  ],
})
export class SelectMemoryCreateTypeComponent {
  @ViewChild('selectCreateType') selectCreateType!: TemplateRef<any>;
  @ViewChild('selectCreateTitle') selectCreateTitle!: TemplateRef<any>;
  @ViewChild('selectCreateFooter') selectCreateFooter!: TemplateRef<any>;

  @Output() openBuiltinMemoryLib = new EventEmitter<void>();
  @Output() openExternalMemoryLib = new EventEmitter<void>();

  private modalRef?: NzModalRef;
  private onConfirm?: (key: 'builtin' | 'external') => void;

  public typeItems = [
    {
      title: this.i18n.transform('memory.selectType.builtin.title'),
      content: this.i18n.transform('memory.selectType.builtin.content'),
      key: 'builtin' as const,
    },
    {
      title: this.i18n.transform('memory.selectType.external.title'),
      content: this.i18n.transform('memory.selectType.external.content'),
      key: 'external' as const,
    },
  ];
  public selectedType = this.typeItems[0];

  constructor(
    private nzModalService: NzModalService,
    private i18n: I18NextEagerPipe,
    private cdr: ChangeDetectorRef,
  ) {}

  onOk(): void {
    const key = this.selectedType.key;
    // Emit legacy events for embedded usage (management page)
    if (key === 'builtin') {
      this.openBuiltinMemoryLib.emit();
    } else if (key === 'external') {
      this.openExternalMemoryLib.emit();
    }
    // Invoke callback for programmatic usage (service)
    this.onConfirm?.(key);
    this.close();
  }

  onCancel(): void {
    this.close();
  }

  private close(): void {
    this.modalRef?.close();
  }

  /**
   * Open the type-selection modal (used by management page via @ViewChild).
   */
  show(): void {
    this.selectedType = this.typeItems[0];
    // Defer to next tick to ensure @ViewChild template refs are resolved
    setTimeout(() => {
      this.modalRef = this.nzModalService.create({
        nzTitle: this.selectCreateTitle,
        nzFooter: this.selectCreateFooter,
        nzContent: this.selectCreateType,
        nzWidth: 500,
        nzClosable: true,
        nzMaskClosable: false,
      });
    }, 0);
  }

  /**
   * Open the type-selection modal with a programmatic callback.
   * Used by MemoryLibService when no component instance exists in the DOM.
   */
  showWithCallback(onConfirm: (key: 'builtin' | 'external') => void): void {
    this.onConfirm = onConfirm;
    // Force change detection so @ViewChild template refs resolve even when
    // the component was created dynamically (not attached to the DOM).
    this.cdr.detectChanges();
    this.show();
  }
}
