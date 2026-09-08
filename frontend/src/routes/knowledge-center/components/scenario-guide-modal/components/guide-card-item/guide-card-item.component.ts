import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MODULES } from '@shared/modules';
import * as scenarioGuideModalConstant from '../../scenario-guide-modal.constant';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { CdkDragHandle } from '@angular/cdk/drag-drop';

@Component({
  selector: 'guide-card-item',
  templateUrl: './guide-card-item.component.html',
  styleUrls: ['./guide-card-item.component.scss'],
  standalone: true,
  imports: [
    MODULES,
    ReactiveFormsModule,
    NzFormModule,
    NzInputModule,
    NzSelectModule,
    NzTagModule,
    NzButtonModule,
    NzToolTipModule,
    NzIconModule,
    CdkDragHandle,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.COMMON],
    },
  ],
})
export class GuideCardItemComponent {
  @Input() guideDataItem: any;
  @Input() formGroupItem: FormGroup | any;
  @Input() guideItemIndex: number;
  @Input() formListLength: number;
  @Input() guideFormConfig: scenarioGuideModalConstant.FormConfig;
  @Input() skillSetOptions: scenarioGuideModalConstant.ISkillOption[] = [];
  @Output() changeCardCollapseEvent = new EventEmitter<any>();
  @Output() deleteGuideEvent = new EventEmitter<number>();
  @Output() removeEffectiveSkillTipEvent = new EventEmitter<any>();
  @Output() removeDeletedSkillTipEvent = new EventEmitter<any>();

  protected LEAST_GUIDE_COUNT = scenarioGuideModalConstant.LEAST_GUIDE_COUNT;
  protected SCENARIO_FIELD_ID = scenarioGuideModalConstant.SCENARIO_FIELD_ID;
  protected FIELD_TYPE = scenarioGuideModalConstant.FIELD_TYPE;
  public changeUrl = cdnAssetUrl;

  constructor() {}

  public changeCardCollapse(event: Event): void {
    event?.stopPropagation();
    this.changeCardCollapseEvent.emit(this.guideDataItem);
  }

  public deleteGuide(event: Event): void {
    event?.stopPropagation();
    this.deleteGuideEvent.emit(this.guideItemIndex);
  }

  public onRemoveEffectiveSkill(): void {
    this.removeEffectiveSkillTipEvent.emit();
  }

  public onRemoveDeletedSkill(): void {
    if (this.guideDataItem.deletedSkills?.length) {
      this.removeDeletedSkillTipEvent.emit();
    }
  }

  trackByIndex(index: number): number {
    return index;
  }

  compareWith(o1: any, o2: any): boolean {
    return o1?.id === o2?.id;
  }
}
