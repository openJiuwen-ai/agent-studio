import { CommonModule } from '@angular/common';
import { Component, computed, DestroyRef, inject, Signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { I18NextModule } from 'angular-i18next';
import { catchError, from, mergeMap } from 'rxjs';
import { SkillApi } from '@agentcore/api/skill.api';
import { SkillDetail, SkillDetailFromPage, skillDetailSignal, SkillSourceTag, SkillStatusTag } from '@agentcore/constants/skill.model';
import { I18nService } from '@agentcore/core/i18n.service';
import { CustomHeaderComponent } from '@agentcore/shared/components/custom-header/custom-header.component';
import { CustomHeaderParam } from '@agentcore/shared/components/custom-header/model';
import { CopyTextRenderComponent } from '@agentcore/shared/components/operator/copy-text-render.component';
import { HeaderButtonOperator } from '@agentcore/shared/components/operator/header-button-operator.component';
import { OperatorWithSpaceComponent, OperatorWithSpaceParams } from '@agentcore/shared/components/operator/operator-with-space.component';
import { SimpleModalComponent } from '@agentcore/shared/components/simple-modal/simple-modal.component';
import { I18nPipe } from '@agentcore/shared/pipes/i18n.pipe';
import { CustomEditorService } from '@agentcore/shared/services/custom-editor.service';
import { LayoutPageComponent } from '@shared/components/layout-page/layout-page.component';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { MODULES } from '@shared/modules';
import { NzModalService } from 'ng-zorro-antd/modal';
import { SkillReferenceHalfmodalComponent } from './skill-reference-halfmodal/skill-reference-halfmodal.component';
import { SkillSingleEditorComponent } from './skill-single-editor/skill-single-editor.component';
import { NzDrawerService } from 'ng-zorro-antd/drawer';
@Component({
  templateUrl: './skill-detail.component.html',
  styleUrl: './skill-detail.component.scss',
  selector: 'skill-detail',
  standalone: true,
  imports: [
    I18NextModule,
    CommonModule,
    SkillSingleEditorComponent,
    LayoutPageComponent,
    I18nPipe,
    OperatorWithSpaceComponent,
    HeaderButtonOperator,
    SkillReferenceHalfmodalComponent,
    SimpleModalComponent,
    CopyTextRenderComponent,
    CustomHeaderComponent,
    MODULES,
  ],
  providers: [I18nService, CustomEditorService],
})
export class SkillDetailComponent {
  skillDetail: SkillDetail | null;
  from = this._route.snapshot.queryParamMap.get('from') ?? SkillDetailFromPage.SKILL;
  skillId = this._route.snapshot.queryParamMap.get('id');
  fromSkill = this.from === SkillDetailFromPage.SKILL;
  fromUrl = this.from === SkillDetailFromPage.SKILL ? '/home/agent-center/library-home?tabId=skill' : '/home/skill-market';
  historyModalInstance;
  headerParams: Signal<CustomHeaderParam> = computed(() => {
    this.skillDetail = skillDetailSignal();
    const res = {
      crumb: [
        {
          label: this._i18n.transform('common.openjiuwen.crumb'),
          clickFn: () => this._router.navigate(['/home']),
        },
        {
          label:
            this.from === SkillDetailFromPage.SKILL ? this._i18n.transform('skill.detail.skill.crumb') : this._i18n.transform('skill.detail.resource.crumb'),
          clickFn: () => this._router.navigateByUrl(this.fromUrl),
        },
        {
          label: this.skillDetail?.skillName,
        },
      ],
      title: this.skillDetail?.skillName,
      img: this.skillDetail?.icon,
      tags: this.getTitleTag(),
      operators: this.generateOperator(),
    };

    return res;
  });
  private destoryRef = inject(DestroyRef);

  constructor(
    private _route: ActivatedRoute,
    private _router: Router,
    private nzModal: NzModalService,
    private _skillApi: SkillApi,
    private _i18n: I18nService,
    private _customEditorService: CustomEditorService,
    private _setSidebarVisibilityService: SetSidebarVisibilityService,
    private drawerService: NzDrawerService
  ) {}

  ngOnInit() {
    this._setSidebarVisibilityService.setSidebarsVisibilityByState('init');
  }

  ngAfterViewInit() {
    this.querySkillDetail(true);
  }

  generateOperator(): Array<any> {
    return [
      {
        label: this._i18n.transform('skill.detail.export'),
        type: 'default',
        click: (): void => {
          if (!this.skillDetail) {
            return;
          }
          this._skillApi
            .exportSkillVersion(this.skillDetail!.skillId)
            .pipe(
              mergeMap(e => from(this._customEditorService.downloadAndRenameZip(e.obs_url, `${this.skillDetail.skillName}.zip`))),
              catchError(e => {
                throw e;
              })
            )
            .subscribe();
        },
      },
      {
        label: this._i18n.transform('skill.detail.operator.reference'),
        type: 'default',
        click: (): void => {
          this.drawerService.create({
            nzContent: SkillReferenceHalfmodalComponent,
            nzWidth: 700,
            nzData: {
              skillId: this.skillDetail?.skillId,
            },
          });
        },
      },
    ];
  }

  ngOnDestroy(): void {
    this._setSidebarVisibilityService.setSidebarsVisibilityByState('destroy');
    skillDetailSignal.set(null);
  }

  paseData(data) {
    if (data) {
      var date = new Date(data);
      const Y = date.getFullYear() + '/';
      const M = (date.getMonth() + 1 < 10 ? '0' + (date.getMonth() + 1) : date.getMonth() + 1) + '-';
      const D = (date.getDate() < 10 ? '0' + date.getDate() : date.getDate()) + ' ';
      const h = (date.getHours() < 10 ? '0' + date.getHours() : date.getHours()) + ':';
      const m = (date.getMinutes() < 10 ? '0' + date.getMinutes() : date.getMinutes()) + ':';
      const s = date.getSeconds() < 10 ? '0' + date.getSeconds() : date.getSeconds();
      return Y + M + D + h + m + s;
    } else {
      return '';
    }
  }

  querySkillDetail(initQuery = false) {
    this._skillApi
      .querySkillDetail(this.skillId, {
        fail: this._i18n.transform('skill.detail.query.fail', { id: this.skillDetail?.skillName ?? this.skillId }),
      })
      .pipe(takeUntilDestroyed(this.destoryRef))
      .subscribe({
        next: data => {
          skillDetailSignal.set(data);
        },
        error: err => {
          this._router.navigateByUrl(this.fromUrl.replace(/^(\/#|#)/, ''));
        },
      });
  }

  existView() {
    if (this.historyModalInstance) {
      this.historyModalInstance.content.instance.close();
    }
    this.querySkillDetail();
  }

  exportOperator() {
    return {
      type: 'iconaction',
      iconaction: {
        label: this._i18n.transform('skill.detail.export'),
        iconName: 'cloudx-action-export-file',
      },
      hide: !this.fromSkill || this.skillDetail?.viewMode,
      click: (): void => {
        if (!this.skillDetail) {
          return;
        }
        this._skillApi
          .exportSkillVersion(this.skillDetail!.skillId)
          .pipe(
            mergeMap(e => from(this._customEditorService.downloadAndRenameZip(e.obs_url, `${this.skillDetail.skillName}.zip`))),
            catchError(e => {
              throw e;
            })
          )
          .subscribe();
      },
    };
  }

  openReferenceModal() {
    return {
      type: 'iconaction',
      iconaction: {
        label: this._i18n.transform('skill.detail.operator.reference'),
        iconName: 'cloudx-action-binging',
      },
      click: (): void => {
        this.drawerService.create({
          nzContent: SkillReferenceHalfmodalComponent,
          nzWidth: 700,
          nzData: {
            skillId: this.skillDetail?.skillId,
          },
        });
      },
    };
  }

  editSkill() {
    return {
      type: 'component',
      hide: !this.fromSkill,
      component: {
        type: HeaderButtonOperator,
        params: {
          text: this._i18n.transform('skill.detail.editorButton'),
          color: 'major',
          tip: this._i18n.transform('skill.detail.editorButtonTip'),
        },
      },
    };
  }

  getTitleTag() {
    if (!this.skillDetail) {
      return [];
    }
    if (this.fromSkill) {
      const statusConfig = SkillStatusTag[this.skillDetail.status];
      const sourceConfig = SkillSourceTag[this.skillDetail.source];
      return [
        this.skillDetail.status
          ? {
              ...statusConfig,
              label: statusConfig?.labelKey ? this._i18n.transform(statusConfig.labelKey) : this.skillDetail.status,
            }
          : undefined,
        this.skillDetail.source
          ? {
              ...sourceConfig,
              label: sourceConfig?.labelKey ? this._i18n.transform(sourceConfig.labelKey) : this.skillDetail.source,
            }
          : undefined,
      ].filter(e => e);
    }
    return [];
  }
}
