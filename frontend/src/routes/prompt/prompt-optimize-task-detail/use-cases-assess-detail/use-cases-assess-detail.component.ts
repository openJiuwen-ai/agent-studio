import { ChangeDetectionStrategy, ChangeDetectorRef, Component, Input, ViewEncapsulation } from '@angular/core';
import { MODULES } from '@shared/modules';
import { ReactiveFormsModule } from '@angular/forms';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzPaginationModule } from 'ng-zorro-antd/pagination';
import { PromptOptimizeService } from '@services/agent-center/prompt-optimize-task/prompt-optimize.service';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';

@Component({
  selector: 'meta-use-cases-assess-detail',
  standalone: true,
  imports: [MODULES, ReactiveFormsModule, NzTableModule, NzPaginationModule],
  templateUrl: './use-cases-assess-detail.component.html',
  styleUrl: './use-cases-assess-detail.component.scss',
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.COMMON, I18nNamespace.PROMPT_PLATFORM],
    },
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
})
export class UseCasesAssessDetailComponent {
  @Input() ptType: 'text' | 'multi';
  @Input() variables: any;
  @Input() taskId: string;
  @Input() iterNum: string;
  pageInfo: {
    total: number;
    pageSize: { options: number[]; size: number };
    currentPage: number;
  } = {
    total: 0,
    pageSize: {
      options: [10, 15, 20, 25],
      size: 10,
    },
    currentPage: 1,
  };
  displayedData: Array<any> = [];
  srcData: { data: any[]; state?: { searched: boolean; sorted: boolean; paginated: boolean } } = {
    data: [],
    state: {
      searched: false,
      sorted: false,
      paginated: false,
    },
  };
  columns: Array<{ title: string; width?: string; sortKey?: string; compareFn?: (a: any, b: any, sortKey: string) => number }> = [
    {
      title: this.i18n.transform('base_number'),
      width: '60px',
    },
    {
      title: this.i18n.transform('evaluation_data'),
      width: '230px',
    },
    {
      title: this.i18n.transform('system_response'),
    },
    {
      title: this.i18n.transform('expected_response'),
    },
    {
      title: this.i18n.transform('answer_score'),
      width: '100px',
      sortKey: 'score',
      compareFn: (a: any, b: any, sortKey: string): number => {
        return a[sortKey] - b[sortKey];
      },
    },
    {
      title: this.i18n.transform('score_reason'),
    },
  ];

  constructor(
    private promptOptimizeService: PromptOptimizeService,
    private cdr: ChangeDetectorRef,
    private i18n: I18NextEagerPipe
  ) {}

  ngOnInit() {
    if (this.ptType === 'multi') {
      this.columns = [
        {
          title: this.i18n.transform('base_number'),
          width: '60px',
        },
        {
          title: this.i18n.transform('evaluation_data'),
          width: '265px',
        },
        {
          title: this.i18n.transform('image'),
        },
        {
          title: this.i18n.transform('system_response'),
        },
        {
          title: this.i18n.transform('expected_response'),
        },
        {
          title: this.i18n.transform('answer_score'),
          width: '100px',
          sortKey: 'score',
          compareFn: (a: any, b: any, sortKey: string): number => {
            return a[sortKey] - b[sortKey];
          },
        },
        {
          title: this.i18n.transform('score_reason'),
        },
      ];
    }
  }

  pageChange(): void {
    this.displayedData = this.srcData.data.slice(
      (this.pageInfo.currentPage - 1) * this.pageInfo.pageSize.size,
      this.pageInfo.currentPage * this.pageInfo.pageSize.size
    );
  }

  public getDetail() {
    this.promptOptimizeService.listEvalDetail(this.taskId, this.iterNum).then(res => {
      this.srcData.data = res.data.map(item => {
        const images = [];
        const useCase = JSON.parse(item.variable);
        for (let variable of this.variables) {
          if (variable.type === 'multi') {
            images.push({
              name: '',
              previewUrl: useCase[variable.value],
            });
          }
        }
        return {
          ...item,
          images,
        };
      });
      this.pageInfo.total = res.data.length;
      this.pageChange();
      this.cdr.detectChanges();
    });
  }
}
