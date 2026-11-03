import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, catchError, from, Observable } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';

export interface UserPermissions {
  roles: string[];
  permissions: string[]; // 后端接口标识列表(所有角色 permissions 并集)
  creatorCheckPermissions?: string[]; // 需创建人校验的操作列表(METHOD#URI)，DEVELOPER/OPERATOR 仅创建者本人可操作
  currentUserId?: string; // 当前用户 userId(对比工作流/智能体 creatorId)
  currentUserName?: string; // 当前用户 userName(对比模型供应商/服务 createdByUser)
  tenantId?: string;
  // 向后兼容：保留角色名作为 key(如 .OPERATOR)，供既有组件直接判断角色。
  // key 为角色名(OPERATOR/DEVELOPER/OWNER/ADMIN)，value 为该角色的 permissions 数组。
  [role: string]: string[] | string | undefined;
}

@Injectable({
  providedIn: 'root',
})
export class PermissionService {
  private permissionsSubject = new BehaviorSubject<UserPermissions>({
    roles: [],
    permissions: [],
  });
  public permissions$ = this.permissionsSubject.asObservable();

  // 后端 /permissions 返回中的特殊 key(非角色名)，单独解析不混入 permissions
  private static readonly CREATOR_CHECK_KEY = 'creatorCheckPermissions';
  private static readonly CURRENT_USER_ID_KEY = 'currentUserId';
  private static readonly CURRENT_USER_NAME_KEY = 'currentUserName';

  constructor(private appService: AppAgentRepoService) {}

  // 获取用户权限信息
  fetchPermissions(): Observable<UserPermissions> {
    return from(
      this.appService.acquirePermission().then(permissions => {
        // 后端返回 {role: [...], creatorCheckPermissions: [...], currentUserId: [...], currentUserName: [...]}
        const raw = permissions || {};
        const specialKeys = new Set([
          PermissionService.CREATOR_CHECK_KEY,
          PermissionService.CURRENT_USER_ID_KEY,
          PermissionService.CURRENT_USER_NAME_KEY,
        ]);
        const creatorCheck = Array.isArray(raw[PermissionService.CREATOR_CHECK_KEY])
          ? raw[PermissionService.CREATOR_CHECK_KEY]
          : [];
        const currentUserId = Array.isArray(raw[PermissionService.CURRENT_USER_ID_KEY])
          ? raw[PermissionService.CURRENT_USER_ID_KEY][0]
          : undefined;
        const currentUserName = Array.isArray(raw[PermissionService.CURRENT_USER_NAME_KEY])
          ? raw[PermissionService.CURRENT_USER_NAME_KEY][0]
          : undefined;
        // permissions 为非特殊 key 的其余数组并集，roles 为这些 key(角色名)
        const perms: string[] = [];
        const roles: string[] = [];
        const roleMap: Record<string, string[]> = {};
        Object.keys(raw).forEach(key => {
          if (specialKeys.has(key)) {
            return;
          }
          roles.push(key);
          if (Array.isArray(raw[key])) {
            perms.push(...raw[key]);
            roleMap[key] = raw[key];
          }
        });
        const normalized: UserPermissions = {
          roles,
          permissions: perms,
          creatorCheckPermissions: creatorCheck,
          currentUserId,
          currentUserName,
          // 向后兼容：保留角色名作 key(如 .OPERATOR)，供既有组件直接判断角色
          ...roleMap,
        };
        return normalized;
      })
    ).pipe(
      tap(permissions => {
        this.permissionsSubject.next(permissions);
        localStorage.setItem('userPermissions', JSON.stringify(permissions));
      })
    );
  }
  // 获取当前权限（同步方法）
  getCurrentPermissions(): any {
    return this.permissionsSubject.value;
  }

  hasPermission(permission: string): boolean {
    const currentPermissions = this.permissionsSubject.value;

    // 检查currentPermissions是否存在
    if (!currentPermissions) return false;

    // 只遍历 permissions 字段(已授权权限)。不遍历 roles/creatorCheckPermissions/currentUserId 等
    // (creatorCheckPermissions 语义是"需创建人校验"而非全权，误纳入会导致已移入该列表的
    // 编辑/删除 URI 被 hasPermission 判为已授权，破坏既有 *appHasPermission 语义)
    return Array.isArray(currentPermissions.permissions)
      && currentPermissions.permissions.includes(permission);
  }


  // 检查是否具有特定角色
  hasRole(role: string): boolean {
    const currentPermissions = this.permissionsSubject.value;
    return currentPermissions.roles.includes(role);
  }

  // 检查是否具有任意指定权限
  hasAnyPermission(permissions: string[]): boolean {
    return permissions.some((permission) => this.hasPermission(permission));
  }

  // 检查是否具有任意指定角色
  hasAnyRole(roles: string[]): boolean {
    return roles.some((role) => this.hasRole(role));
  }

  // 获取需创建人校验的操作列表(METHOD#URI)
  getCreatorCheckPermissions(): string[] {
    return this.permissionsSubject.value?.creatorCheckPermissions ?? [];
  }

  // 判断指定操作是否需要创建人校验(当前角色该操作在 creatorCheckPermissions 中)
  isCreatorCheckRequired(method: string, uri: string): boolean {
    const list = this.getCreatorCheckPermissions();
    return list.some(action => {
      const idx = action.indexOf('#');
      if (idx < 0) return false;
      const actMethod = action.substring(0, idx);
      const actUri = action.substring(idx + 1);
      return actMethod === method && this.matchUri(actUri, uri);
    });
  }

  // AntPath 风格的 URI 模板匹配(支持 {var})
  // 先转义特殊字符，再把 {var} 占位替换为 [^/]+，避免转义破坏通配符
  private matchUri(pattern: string, uri: string): boolean {
    const escaped = pattern.replace(/[.*+?^$|[\]\\()]/g, '\\$&');
    const regexStr = escaped.replace(/\{[^}]+\}/g, '[^/]+');
    return new RegExp('^' + regexStr + '$').test(uri);
  }

  // 判断当前用户能否修改/删除指定资源(供前端按钮 *ngIf 调用)
  // - 操作在 creatorCheckPermissions: 仅创建者本人可操作(creator===当前用户)
  // - 操作不在 creatorCheckPermissions: 需查 permissions 是否全权授权(与后端 validator 一致),
  //   既不在 permissions 也不在 creatorCheckPermissions 则无权限(false),避免按钮显示但后端 403
  // - isSystemResource=true(平台/系统资源): creator 为空放行(与后端系统资源放行一致)
  // - isSystemResource=false(用户资源): creator 为空 fail-closed(与后端用户资源 fail-closed 一致)
  // creatorIsUserId: true 对比 currentUserId(工作流/智能体 creatorId)；false 对比 currentUserName(模型 createdByUser)
  canModify(method: string, uri: string, creator: string | undefined | null,
    creatorIsUserId: boolean, isSystemResource = false): boolean {
    if (!this.isCreatorCheckRequired(method, uri)) {
      // 不在 creatorCheckPermissions,查 permissions 是否全权授权(与后端 validator 一致)
      return this.isPermissionGranted(method, uri);
    }
    // 系统/平台资源(无创建人)放行,与后端 isSystemResource 放行一致
    if (isSystemResource) {
      return true;
    }
    // 用户资源:creator 为空 fail-closed,与后端用户资源 creator 为空 fail-closed 一致
    if (!creator) {
      return false;
    }
    const currentIdentifier = creatorIsUserId
      ? this.permissionsSubject.value?.currentUserId
      : this.permissionsSubject.value?.currentUserName;
    return !!currentIdentifier && creator === currentIdentifier;
  }

  // 判断当前角色是否全权授权指定操作(METHOD#URI 在 permissions 列表)
  // 与后端 PermissionService.isPermissionGranted 对齐
  isPermissionGranted(method: string, uri: string): boolean {
    const list = this.permissionsSubject.value?.permissions ?? [];
    return list.some(action => {
      const idx = action.indexOf('#');
      if (idx < 0) return false;
      const actMethod = action.substring(0, idx);
      const actUri = action.substring(idx + 1);
      return actMethod === method && this.matchUri(actUri, uri);
    });
  }

  // ============ 语义化方法:按资源类型 + 操作判断创建人权限，调用方不写 URI ============
  // 资源操作 -> [method, uriTemplate] 映射(与后端 role_permissions_interceptor.json 的 creatorCheckPermissions 对应)
  // creatorId 对比 userId 的资源(智能体/工作流)用 true，createdByUser 对比 userName 的资源(模型供应商/服务)用 false
  private static readonly AGENT_ACTIONS: Record<string, [string, string]> = {
    delete: ['DELETE', '/v1/{project_id}/agent-manager/agents/{agent_id}'],
    edit: ['PUT', '/v1/{project_id}/agent-manager/agents/{agent_id}'],
    channel: ['POST', '/v1/{project_id}/agent-manager/agents/{agent_id}/channels'],
  };
  private static readonly WORKFLOW_ACTIONS: Record<string, [string, string]> = {
    delete: ['DELETE', '/v1/{project_id}/agent-manager/workflows/{workflow_id}'],
    edit: ['PUT', '/v1/{project_id}/agent-manager/workflows/{workflow_id}'],
    channel: ['POST', '/v1/{project_id}/agent-manager/workflows/{workflow_id}/channels'],
  };
  private static readonly PROVIDER_ACTIONS: Record<string, [string, string]> = {
    delete: ['DELETE', '/v1/{project_id}/model-manager/integration/providers/{id}'],
    edit: ['PUT', '/v1/{project_id}/model-manager/integration/providers/{id}'],
    // 鉴权按钮(列表页)触发 provider/auths 新增/删除，映射 provider/auths(POST)；
    // auth-info(PUT)是 updateModelServiceProviderAuthInfo，仅后端用，前端不直接判断
    auth: ['POST', '/v1/{project_id}/model-manager/provider/auths'],
  };
  private static readonly MODEL_SERVICE_ACTIONS: Record<string, [string, string]> = {
    delete: ['DELETE', '/v1/{project_id}/model-manager/model-services/{id}'],
    edit: ['PUT', '/v1/{project_id}/model-manager/model-services/{id}'],
    online: ['POST', '/v1/{project_id}/model-manager/model-services/{id}/online'],
    offline: ['POST', '/v1/{project_id}/model-manager/model-services/{id}/offline'],
  };

  // 智能体创建人权限(creatorId=userId)。action: delete/edit/channel
  // isSystemResource: 系统预置智能体(无创建人)传 true 放行,用户智能体传 false(creator 为空 fail-closed)
  canModifyAgent(creator: string | undefined | null, action: string, isSystemResource = false): boolean {
    return this.canModifyByAction(PermissionService.AGENT_ACTIONS, action, creator, true, isSystemResource);
  }
  // 工作流创建人权限(creatorId=userId)。action: delete/edit/channel
  canModifyWorkflow(creator: string | undefined | null, action: string, isSystemResource = false): boolean {
    return this.canModifyByAction(PermissionService.WORKFLOW_ACTIONS, action, creator, true, isSystemResource);
  }
  // 模型供应商创建人权限(createdByUser=userName)。action: delete/edit/auth
  canModifyProvider(creator: string | undefined | null, action: string, isSystemResource = false): boolean {
    return this.canModifyByAction(PermissionService.PROVIDER_ACTIONS, action, creator, false, isSystemResource);
  }
  // 模型服务创建人权限(createdByUser=userName)。action: delete/edit/online/offline
  canModifyModelService(creator: string | undefined | null, action: string, isSystemResource = false): boolean {
    return this.canModifyByAction(PermissionService.MODEL_SERVICE_ACTIONS, action, creator, false, isSystemResource);
  }

  private canModifyByAction(actionMap: Record<string, [string, string]>, action: string,
    creator: string | undefined | null, creatorIsUserId: boolean, isSystemResource: boolean): boolean {
    const entry = actionMap[action];
    if (!entry) {
      // 未知 action fail-closed(隐藏按钮)，与后端 validateByAction 抛异常口径一致；后端兜底
      console.warn('[permission] unknown action, fail-closed:', action);
      return false;
    }
    return this.canModify(entry[0], entry[1], creator, creatorIsUserId, isSystemResource);
  }

  // 清除权限信息（用于退出登录）
  clearPermissions(): void {
    this.permissionsSubject.next({ roles: [], permissions: [] });
    localStorage.removeItem('userPermissions');
  }

  // 初始化权限（应用启动时调用）
  initializePermissions(): void {
    const stored = localStorage.getItem('userPermissions');
    if (stored) {
      this.permissionsSubject.next(JSON.parse(stored));
    }
  }
}
