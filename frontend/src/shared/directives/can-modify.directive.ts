import { Directive, Input, TemplateRef, ViewContainerRef, OnDestroy } from '@angular/core';
import { Subscription } from 'rxjs';
import { PermissionService } from '@services/permission.service';

/**
 * 创建人权限控制指令(结构型)。风格对齐既有 `*appHasPermission`:
 * 模板里声明，指令订阅 permissions$ 自动显隐，OnDestroy 取消订阅，组件 ts 不写业务方法。
 *
 * 用法:
 *   <!-- 资源类型 + action + creator。creator 为 userId(智能体/工作流) 或 userName(模型供应商/服务) -->
 *   <button *appCanModify="['provider', 'edit', dataItem.created_by_user]">编辑</button>
 *   <button *appCanModify="['agent', 'delete', data.creator_id ?? data.creatorId]">删除</button>
 *
 * 资源类型 + creator 标识形态对应:
 *   agent / workflow      → creator 为 userId
 *   provider / modelService → creator 为 userName
 *
 * 内部调用 PermissionService.canModifyAgent/Workflow/Provider/ModelService,
 * URI 模板集中在 PermissionService，本指令与组件都不写 URI。
 */
@Directive({
  standalone: true,
  selector: '[appCanModify]',
})
export class CanModifyDirective implements OnDestroy {
  private args: [string, string, string | undefined | null] = ['', '', undefined];
  private permissionSubscription?: Subscription;
  private hasView = false;

  constructor(
    private templateRef: TemplateRef<any>,
    private viewContainer: ViewContainerRef,
    private permissionService: PermissionService,
  ) {}

  @Input() set appCanModify(args: [string, string, string | undefined | null]) {
    this.args = args || ['', '', undefined];
    this.updateView();
    if (this.permissionSubscription) {
      this.permissionSubscription.unsubscribe();
    }
    this.permissionSubscription = this.permissionService.permissions$.subscribe(() => {
      this.updateView();
    });
  }

  private updateView(): void {
    const canModify = this.canModify();
    if (canModify && !this.hasView) {
      this.viewContainer.createEmbeddedView(this.templateRef);
      this.hasView = true;
    } else if (!canModify && this.hasView) {
      this.viewContainer.clear();
      this.hasView = false;
    }
  }

  private canModify(): boolean {
    const [resourceType, action, creator] = this.args;
    switch (resourceType) {
      case 'agent':
        return this.permissionService.canModifyAgent(creator, action);
      case 'workflow':
        return this.permissionService.canModifyWorkflow(creator, action);
      case 'provider':
        return this.permissionService.canModifyProvider(creator, action);
      case 'modelService':
        return this.permissionService.canModifyModelService(creator, action);
      default:
        return false; // 未知资源类型 fail-closed
    }
  }

  ngOnDestroy(): void {
    if (this.permissionSubscription) {
      this.permissionSubscription.unsubscribe();
    }
  }
}
