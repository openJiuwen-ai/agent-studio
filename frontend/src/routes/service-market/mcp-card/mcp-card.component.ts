import {
  Component,
  EventEmitter,
  Input,
  OnInit,
  Output,
  SimpleChanges,
  TemplateRef,
} from '@angular/core';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { MODULES } from '@shared/modules';
import { MCP_DEFAULT_ICON_BASE64_STR } from '@shared/config/default-icons-base64';
import { cdnAssetUrl } from '../../../single-spa/assets-url';
import { McpInterfaces } from '@interfaces/mcp/mcp.interfaces';
import { Router } from '@angular/router';
import { CommonUtils } from '../../../utils/common.util';
import { Subscription } from 'rxjs';
import { PermissionService } from '@services/permission.service';
import { CommonService } from '@services/common.service';
import {
  AddMcpHalfModalComponent,
} from '@routes/agent-center/app-mcp-service/components/add-mcp-half-modal/add-mcp-half-modal.component';
import { NzDrawerRef, NzDrawerService } from 'ng-zorro-antd/drawer';
import { McpAllService } from '@routes/service-market/mcp-all.service';
import {HttpService} from "@services/http.service";
import { WindowResizeService } from '@shared/base/window-resize.service';
import { AssertSquareTagType } from '@routes/agent-center/app-agent/common-logic-agent';
import { NzModalService } from 'ng-zorro-antd/modal';
import { MCPService } from '@services/agent-center/mcp.service';
import { MessageComponent } from '@shared/services/cfdata.service';
enum mapKeys {
  service_id = 'service_id'
}

@Component({
  selector: 'mcp-card',
  templateUrl: './mcp-card.component.html',
  styleUrls: ['./mcp-card.component.less'],
  standalone: true,
  imports: [MODULES],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.COMMON, I18nNamespace.AGENT],
    },
  ],
})
export class McpCardComponent implements OnInit {
  @Input() mcpData: any;
  @Input() mcpTotal: any;
  @Input() appTabs: AssertSquareTagType[] = [];
  @Input() activeTabIsOfficial = false;
  @Output() onRefresh = new EventEmitter<void>();
  public lang: string = '';
  statusMap = new Map([
    ['success', { label: this.i18n.transform('installed'), color: 'green' }],
    [
      'creatingStack',
      { label: this.i18n.transform('installing'), color: 'orange' },
    ],
    ['stackFail', { label: this.i18n.transform('installFail'), color: 'red' }],
    ['inner', { label: this.i18n.transform('platform'), color: 'blue' }],
    ['user', { label: this.i18n.transform('user'), color: 'purple' }],
  ]);
  public currentPermissions: any;
  private permissionSubscription: Subscription;
  subscribeBtnStatus = this.commonService.getSubscribeStatus();
  public windowWidth: number;
  private resizeSub: Subscription;

  constructor(
    private router: Router,
    private permissionService: PermissionService,
    public commonService: CommonService,
    private nzDrawerService: NzDrawerService,
    private i18n: I18NextEagerPipe,
    private mcpAllService: McpAllService,
    private http: HttpService,
    private windowResizeService: WindowResizeService,
    private nzModal: NzModalService,
    private mcpService: MCPService
  ) {
    this.lang = CommonUtils.getLanguage();
  }

  unpublishMcp($event?: Event): void {
    $event?.stopPropagation();
    this.nzModal.confirm({
      nzTitle: this.i18n.transform('plaza_offshelf_confirm'),
      nzOkText: this.i18n.transform('ok'),
      nzCancelText: this.i18n.transform('cancel'),
      nzOnOk: () => {
        return this.mcpService
          .unpublishServer(this.mcpData.id)
          .then(() => {
            MessageComponent.showSuccess(this.i18n.transform('plaza_offshelf_success'));
            this.onRefresh.emit();
            return null;
          })
          .catch(() => null);
      },
    });
  }

  ngOnChanges(changes: SimpleChanges) {
  }

  ngOnInit(): void {
    this.resizeSub = this.windowResizeService.getWindowWidth().subscribe((width) => {
      this.windowWidth = width;
    });
    this.permissionSubscription = this.permissionService.permissions$.subscribe(
      (permissions) => {
        this.currentPermissions = permissions;
      },
    );
  }

  ngOnDestroy(): void {
    if (this.permissionSubscription) {
      this.permissionSubscription.unsubscribe();
    }
  }

  handleOpenModal(event: MouseEvent, cardData: McpInterfaces) {
    event.stopPropagation();
    if (this.hasPermission()) {
      return;
    }
    const thisNzModal: any = this.nzModal.create({
      nzContent: AddMcpHalfModalComponent,
      nzTitle: this.i18n.transform('install_mcp'),
      nzWidth: '1000px',
    });
    const instance = thisNzModal.getContentComponent();
    instance.type = 'server';
    instance.selectMcpData = cardData;
    instance.title = this.isZH() ? cardData.name : cardData.name_en;
  }

  get halfModalWidth() {
    if (this.windowWidth > 1920) {
      return '800px';
    } else {
      return '600px';
    }
  }

  toDetail(item) {
    if (!this.subscribeBtnStatus) {
      return;
    }
    // 若正在创建中，禁止跳转
    if (item.fc_instance_status === 'creatingStack') {
      return;
    }
    if (!item.is_subscription && ['kooGallery','ROMA'].includes(item?.resource)) {
      return;
    }
    let queryParams:any = {
      id: item.id || item[mapKeys.service_id],
      type: item?.resource ? 'third' : 'server',
      ...(item?.resource && { resource: item.resource }),
      ...(item?.version_id && { version_id: item.version_id }),
    };
    if (['kooGallery','ROMA'].includes(item?.resource)){
      queryParams.org_type = item.org_type;
    }
    this.router.navigate(['/home/agent-center/mcp-service/detail'], {
      queryParams: queryParams,
    });
  }

  public hasPermission(): boolean {
    return (
      this.currentPermissions &&
      this.currentPermissions.OPERATOR
    );
  }

  show(e, content: TemplateRef<any>): void {
    e.stopPropagation();
  }

  isZH(): boolean {
    return this.lang === 'zh-cn';
  }

  public getMcpTagName(resource){
    const resource_list ={
      ROMA:'ROMA',
      custom:this.i18n.transform('custom'),
      kooGallery:this.i18n.transform('cloud_store'),
      inner:this.i18n.transform('platform')
    }
    return resource_list[resource]??this.i18n.transform('custom')
  }

  selectClass(){
    if (!this.subscribeBtnStatus) {
      return 'cursor-not-allowed';
    }
    if (this.mcpData?.resource) {
      if (this.mcpData?.is_subscription){
        return 'cursor-pointer';
      } else {
        return 'cursor-not-allowed';
      }
    } else {
      return 'cursor-pointer';
    }
  }

  getCategoryLabel(tagId: string): string {
    if (!tagId || this.appTabs.length <= 0) {
      return '';
    }
    const filterData = this.appTabs.filter(item => item.id === tagId);
    if (filterData && filterData.length > 0) {
      return this.isZH() ? filterData[0].name : filterData[0].name_en;
    }
    return '';
  }

  protected readonly MCP_DEFAULT_ICON_BASE64_STR = MCP_DEFAULT_ICON_BASE64_STR;
  protected readonly changeUrl = cdnAssetUrl;
}
