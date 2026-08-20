import { Component, ViewChild, ElementRef, OnInit, OnDestroy } from '@angular/core';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { ActivatedRoute, Router } from '@angular/router';
import { Subject } from 'rxjs';
import { CommonModule } from '@angular/common';
import {
  FormBuilder,
  FormControl,
  FormArray,
  Validators,
  FormsModule,
  ReactiveFormsModule
} from '@angular/forms';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { cloneDeep } from 'lodash';
import { IntentPackageService } from '../intent-package.service';
import { IntentInfo } from '../intent-package.interface';
import { BatchExampleComponent } from '../components/batch-example/batch-example.component';
import { ImportIntentModalComponent } from '../components/import-intent/import-intent.component';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { CommonService } from '@services/common.service';
import { HttpService } from '@services/http.service';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzModalModule, NzModalService } from 'ng-zorro-antd/modal';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzMessageService } from 'ng-zorro-antd/message';

@Component({
  selector: 'intent-detail',
  templateUrl: './intent-detail.component.html',
  styleUrls: ['./intent-detail.component.less'],
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MODULES,
    NzButtonModule,
    NzInputModule,
    NzIconModule,
    NzToolTipModule,
    NzFormModule,
    NzModalModule,
    NzSpinModule
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
    NzModalService
  ],
})
export class IntentDetailComponent implements OnInit, OnDestroy {
  @ViewChild('mainContainer') mainContainer?: ElementRef<HTMLElement>;

  subscribeBtnStatus = this.commonService.getSubscribeStatus();

  public changeUrl = cdnAssetUrl;
  private destroy$ = new Subject<void>();

  public intentPackageId = '';
  public intentPackageName = this.i18n.transform('default_intent_name');
  public isEditTitle = false;
  public editTitleValue = '';
  public intentName = '';
  public dataList: IntentInfo[] = [];
  public activeItem: IntentInfo | null = null;
  public searchKeyword = '';
  public isActive: number | null = null;
  public isOpen = false;
  public isAdd = true;

  public isLoading = false;
  public isPageLoading = false;

  public isGenerate = false;
  public previousUrl: string = '';
  public flowId: string = '';
  public workspaceId: string = '';
  public defaultPackName = this.i18n.transform('default_intent_name');

  public form = this.fb.group({
    name: new FormControl(this.defaultPackName, [
      Validators.maxLength(32),
      Validators.required,
      Validators.pattern(/^[\u4e00-\u9fa5a-zA-Z0-9_\-]+$/),
    ]),
  });

  public intentForm = this.fb.group({
    name: this.fb.control('', [
      Validators.maxLength(63),
      Validators.required,
      Validators.pattern(/^[\u4e00-\u9fa5a-zA-Z0-9_\-]+$/),
    ]),
    examples: this.fb.array<FormControl>([]),
  });

  private exampleValidator = Validators.pattern(/^[\u4e00-\u9fa5a-zA-Z0-9_\-]+$/);

  get questions(): FormArray {
    return this.intentForm.get('examples') as FormArray;
  }

  createQuestion(val = ''): FormControl {
    return this.fb.control(val, [
      this.exampleValidator,
      Validators.maxLength(63),
    ]);
  }

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private route: ActivatedRoute,
    private nzModalService: NzModalService,
    private readonly i18n: I18NextEagerPipe,
    private api: IntentPackageService,
    private elementRef: ElementRef,
    private setSidebarVisibilityService: SetSidebarVisibilityService,
    private commonService: CommonService,
    private readonly http: HttpService,
    private message: NzMessageService,
  ) {
    this.route.queryParams.subscribe((params) => {
      this.intentPackageId = params.id;
    });
  }

  ngOnInit() {
    this.setSidebarVisibilityService.setSidebarsVisibilityByState('init');
    this.route.queryParams.subscribe((params) => {
      const { previousUrl, flowId, workspaceId } = params;
      this.previousUrl = previousUrl;
      this.flowId = flowId;
      this.workspaceId = workspaceId;
    });
    if (!this.previousUrl) {
      this.getIntentPackageDetail();
      this.loadIntent('');
    }
  }

  onPageBack() {
    if (this.dataList.some((v) => !v.branch_id)) {
      this.nzModalService.confirm({
        nzTitle: this.i18n.transform('back_list_title'),
        nzContent: this.i18n.transform('back_list_tips'),
        nzOkText: this.i18n.transform('determined'),
        nzCancelText: this.i18n.transform('cancel'),
        nzOnOk: () => {
          if (this.previousUrl === 'agent') {
            this.goToWorkflow();
            return;
          }
          this.router.navigate(['/home/development-configuration'], {
            queryParams: { previousUrl: 'intent-manage' },
          });
        },
      });
    } else {
      if (this.previousUrl === 'agent') {
        this.goToWorkflow();
        return;
      }
      this.router.navigate(['/home/development-configuration'], {
        queryParams: { previousUrl: 'intent-manage' },
      });
    }
  }

  goToWorkflow() {
    if (this.intentPackageId) {
      localStorage.setItem(
        'intentAdded',
        JSON.stringify({
          name: this.form.value.name,
          intentId: this.intentPackageId,
          type: 'success',
        }),
      );
    }
    window.close();
  }

  getIntentPackageDetail() {
    this.api.getIntentPackageDetail(this.intentPackageId).then((res: any) => {
      this.intentPackageName = res.name ?? '';
      this.form.patchValue({
        name: this.intentPackageName,
      });
      this.isEditTitle = false;
    });
  }

  async loadIntent(intentPackageId) {
    if (intentPackageId) {
      this.intentPackageId = intentPackageId;
    }
    const res = await this.api.getIntentBranchesList(
      { offset: 0, limit: 1000 },
      this.intentPackageId,
    );
    if (res) {
      const data: any[] = res.branches || [];
      data.forEach((v) => {
        if (!v.examples) v.examples = [];
        if (!v.examples.length || v.examples[v.examples.length - 1]) {
          v.examples.push('');
        }
      });
      this.dataList = data;
    }
    this.postDel();
  }

  get intentList() {
    const arr = this.dataList.filter((v) => {
      if (this.searchKeyword) {
        return v.name.toLowerCase().includes(this.searchKeyword.toLowerCase());
      }
      return true;
    });
    this.isActive = arr.findIndex(
      (v) => v.branch_id === this.activeItem?.branch_id,
    );
    return arr;
  }

  addIntent(): void {
    if (this.subscribeBtnStatus) {
      this.isActive = 0;
      this.searchKeyword = '';
      this.intentName = this.i18n.transform('add_intention');
      while (this.dataList.some((v) => v.name === this.intentName)) {
        this.intentName += '_1';
      }
      this.isAdd = false;
      this.isOpen = true;
      this.questions.clear();
      this.questions.push(this.createQuestion());
      this.intentForm.reset();
      this.dataList.unshift({ name: this.intentName, examples: [''] });
      this.activeItem = cloneDeep(this.dataList[0]);
      this.intentForm.patchValue({ name: this.intentName });
      this.showGenerate();
    }
  }

  delIntent(e: Event, item: any): void {
    e.stopPropagation();
    this.activeItem = cloneDeep(item);

    if (this.activeItem.branch_id) {
      this.nzModalService.confirm({
        nzTitle: this.i18n.transform('delete_intent_title'),
        nzContent: this.i18n.transform('delete_intent_tips'),
        nzOkText: this.i18n.transform('determined'),
        nzCancelText: this.i18n.transform('cancel'),
        nzOnOk: () => {
          return this.api.deleteIntent(this.intentPackageId, this.activeItem.branch_id)
            .then(() => {
              this.dataList = this.dataList.filter(
                (dataItem) => dataItem.branch_id !== item.branch_id,
              );
              this.message.success(this.i18n.transform('deleted_successfully'));
              this.isAdd = true;
              this.postDel();
            });
        },
      });
    } else {
      this.dataList = this.dataList.filter((dataItem) => dataItem.branch_id !== item.branch_id);
      this.isAdd = true;
      this.postDel();
    }
  }

  onSearch(keyword: string): void {
    this.searchKeyword = keyword;
  }

  chooseIntent(item: IntentInfo, index: number): void {
    const isSearchedChange =
      this.searchKeyword &&
      JSON.stringify(
        this.dataList.find((i) => i.branch_id === this.activeItem?.branch_id),
      ) !== JSON.stringify(this.activeItem);

    if (
      (this.isActive !== -1 &&
        JSON.stringify(this.intentList[this.isActive]) !== JSON.stringify(this.activeItem)) ||
      isSearchedChange
    ) {
      this.nzModalService.confirm({
        nzTitle: this.i18n.transform('switch_intent_title'),
        nzContent: this.i18n.transform('switch_intent_tips'),
        nzOkText: this.i18n.transform('determined'),
        nzCancelText: this.i18n.transform('cancel'),
        nzOnOk: () => {
          this.executeChooseIntent(item, index);
        },
      });
    } else {
      this.executeChooseIntent(item, index);
    }
  }

  executeChooseIntent(item: IntentInfo, index: number) {
    this.isActive = index;
    this.activeItem = cloneDeep(item);
    this.intentName = this.activeItem.name;
    this.intentForm.patchValue({ name: this.activeItem.name });
    this.isOpen = Boolean(this.activeItem.examples?.length);
    this.questions.clear();

    if (this.activeItem?.examples) {
      this.activeItem.examples.forEach((v) => {
        this.questions.push(this.createQuestion(v));
      });
      this.showGenerate();
    }
  }

  onNameChange(val: string): void {
    if (this.activeItem) {
      this.activeItem.name = val;
    }
  }

  textChange(val: string, index: number): void {
    if (val) {
      this.activeItem.examples[index] = val;
      if (this.activeItem.examples.length - 1 === index) {
        this.activeItem.examples.push('');
        this.questions.push(this.createQuestion(''));
      }
    } else if (this.activeItem.examples.length - 1 !== index) {
      this.activeItem.examples.splice(index, 1);
      this.questions.removeAt(index);
    }
    this.showGenerate();
  }

  toggleQuestion(): void {
    this.isOpen = !this.isOpen;
  }

  showGenerate() {
    if (this.activeItem?.examples.length) {
      this.isGenerate = true;
    } else {
      this.isGenerate = false;
    }
  }

  addQuestion(): void {
    if (this.subscribeBtnStatus) {
      this.nzModalService.create({
        nzContent: BatchExampleComponent,
        nzClassName: 'batch-example-modal',
        nzFooter: null,
        nzData: {
          outputs: {
            getIntentExampleName: (name: string) => {
              const arr = name.split(',').filter((v) => !!v);
              if (arr.length) {
                this.questions.removeAt(this.activeItem.examples.length - 1);
                this.activeItem.examples.pop();
                arr.push('');
                arr.forEach((v) => {
                  this.activeItem.examples.push(v);
                  this.questions.push(this.createQuestion(v));
                });
              }
            },
          },
        },
      });
    }
  }

  deleteQuestion(index: number): void {
    this.activeItem?.examples.splice(index, 1);
    this.isOpen = Boolean(this.activeItem?.examples?.length);
    this.questions.removeAt(index);
    this.showGenerate();
  }

  startEditTitle(): void {
    this.editTitleValue = this.form.controls.name.value;
    this.isEditTitle = true;
  }

  onEditTitleChange(value: string): void {
    this.form.controls.name.setValue(value);
    this.form.controls.name.markAsDirty();
  }

  cancelEditTitle(): void {
    this.isEditTitle = false;
    this.form.patchValue({
      name: this.intentPackageName,
    });
  }

  savePackageName() {
    if (!this.#validatePackageName()) {
      return;
    }
    this.isLoading = true;

    const action = this.intentPackageId
      ? this.api.updateIntent({ id: this.intentPackageId, name: this.form.value.name })
      : this.api.createIntent({ name: this.form.value.name });

    action.then((res: any) => {
      this.message.success(this.i18n.transform('save_success'));
      if (!this.intentPackageId) {
        this.intentPackageId = res.intent_id;
      }
      this.getIntentPackageDetail();
    }).finally(() => {
      this.isLoading = false;
    });
  }

  #validatePackageName(): boolean {
    if (this.form.invalid) {
      Object.values(this.form.controls).forEach(c => {
        c.markAsDirty();
        c.updateValueAndValidity({ onlySelf: true });
      });
      this.message.error(this.i18n.transform('form_verify_fail_tips'));
      return false;
    }
    return true;
  }

  saveIntent() {
    if (!this.#validatePackageName()) {
      return;
    }
    if (!this.#validateIntent()) {
      return;
    }
    if (
      this.dataList.some(
        (v) => v.branch_id !== this.activeItem.branch_id && v.name === this.intentForm.value.name,
      )
    ) {
      this.message.error(this.i18n.transform('name_repeat_tips'));
      return;
    }

    this.isPageLoading = true;

    if (this.activeItem?.name) {
      this.activeItem.name = this.intentForm.value.name;
    }

    const payload: any = {
      name: this.form.value.name,
      branches: [
        {
          name: this.activeItem?.name,
          examples: this.activeItem?.examples.filter((v) => !!v),
        },
      ],
    };

    if (this.intentPackageId) {
      payload.id = this.intentPackageId;
      if (this.activeItem?.branch_id) {
        payload.branches[0].branch_id = this.activeItem?.branch_id;
      }
      this.api.updateIntent(payload)
        .then((res) => {
          this.message.success(this.i18n.transform('save_success'));
          this.isAdd = true;
          this.activeItem.branch_id = res.branch_id;
          this.dataList[this.isActive] = cloneDeep(this.activeItem);
          this.intentName = this.intentForm.value.name;
        })
        .finally(() => {
          this.isPageLoading = false;
        });
    } else {
      this.api.createIntent(payload)
        .then((res) => {
          this.message.success(this.i18n.transform('add_success'));
          const { branch_id, intent_id } = res;
          this.isAdd = true;
          this.activeItem.branch_id = branch_id;
          this.dataList[this.isActive] = cloneDeep(this.activeItem);
          this.intentName = this.intentForm.value.name;
          this.intentPackageId = intent_id;
        })
        .finally(() => {
          this.isPageLoading = false;
        });
    }
  }

  #validateIntent(): boolean {
    if (this.intentForm.invalid) {
      Object.values(this.intentForm.controls).forEach(control => {
        if (control instanceof FormArray) {
          control.controls.forEach(c => {
            c.markAsDirty();
            c.updateValueAndValidity({ onlySelf: true });
          });
        } else {
          control.markAsDirty();
          control.updateValueAndValidity({ onlySelf: true });
        }
      });

      const firstInvalidControlName = Object.keys(this.intentForm.controls).find(
        key => this.intentForm.controls[key].invalid
      );

      if (firstInvalidControlName) {
        if (firstInvalidControlName === 'examples') {
          const examples = this.intentForm.get('examples') as FormArray;
          const firstInvalidIndex = examples.controls.findIndex(c => c.invalid);
          if (firstInvalidIndex !== -1) {
            const inputElement = this.elementRef.nativeElement.querySelector(`input[name='${firstInvalidIndex}']`);
            if (inputElement) inputElement.focus();
          }
        } else {
          const inputElement = this.elementRef.nativeElement.querySelector(`[formControlName="${firstInvalidControlName}"]`);
          if (inputElement) inputElement.focus();
        }
      }
      this.message.error(this.i18n.transform('form_verify_fail_tips'));
      return false;
    }
    return true;
  }

  showImport() {
    this.nzModalService.create({
      nzContent: ImportIntentModalComponent,
      nzClassName: 'import-intent-modal',
      nzFooter: null,
      nzData: {
        intentId: this.intentPackageId,
        intentName: this.form.value.name,
        outputs: {
          refreshTable: (intentIds) => {
            this.loadIntent(intentIds?.[0] || '');
          },
        },
      },
    });
  }

  ngOnDestroy(): void {
    this.setSidebarVisibilityService.setSidebarsVisibilityByState('destroy');
    this.destroy$.next();
    this.destroy$.complete();
  }

  postDel() {
    if (this.dataList.length) {
      this.isActive = 0;
      this.activeItem = cloneDeep(this.dataList[0]);
      this.intentName = this.activeItem.name;
      this.intentForm.patchValue({
        name: this.activeItem.name,
      });
      this.questions.clear();
      this.activeItem.examples?.forEach((v) => {
        this.questions.push(this.createQuestion(v));
      });
      this.isOpen = Boolean(this.activeItem.examples?.length);
      this.showGenerate();
    } else {
      this.isActive = null;
      this.isOpen = false;
      this.intentName = '';
      this.activeItem = null;
      this.questions.clear();
      this.intentForm.reset();
    }
  }
}
