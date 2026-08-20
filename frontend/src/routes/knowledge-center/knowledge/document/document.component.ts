import { ChangeDetectorRef, Component, EventEmitter, Input, OnChanges, OnInit, OnDestroy, Output, SimpleChanges, ViewChild } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { I18nNamespace } from '@i18n';
import { Network } from '@model';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { IKbQueryBase, IFile } from '@routes/agent-center/app-knowledge/knowledge.types';
import { KbFileTagEditComponent } from '@routes/knowledge-center/components/kb-file-tag-edit/kb-file-tag-edit.component';
import { FileUploadComponent } from '@routes/knowledge-center/file-upload/file-upload.component';
import { TaskType } from '@routes/knowledge-center/knowledge.types';
import { KnowledgeRepoService } from '@services/agent-center/knowledge.service';
import { KbAbilitiesService } from '@services/knowledge-center/kb-abilities.service';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { BehaviorSubject, Subject, catchError, expand, finalize, from, map, mergeMap, of, switchMap, takeUntil, takeWhile, tap, timer, toArray } from 'rxjs';
import { BytesPipe } from 'src/pipes/bytes.pipe';
import { FormateTimePipe } from 'src/pipes/formate-time.pipe';
import { CommonUtils } from 'src/utils/common.util';
import { BatchDeleteComponent } from '../batch-delete.component';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { NzTableModule, NzTableQueryParams } from 'ng-zorro-antd/table';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzBadgeModule } from 'ng-zorro-antd/badge';
import { NzTypographyModule } from 'ng-zorro-antd/typography';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzModalService, NzModalModule } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzDrawerService, NzDrawerModule } from 'ng-zorro-antd/drawer';
import { NzDividerModule } from 'ng-zorro-antd/divider';
import { NzTagModule } from 'ng-zorro-antd/tag';
import {HttpService} from "@services/http.service";

const SUPPORTED_FORMATS = [
  'doc',
  'docx',
  'pdf',
  'pptx',
  'ppt',
  'xlsx',
  'xls',
  'csv',
  'wps',
  'png',
  'jpg',
  'jpeg',
  'bmp',
  'gif',
  'tiff',
  'tif',
  'webp',
  'pcx',
  'ico',
  'psd',
  'dps',
  'et',
  'txt',
  'ofd',
  'md',
  'html',
  'mhtml',
];

enum mapKey {
  kb = 'kb',
  chunkMethod = 'chunkMethod',
}

@Component({
  selector: 'knowledge-document',
  templateUrl: './document.component.html',
  styleUrls: ['./document.component.less'],
  imports: [
    MODULES,
    BytesPipe,
    BatchDeleteComponent,
    KbFileTagEditComponent,
    RouterModule,
    FormsModule,
    NzTableModule,
    NzButtonModule,
    NzInputModule,
    NzSelectModule,
    NzBadgeModule,
    NzTypographyModule,
    NzIconModule,
    NzEmptyModule,
    NzModalModule,
    NzDrawerModule,
    NzDividerModule,
    NzTagModule,
  ],
  providers: [
    {
      useValue: [I18nNamespace.COMMON, I18nNamespace.KNOWLEDGE, I18nNamespace.AGENT_CENTER],
      provide: I18NEXT_NAMESPACE,
    },
    FormateTimePipe,
    NzModalService,
    NzMessageService,
    NzDrawerService,
  ],
  standalone: true,
})
export class DocumentComponent implements OnInit, OnChanges, OnDestroy {
  @Input() kbId!: string;
  @Input() kb: any;
  @Input() chunkMethod!: string;
  @Input() isMarket = false;
  @Output() refreshDetail = new EventEmitter();
  @Output() goToTagManage = new EventEmitter();
  @ViewChild('batchDeleteModal') batchDeleteModal!: BatchDeleteComponent;
  @ViewChild('kbFileTagEdit') kbFileTagEdit!: KbFileTagEditComponent;

  tableData: any[] = [];
  loading = false;
  total = 0;
  pageIndex = 1;
  pageSize = 10;
  emptyImage = `${Network.ASSETS_PATH}images/noData.svg`;
  searchName = '';
  searchStatus: string | null = null;
  searchFileType: string | null = null;
  fileTypeOptions: { label: string; value: string }[] = [];
  statusOptions: { label: string; value: string }[] = [];
  setOfCheckedId = new Set<string>();
  allChecked = false;
  indeterminate = false;

  public bytes = new BytesPipe();
  public isDownloading = false;
  public isFaqEnable = false;
  public isRagFlow = false;

  get isOpenJiuwen() {
    return this.configServ.openjiuwenKbEnable() && this.kb?.source?.knowledge_base_connector_id === 'OpenjiuwenInside';
  }

  ocrAccept =
    '.doc, .docx, .pdf, .pptx, .ppt, .xlsx, .xls, .csv, .wps, .png, .jpg, .jpeg, .bmp, .gif, .tiff, .tif, .webp, .pcx, .ico, .psd, .dps, .et, .txt, .ofd, .md, .html, .mhtml';
  acceptWithNoOcr = '.doc, .docx, .pdf, .pptx, .ppt, .xlsx, .xls, .csv, .wps, .dps, .et, .txt, .ofd, .md, .html, .mhtml';
  ragAccept = '.doc, .docx, .xlsx, .xls, .md, .txt, .html';

  public regFileType = new Map([
    ['naive', '.docx, .xlsx, .xls, .md, .txt, .html, .csv'],
    ['qa', '.xlsx, .xls, .txt, .csv'],
    ['table', '.xlsx, .xls, .txt, .csv'],
    ['book', '.docx, .txt'],
    ['laws', '.docx, .txt'],
    ['one', '.docx, .xlsx, .xls, .txt'],
  ]);

  private destroy$ = new Subject<void>();
  private loadTrigger$ = new BehaviorSubject<void>(undefined);

  constructor(
    private kbRepoServ: KnowledgeRepoService,
    private nzMessage: NzMessageService,
    private nzModal: NzModalService,
    private nzDrawerService: NzDrawerService,
    private cdr: ChangeDetectorRef,
    private i18n: I18NextEagerPipe,
    private configServ: AgentConfigService,
    public kbAbilitiesService: KbAbilitiesService,
    private formateTimePipe: FormateTimePipe,
    private httpClient: HttpClient,
    private readonly http: HttpService,
  ) {
    this.isFaqEnable = this.configServ.faqEnable();
    this.isRagFlow = this.configServ.knowledgeSource() === 'AgentBaseRag';
  }

  ngOnInit() {
    this.initFilterOptions();
    this.setupDataPolling();
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes[mapKey.kb]?.currentValue || changes[mapKey.chunkMethod]?.currentValue) {
      this.initFilterOptions();
      this.loadTrigger$.next();
    }
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private initFilterOptions() {
    const { knowledge_file_types } = this.configServ.getConfigs();

    if (this.isRagFlow) {
      this.statusOptions = [
        { label: this.i18n.transform('success'), value: 'SUCCESS' },
        { label: this.i18n.transform('error'), value: 'ERROR' },
        { label: this.i18n.transform('pending'), value: 'PENDING' },
        { label: this.i18n.transform('running'), value: 'RUNNING' },
      ];
    } else {
      this.statusOptions = [
        { label: this.i18n.transform('success'), value: 'SUCCESS' },
        { label: this.i18n.transform('error'), value: 'ERROR' },
        { label: this.i18n.transform('enhance'), value: 'POST_PROCESSING' },
        { label: this.i18n.transform('waiting_queue'), value: 'CREATED' },
        { label: this.i18n.transform('pending'), value: 'PENDING' },
        { label: this.i18n.transform('running'), value: 'RUNNING' },
        { label: this.i18n.transform('inventory_in_progress'), value: 'INBOUND' },
      ];
    }

    if (this.isRagFlow) {
      this.fileTypeOptions = [
        { label: 'doc', value: 'doc' },
        { label: 'docx', value: 'docx' },
        { label: 'xlsx', value: 'xlsx' },
        { label: 'xls', value: 'xls' },
        { label: 'md', value: 'md' },
        { label: 'txt', value: 'txt' },
        { label: 'html', value: 'html' },
      ];
      if (this.chunkMethod) {
        const fileTypeArr = this.regFileType.get(this.chunkMethod)?.split(', .') || [];
        if (fileTypeArr.length) {
          this.fileTypeOptions = fileTypeArr.map(item => {
            const result = item.includes('.') ? item.slice(1) : item;
            return { label: result, value: result };
          });
        }
      }
    } else if (knowledge_file_types?.length) {
      this.fileTypeOptions = knowledge_file_types.map((item: string) => ({ label: item, value: item }));
    } else {
      this.fileTypeOptions = SUPPORTED_FORMATS.map(item => ({ label: item, value: item }));
    }
  }

  private setupDataPolling() {
    this.loadTrigger$
      .pipe(
        takeUntil(this.destroy$),
        switchMap(() => this.fetchAndPollFiles())
      )
      .subscribe(res => {
        this.tableData = res.data;
        this.total = res.total;
        this.loading = false;
        this.refreshCheckedStatus();
        this.cdr.detectChanges();
      });
  }

  private fetchAndPollFiles() {
    this.loading = true;
    return this.getFiles().pipe(
      expand((val: any) => {
        const onProcessingFiles = val.file_info_list.some((file: any) => ['PENDING', 'RUNNING'].includes(file.file_status.toUpperCase()));
        if (onProcessingFiles) {
          return timer(15_000).pipe(switchMap(() => this.getFiles()));
        }
        return of(null);
      }),
      takeWhile(val => val !== null),
      map((val: any) => {
        val?.file_info_list?.forEach((item: any) => {
          item.create_time = this.formateTimePipe.transform(item.create_time);
        });
        return {
          data: val?.file_info_list ?? [],
          total: val?.count ?? 0,
        };
      }),
      catchError(() => of({ data: [], total: 0 }))
    );
  }

  public getFiles() {
    const query: IKbQueryBase = {
      knowledge_repo_id: this.kbId,
      offset: (this.pageIndex - 1) * this.pageSize,
      limit: this.pageSize,
    };
    if (this.searchName) query.name = this.searchName;
    if (this.searchFileType) query.type = this.searchFileType;
    if (this.searchStatus) query.status = this.searchStatus;

    return from(this.kbRepoServ.listFiles(query));
  }

  public onQueryParamsChange(params: NzTableQueryParams) {
    this.pageIndex = params.pageIndex;
    this.pageSize = params.pageSize;
    this.loadTrigger$.next();
  }

  public onSearch() {
    this.pageIndex = 1;
    this.loadTrigger$.next();
  }

  public operationDisableFn(): boolean {
    return this.setOfCheckedId.size === 0 || this.kbAbilitiesService.isResourceDisabled;
  }

  public openUploadFileHalfmodal() {
    const { ocr_enable, knowledge_file_types } = this.configServ.getConfigs();
    let accept = ocr_enable ? this.ocrAccept : this.acceptWithNoOcr;
    if (knowledge_file_types?.length) {
      accept = `.${knowledge_file_types.join(', .')}`;
    }
    if (this.isRagFlow) {
      accept = this.ragAccept;
      if (this.chunkMethod) accept = this.regFileType.get(this.chunkMethod) || accept;
    }

    const drawerRef = this.nzDrawerService.create({
      nzContent: FileUploadComponent,
      nzWidth: '700px',
      nzMaskClosable: true,
      nzContentParams: {
        kbId: this.kbId,
        isSupTag: this.kbAbilitiesService.isSupTag(this.kb),
        accept,
        description: [{ type: 'text', content: this.i18n.transform('knowledge_upload_tip', { accept }) }],
      },
    });

    drawerRef.afterOpen.subscribe(() => {
      const drawContentComponent = drawerRef?.getContentComponent();
      drawContentComponent?.cancelForm?.subscribe(() => {
        drawerRef.close();
      });

      drawContentComponent?.submitForm?.subscribe(async ({ fileList, setConfirmLoading }: any) => {
        try {
          setConfirmLoading(true);
          const promises = fileList.map(async (file: any) => {
            try {
              const formData = new FormData();
              formData.append('file', file?.file);
              return await this.kbRepoServ.uploadFile(this.kbId, formData, { tags: file.tagSelected ?? [] });
            } catch (error: any) {
              if (error?.data?.error_code) {
                this.nzMessage.error(this.i18n.transform('file_upload_error', { fileName: file.name, errorMsg: error.data.error_msg }), { nzDuration: 3000 });
              }
              return null;
            }
          });
          const results = await Promise.all(promises);
          if (!results.includes(null)) {
            this.nzMessage.success(this.i18n.transform('upload_success'));
          }
          if (results.some(r => r !== null)) {
            this.loadTrigger$.next();
            this.refreshDetail.emit();
          }
          drawerRef.close();
        } finally {
          setConfirmLoading(false);
        }
      });
      drawContentComponent?.submitForm?.subscribe(() => {
        drawerRef.close();
        this.goToTagManage.emit();
      });
    });
  }

  public onDownload(data: any) {
    if (this.kbAbilitiesService.isResourceDisabled) return;
    const url = `${this.kbRepoServ.prefix}/knowledges/${this.kbId}/files/${data.file_id}/content?workspace_id=${this.http.getWorkspaceId()}`;
    this.httpClient.get(url, { responseType: 'blob' }).subscribe({
      next: (blob: Blob) => {
        CommonUtils.downloadFile(blob, data.file_name, true);
      },
      error: (err) => {
        this.nzMessage.error(this.i18n.transform('download_error'));
      }
    });
  }

  public onBatchDownload() {
    if (this.isDownloading) {
      this.nzMessage.info(this.i18n.transform('file_downloading'));
      return;
    }
    const selectedRows = this.tableData.filter(d => this.setOfCheckedId.has(d.file_id));
    this.isDownloading = true;
    let successCount = 0;
    let failureCount = 0;

    from(selectedRows)
      .pipe(
        mergeMap(
          ({ file_id, file_name }) => {
            const url = `${this.kbRepoServ.prefix}/knowledges/${this.kbId}/files/${file_id}/content?workspace_id=${this.http.getWorkspaceId()}`;
            return this.httpClient.get(url, { responseType: 'blob' }).pipe(
              tap((blob: Blob) => {
                CommonUtils.downloadFile(blob, file_name, true);
                successCount++;
              }),
              catchError(() => {
                failureCount++;
                return of(null);
              })
            );
          },
          6
        ),
        toArray(),
        finalize(() => {
          this.isDownloading = false;
          this.cdr.detectChanges();
        })
      )
      .subscribe({
        next: () => {
          this.nzMessage.success(this.i18n.transform('download_success', { successCount, failureCount }));
          this.setOfCheckedId.clear();
          this.loadTrigger$.next();
        },
        error: () => this.nzMessage.error(this.i18n.transform('download_error')),
      });
  }

  public onBatchDelete() {
    const selectedRows = this.tableData.filter(d => this.setOfCheckedId.has(d.file_id));
    this.batchDeleteModal.openModal(
      [
        { headerName: this.i18n.transform('knowledge_file'), field: 'file_name' },
        { headerName: this.i18n.transform('status'), field: '_statusText' },
      ],
      selectedRows.map(row => ({ ...row, _statusText: this.getStatusText(row.file_status) }))
    );
  }

  public async handleBatchDelete(ctx: any) {
    try {
      const selectedRows = ctx.tableData || [];
      const res = await this.kbRepoServ.batchDeleteFile(this.kbId, {
        file_ids: selectedRows.map((r: any) => r.file_id),
      });
      const { total_count, deleted_count } = res as any;
      this.nzMessage.success(this.i18n.transform('batch_delete_success', { totalCount: total_count, deletedCount: deleted_count }));
      this.setOfCheckedId.clear();
      this.loadTrigger$.next();
      this.batchDeleteModal.closeModal();
    } finally {
      ctx.confirmLoading = false;
    }
  }

  public onDelete(data: any) {
    if (this.kbAbilitiesService.isResourceDisabled) return;

    this.nzModal.confirm({
      nzTitle: this.i18n.transform('knowledge_file_delete_warning_title'),
      nzContent: this.i18n.transform('knowledge_file_delete_warning_content', { fileName: data.file_name }),
      nzOkType: 'primary',
      nzOkDanger: true,
      nzOkText: this.i18n.transform('delete'),
      nzOnOk: async () => {
        try {
          await this.kbRepoServ.deleteFile(this.kbId, data.file_id);
          this.nzMessage.success(this.i18n.transform('delete_success'));
          this.loadTrigger$.next();
          this.refreshDetail.emit();
          return true;
        } catch (error) {
          return false;
        }
      },
    });
  }

  public onBatchRetry() {
    const fileIds = this.tableData.filter(d => this.setOfCheckedId.has(d.file_id)).map(d => d.file_id);
    this.showRetryModal(fileIds);
  }

  public showRetryModal(fileIds: string[]): void {
    this.nzModal.confirm({
      nzTitle: this.i18n.transform('retry_prompt_title'),
      nzContent: this.i18n.transform('retry_prompt_content'),
      nzOkText: this.i18n.transform('retry'),
      nzOnOk: async () => {
        try {
          await this.kbRepoServ.generateTasks(this.kbId, {
            task_type: TaskType.RETRY_FILES,
            file_ids: fileIds,
          });
          this.nzMessage.success(this.i18n.transform('retry_success'));
          this.setOfCheckedId.clear();
          this.loadTrigger$.next();
          return true;
        } catch (e) {
          return false;
        }
      },
    });
  }

  public editTag(files: IFile[], isMulti: boolean) {
    this.kbFileTagEdit.showModal(files, isMulti);
  }

  public tagEditSuccess() {
    this.loadTrigger$.next();
  }

  onAllChecked(checked: boolean): void {
    this.tableData.forEach(({ file_id }) => this.updateCheckedSet(file_id, checked));
    this.refreshCheckedStatus();
  }

  onItemChecked(id: string, checked: boolean): void {
    this.updateCheckedSet(id, checked);
    this.refreshCheckedStatus();
  }

  private updateCheckedSet(id: string, checked: boolean): void {
    if (checked) {
      this.setOfCheckedId.add(id);
    } else {
      this.setOfCheckedId.delete(id);
    }
  }

  private refreshCheckedStatus(): void {
    this.allChecked = this.tableData.length > 0 && this.tableData.every(({ file_id }) => this.setOfCheckedId.has(file_id));
    this.indeterminate = this.tableData.some(({ file_id }) => this.setOfCheckedId.has(file_id)) && !this.allChecked;
  }

  public getStatusText(status: string): string {
    const map: Record<string, string> = {
      'SUCCESS': this.i18n.transform('success'),
      'ERROR': this.i18n.transform('error'),
      'POST_PROCESSING': this.i18n.transform('enhance'),
      'CREATED': this.i18n.transform('waiting_queue'),
      'PENDING': this.i18n.transform('pending'),
      'RUNNING': this.i18n.transform('running'),
      'INBOUND': this.i18n.transform('inventory_in_progress'),
    };
    return map[status?.toUpperCase()] || status;
  }

  public getStatusIcon(status: string): any {
    const map: Record<string, string> = {
      'SUCCESS': 'success',
      'ERROR': 'error',
      'POST_PROCESSING': 'processing',
      'CREATED': 'default',
      'PENDING': 'default',
      'RUNNING': 'processing',
      'INBOUND': 'processing',
    };
    return map[status?.toUpperCase()] || 'default';
  }
}
