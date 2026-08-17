import {
  Component,
  OnInit,
  OnChanges,
  Input,
  Output,
  EventEmitter,
  ViewChild,
  ElementRef,
  SimpleChanges,
} from '@angular/core';
import { FormBuilder, FormControl, Validators } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE } from 'angular-i18next';

@Component({
  selector: 'edit-name',
  templateUrl: './edit-name.component.html',
  styleUrls: ['./edit-name.component.scss'],
  standalone: true,
  imports: [MODULES],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.AGENT_CENTER,
        I18nNamespace.MODEL_ACCESS,
        I18nNamespace.REVIEW,
      ],
    },
  ],
})
export class EditNameComponent implements OnInit, OnChanges {
  @Input() name!: any;
  @Output() nameChange = new EventEmitter<any>();
  @Output() onBlurConfirm = new EventEmitter();

  @ViewChild('nameInput') nameInput: ElementRef<HTMLTextAreaElement>;

  public groupFormControl = this.fb.group({
    name: new FormControl('', [Validators.required]),
  });

  shoNameDiv = true;

  constructor(private fb: FormBuilder) {}

  ngOnInit() {
    this.groupFormControl.controls.name.setValue(this.name || '');
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.name && !changes.name.firstChange && this.shoNameDiv) {
      this.groupFormControl.controls.name.setValue(this.name || '');
    }
  }

  nameDivClice() {
    this.shoNameDiv = false;
    setTimeout(() => {
      this.nameInput?.nativeElement?.focus();
    });
  }

  onBlur() {
    this.groupFormControl.markAllAsTouched();
    if (this.groupFormControl.valid) {
      this.shoNameDiv = true;
      this.name = this.groupFormControl.value.name;
      this.nameChange.emit(this.name);
      this.onBlurConfirm.emit();
    }
  }

  dismiss(): void {}

  close(): void {}
}
