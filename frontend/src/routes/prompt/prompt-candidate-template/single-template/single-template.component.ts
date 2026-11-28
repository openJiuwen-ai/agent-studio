import {
  Component,
  OnInit,
  ChangeDetectionStrategy,
  Input,
  HostListener,
  Output,
  EventEmitter,
  SimpleChanges,
  OnChanges,
} from '@angular/core';
import { MODULES } from '@shared/modules';
import { NzRateModule } from 'ng-zorro-antd/rate';
import { PromptEditorComponent } from '@shared/components/prompt-editor/prompt-editor.component';
import { TmplVariantTagComponent } from '@shared/components/tmpl-variant-tag/tmpl-variant-tag.component';
import { PromptEditorService } from '@services/prompt-editor.service';
import { I18nNamespace } from '@i18n';
import * as angularI18next from 'angular-i18next';
import { IPromptChunk } from '@interfaces/prompt/prompt-editor.interface';
import { ActivatedRoute, Router } from '@angular/router';
import { NzModalRef, NzModalService, NzModalModule } from 'ng-zorro-antd/modal';
import * as candidateTemplateListInterface from '@interfaces/prompt/candidate-template-list.interface';
import { CandidateTemplateListService } from '@services/candidate-template-list.service';
import { GETVARIANT_REG } from '@constants/exp-tmpl-config.const';
import { NzPopconfirmModule } from 'ng-zorro-antd/popconfirm';
import { MessageComponent } from '@shared/services/cfdata.service';
import { RouteParamsService } from '@services/routeParams.service';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { PromptWritingService } from '@services/prompt-writing.service';
import { ECandSaveType } from '@enums/prompt-writing.enum';
import { isNil } from 'lodash';

@Component({
  selector: 'meta-single-template',
  templateUrl: './single-template.component.html',
  styleUrls: ['./single-template.component.scss'],
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    MODULES,
    NzRateModule,
    PromptEditorComponent,
    TmplVariantTagComponent,
    NzPopconfirmModule,
    NzModalModule,
  ],
  providers: [
    {
      provide: angularI18next.I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.PROMPT_PLATFORM],
    },
  ],
})
export class SingleTemplateComponent implements OnInit, OnChanges {
  @Input() idx: number;
  @Input() item: candidateTemplateListInterface.ICandidateTmplData;

  @Input() promptTmplIds: string[];

  @Output() deleteCurrentTmpl = new EventEmitter<void>();

  public isMoveToCard = false;
  public singleTmplContent: IPromptChunk[];

  public isTaskInProgress = true;
  public isShowEvaluation = false;
  public changeUrl = cdnAssetUrl;
  public isEditing: boolean = false;

  private task_id: string;

  constructor(
    private promptEditorServ: PromptEditorService,
    private router: Router,
    private nzModal: NzModalService,
    private candidateTemplateListServe: CandidateTemplateListService,
    private route: ActivatedRoute,
    private routeParamsServe: RouteParamsService,
    private promptWritingServ: PromptWritingService,
    private i18n: angularI18next.I18NextEagerPipe,
  ) {
    this.route.queryParams.subscribe((params) => {
      this.task_id = params.taskId;
    });
  }

  async ngOnInit() {
    this.singleTmplContent = this.promptEditorServ.processVar(
      this.item.content,
    );
    if (this.item.evaluation_avg !== -1) {
      this.isShowEvaluation = true;
    }
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.promptTmplIds) {
      if (changes.promptTmplIds.currentValue.includes(this.item.id)) {
        this.isTaskInProgress = true;
      } else {
        this.isTaskInProgress = false;
      }
    }
  }

  public toPromptWriting() {
    this.router.navigate(['/home/prompt/prompt-writing'], {
      queryParams: {
        taskId: this.task_id || '',
        candidateId: this.item.id || '',
        activeMenuItemId: `edit-candidate${this.item.id}`,
        isEdit: true,
      },
    });
  }

  public toPromptCandidate() {
    this.router.navigate(['/home/prompt/prompt-writing'], {
      queryParams: {
        taskId: this.task_id || '',
        candidateId: this.item.id || '',
        activeMenuItemId: `edit-candidate${this.item.id}`,
      },
    });
  }

  public showSaveTmplModal() {
    this.routeParamsServe.setTemplateName(this.item.name);
    const modalRef: NzModalRef = this.nzModal.create({
      nzTitle: this.i18n.transform('candidate_template_saveTemplateLibrary'),
      nzWidth: '800px',
      nzClosable: true,
      nzMaskClosable: false,
      nzFooter: [
        {
          label: this.i18n.transform('cancel'),
          onClick: () => modalRef.close(),
        },
        {
          label: this.i18n.transform('ok'),
          type: 'primary',
          onClick: () => {
            const formInstance = modalRef.getContentComponent()?.formName;
            if (formInstance?.value?.templateName) {
              const params = {
                task_id: this.task_id,
                id: '',
                name: formInstance.value.templateName,
                content: this.item.content,
                source: 'PLAYGROUND',
                variables: this.processString(this.item.content),
              };
              this.candidateTemplateListServe.createFormalTmpl(params).subscribe({
                next: (res) => {
                  MessageComponent.showSuccess(
                    this.i18n.transform('single_tmpl_save_success_tip'),
                  );
                },
              });
            }
            modalRef.close();
          },
        },
      ],
    });
  }

  public processString(input: string): string {
    const matches = input.match(GETVARIANT_REG);
    if (matches) {
      const extractedValues = matches.map((match) => match.slice(2, -2));
      return extractedValues.join(',');
    }
    return '';
  }

  public deleteSingleTmplButton() {
    this.nzModal.confirm({
      nzTitle: this.i18n.transform('single_tmpl_delete_confirm'),
      nzOkText: this.i18n.transform('ok'),
      nzCancelText: this.i18n.transform('cancel'),
      nzOnOk: () => this.deleteSingleTmpl(),
    });
  }

  public deleteSingleTmpl() {
    this.candidateTemplateListServe
      .deleteCandidateTmpl(this.item.id)
      .subscribe({
        next: (res) => {
          this.deleteCurrentTmpl.emit();
          MessageComponent.showSuccess(
            `${this.item.name} ${this.i18n.transform('base_delete_success')}`,
          );

          this.promptWritingServ.setCandChangeInfo({
            type: ECandSaveType.SAVE,
          });
        },
      });
  }

  public openLabelEditor() {
    this.isEditing = true;
  }

  public confirmTitleChange() {
    const params = {
      id: this.item.id,
      name: this.item.name,
    };
    this.candidateTemplateListServe.updateCandidateTmplTitle(params).subscribe({
      next: (res) => {
        MessageComponent.showSuccess(
          this.i18n.transform('single_tmpl_edit_name_success'),
        );
      },
    });
    this.isEditing = false;
  }

  public isNotNil(val: any): boolean {
    return !isNil(val);
  }

  @HostListener('mouseenter') onMouseEnter() {
    this.isMoveToCard = true;
  }

  @HostListener('mouseleave') onMouseLeave() {
    this.isMoveToCard = false;
  }
}
