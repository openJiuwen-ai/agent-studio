import { Component, EventEmitter, Input, Output, inject } from '@angular/core';
import { NzModalRef } from 'ng-zorro-antd/modal';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { RefTypeToTextPipe } from 'src/pipes/ref-type-to-text.pipe';
import { HttpService } from '@services/http.service';
import { SkillApi } from '@agentcore/api/skill.api';
import { I18nService } from '@agentcore/core/i18n.service';
import { I18nPipe } from '@agentcore/shared/pipes/i18n.pipe';
import { BehaviorSubject, catchError, map, of } from 'rxjs';
import { ActivatedRoute, Router } from '@angular/router';
@Component({
  selector: 'skill-delete-modal',
  templateUrl: './skill-delete-modal.component.html',
  styleUrls: ['./skill-delete-modal.component.scss'],
  standalone: true,
  imports: [MODULES, RefTypeToTextPipe, I18nPipe],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class SkillDeleteModalComponent {
  readonly modalRef = inject(NzModalRef);
  @Input() id: string = '';
  @Input() name: string = '';

  srcData: any = {
    data: [],
    state: {
      searched: false,
      sorted: false,
      paginated: true,
    },
  };

  totalNumber: number = 0;

  @Output() confirm = new EventEmitter();

  public columns: Array<any> = [
    {
      title: this._i18n.transform('name'),
    },
    {
      title: this._i18n.transform('skill.agentVersion.notExist'),
    },
    {
      title: this._i18n.transform('type'),
    },
  ];

  public pageSize = {
    options: [10, 20, 50, 100],
    size: 10,
  };

  public currentPage: number = 1;

  public deleteVal = '';

  public errorClass = false;

  constructor(
    private readonly http: HttpService,
    private _skillApi: SkillApi,
    private _i18n: I18nService,
    private router: Router
  ) {}
  ngOnInit() {
    this.getMappingsByPage();
  }

  public close() {
    this.modalRef.destroy();
  }

  public dismiss() {
    this.modalRef.destroy();
  }

  public onConfirm() {
    if (this.deleteVal === 'DELETE' || this.srcData.data.length === 0) {
      this.close();
      this.confirm.emit();
    } else {
      this.errorClass = true;
    }
  }

  public getMappingsByPage() {
    this._skillApi
      .queryReference(this.id, 0, 10)
      .pipe(
        map((res: any) => {
          this.srcData.data = res.relations || [];
          this.totalNumber = res.count || 0;
          const relations = res.relations || [];
          return relations;
        }),
        catchError(() => of(false))
      )
      .subscribe(
        relations => {},
        () => {}
      );
  }

  public navigateAppDetail(row: any) {
    this.close();
    this.router.navigate(['/home/agent-center/app-agent/detail'], {
      queryParams: {
        agentId: row.app_id,
      },
    });
  }
}
