import {Component, Input, OnDestroy, OnInit, ViewEncapsulation,} from '@angular/core';
import {CommonModule} from '@angular/common';
import {MODULES} from '@shared/modules';
import {I18NEXT_NAMESPACE, I18NextEagerPipe} from 'angular-i18next';
import {I18nNamespace} from '@i18n';
import {SpaceTeamManagementService} from '@services/space-team-management.service';
import {CommonUtils} from '../../../../utils/common.util';
import {getSessionStorage} from "../../../../utils/utils";
import {NzMessageService} from "ng-zorro-antd/message";
import {NzModalRef} from 'ng-zorro-antd/modal';

@Component({
  selector: 'space-add-user',
  templateUrl: './add-user.component.html',
  styleUrls: ['./add-user.component.less'],
  encapsulation: ViewEncapsulation.None, // 要想设置的样式生效，此处必须配置成 ViewEncapsulation.None
  standalone: true,
  imports: [CommonModule, MODULES],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.PLATFORM_MANAGEMENT, I18nNamespace.COMMON],
    },
  ],
})
export class AddUserComponent implements OnInit, OnDestroy {
  @Input() space_id: '';

  btnLoading = false;
  btn_disabled = false;

  search_value = '';
  checkedArray = [];
  has_add_user = [];
  has_add_user_id = [];
  // 数据列表
  dataArray1: Array<any> = [];
  originDataArray1: Array<any> = [];
  integrationTabsOption: Array<any> = [];
  space_team_users = [];
  roles_all = getSessionStorage('ROLES') ? getSessionStorage('ROLES') : [];
  checkAll = false;

  constructor(
    private i18n: I18NextEagerPipe,
    private spaceTeamManagementService: SpaceTeamManagementService,
    private message: NzMessageService,
    private modalRef: NzModalRef
  ) {}

  async ngOnInit() {
    const lang = CommonUtils.getLanguage();
    // nz-select 的 [nzOptions] 需要 { label, value } 结构，否则下拉选项显示为空白
    this.integrationTabsOption = this.roles_all.map((item) => {
      return {
        label: lang === 'zh-cn' ? item.roleNameCn : CommonUtils.titleCase3(item.roleNameEn),
        value: item.roleId,
        disabled: item.roleId === 'OWNER',
      };
    });
    await this.get_space_members();
    await this.getAllUsersFn();
  }

  ngOnDestroy(): void {}

  close() {
    this.modalRef.destroy();
  }

  dismiss() {
    this.modalRef.destroy();
  }

  addUserFn() {
    if (this.checkedArray.length === 0) {
      this.message.create('error', this.i18n.transform('no_person_selected'));
      return;
    }
    this.btnLoading = true;
    const members = [];
    const members_name = [];
    this.checkedArray.forEach((item) => {
      if (!this.has_add_user_id.includes(item.memberId)) {
        members.push({
          member_id: item.memberId,
          member_name: item.memberName,
          role: item.value,
          member_source: 'IAM',
        });
        members_name.push(item.memberName);
      }
    });
    const params = {
      members,
    };
    this.spaceTeamManagementService
      .addSpaceMembers(params)
      .then((res) => {
        const tip = this.i18n.transform('add_user_success');
        this.message.create('success', `${(members_name.join(','), tip)}`);
        this.close();
      })
      .catch(() => {
        const error_code = getSessionStorage('error_code');
        if (['Openjiuwen.02001064', 'Openjiuwen.02001022'].includes(error_code)) {
          this.close();
        }
        this.close();
      })
      .finally(() => {
        this.btnLoading = false;
      });
  }

  async get_space_members() {
    const params = {
      page_num: 1,
      page_size: 9999,
    };
    await this.spaceTeamManagementService
      .getSpaceMembers(params)
      .then((res: any) => {
        this.space_team_users = res?.workspaceList;
      });
  }

  role_name(id: string): string {
    const role = this.roles_all.filter((item) => item.roleId === id);
    return role.length ? role[0].roleNameCn : '';
  }

  deleteUser(data) {
    this.checkedArray = this.checkedArray.filter(
      (item) => item.memberId !== data.memberId,
    );
    this.syncCheckAll();
  }

  /** 单个成员是否已勾选（按 memberId 比较，避免对象引用差异导致状态不同步） */
  isChecked(item: any): boolean {
    return this.checkedArray.some((c) => c.memberId === item.memberId);
  }

  /** 单个成员勾选变化：同步到 checkedArray，左侧勾选态与右侧“已选”才会响应 */
  onItemChecked(item: any, checked: boolean) {
    if (checked) {
      if (!this.isChecked(item)) {
        this.checkedArray = [...this.checkedArray, item];
      }
    } else {
      this.checkedArray = this.checkedArray.filter(
        (c) => c.memberId !== item.memberId,
      );
    }
    this.syncCheckAll();
  }

  /** 当前列表中可勾选的成员（搜索过滤后即为可见项；已存在成员 disabled，不参与） */
  private get selectableMembers(): Array<any> {
    return this.dataArray1.filter((item) => !item.disabled);
  }

  /** 根据当前列表的勾选情况回填“全部”复选框 */
  syncCheckAll() {
    const selectable = this.selectableMembers;
    this.checkAll =
      selectable.length > 0 && selectable.every((item) => this.isChecked(item));
  }

  async getAllUsersFn() {
   await this.spaceTeamManagementService.getAllUsers().then((res: any) => {
      const list = [];
      res.workspaceList?.forEach((item) => {
        const is_user = this.space_team_users.filter(
          (arr) => item.memberId === arr.memberId,
        );
        if (is_user.length === 1) {
          const nj = {
            memberId: item.memberId,
            memberName: item.memberName,
            value: is_user[0].role,
            disabled: true,
          };
          this.has_add_user.push(nj);
          this.has_add_user_id.push(item.memberId);
          list.push(nj);
        } else {
          list.push({
            memberId: item.memberId,
            memberName: item.memberName,
            value: 'DEVELOPER',
            disabled: false,
          });
        }
      });
      this.dataArray1 = list;
      this.originDataArray1 = list;
      this.checkedArray = this.has_add_user;
      this.syncCheckAll();
    });
  }

  onClear() {
    this.dataArray1 = this.originDataArray1;
    this.syncCheckAll();
  }

  onSearch(value: string) {
    if (!value) {
      this.dataArray1 = this.originDataArray1;
    } else {
      // 始终基于完整列表过滤，避免在已过滤结果上二次过滤导致结果丢失
      this.dataArray1 = this.originDataArray1.filter(
        (item) => item.memberName.indexOf(value) > -1,
      );
    }
    // 可见列表变化后同步“全部”复选框状态
    this.syncCheckAll();
  }

  onNgcheckAll(info) {
    const selectable = this.selectableMembers;
    if (info) {
      // 全选：仅补齐当前列表中尚未勾选的成员，保留其余已勾选项
      // （含搜索前已勾选、当前被过滤隐藏的成员，避免整体重建导致勾选丢失）
      const checkedIds = this.checkedArray.map((c) => c.memberId);
      const toAdd = selectable.filter(
        (item) => !checkedIds.includes(item.memberId),
      );
      this.checkedArray = [...this.checkedArray, ...toAdd];
    } else {
      // 取消全选：仅移除当前列表中的成员，保留其余已勾选项
      const selectableIds = selectable.map((item) => item.memberId);
      this.checkedArray = this.checkedArray.filter(
        (c) => !selectableIds.includes(c.memberId),
      );
    }
    this.syncCheckAll();
  }
}
