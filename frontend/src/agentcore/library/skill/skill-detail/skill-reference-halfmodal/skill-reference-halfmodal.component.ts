import { CommonModule } from '@angular/common';
import { Component, inject, Inject } from '@angular/core';
import { Router } from '@angular/router';
import { NzTableModule } from 'ng-zorro-antd/table';
import { MODULES } from '@shared/modules';
import { I18nService } from '@agentcore/core/i18n.service';
import { I18nPipe } from '@agentcore/shared/pipes/i18n.pipe';
import { SkillReferenceTableService } from './skill-reference-table.service';
import { SkillApi } from '@agentcore/api/skill.api';
import { NZ_DRAWER_DATA, NzDrawerModule, NzDrawerRef } from 'ng-zorro-antd/drawer';
import { NzPaginationModule } from 'ng-zorro-antd/pagination';
@Component({
  selector: 'skill-reference-halfmodal',
  templateUrl: './skill-reference-halfmodal.component.html',
  styleUrls: ['./skill-reference-halfmodal.component.scss'],
  standalone: true,
  imports: [CommonModule, I18nPipe, NzTableModule, MODULES, NzPaginationModule],
  providers: [I18nService, SkillReferenceTableService],
})
export class SkillReferenceHalfmodalComponent extends SkillReferenceTableService {
  override skillId: string;
  total = 0;
  ListData: any[] = [];
  loading = true;
  pageSize = 12;
  pageIndex = 1;
  cardPageSizeoptions = [12, 24, 48, 64];
  title = [this._i18n.transform('skill.detail.reference.header.appName'), this._i18n.transform('skill.detail.reference.header.appVersion')];
  readonly drawerRef = inject(NzDrawerRef);
  constructor(
    private router: Router,
    @Inject(NZ_DRAWER_DATA) public nzData: any
  ) {
    super();
    this.skillId = this.nzData.skillId;
  }

  dismiss() {
    this.drawerRef.close();
  }

  close() {
    this.drawerRef.close();
  }

  ngOnInit() {
    this.onQueryParamsChange();
  }

  public onQueryParamsChange() {
    const nextOffset = (this.pageIndex - 1) * this.pageSize;
    const limit = this.pageSize;
    this._skillApi.queryReference(this.skillId, nextOffset, limit).subscribe(response => {
      this.total = response.const;
      this.ListData = (response.relations || []).map(item => {
        if (!item.app_version) {
          item.app_version = this._i18n.transform('skill.agentVersion.notExist');
        }
        return item;
      });
    });
  }

  public linkto(data) {
    this.router.navigate([`/home/agent-center/app-agent/detail`], {
      queryParams: { agentId: data.app_id },
    });
    this.drawerRef.close();
  }
}
