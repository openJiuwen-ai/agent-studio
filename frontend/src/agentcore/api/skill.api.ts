import { Injectable } from '@angular/core';

import { catchError, map, Observable, of } from 'rxjs';

import { ServiceId } from '@agentcore/constants/request';
import { SkillDetailRes, SkillListRes, SkillVersionDetail, SkillVersionListRes } from '@agentcore/constants/skill.model';
import { customPropTransfer } from '@agentcore/shared/decorators/prop';
import { MessageConfig } from '@agentcore/types/request';

import { JiuwenBaseApi } from './jiuwen-base.api';

@Injectable({
  providedIn: 'root',
})
export class SkillApi extends JiuwenBaseApi {
  override serviceId = (window as any).iamTargetId || ServiceId.JIUWEN;
  prefix = '/v1/{projectId}/agent-manager/skills';

  importSkill(params: FormData): Observable<any> {
    return this.request.post({
      url: `${this.prefix}/import`,
      query: {
        workspace_id: this.request.getWorkspaceId(),
      },
      body: params,
    } as any);
  }

  deleteSkill(skillId: string) {
    return this.request.delete({
      url: `${this.prefix}/${skillId}`,
      query: {
        workspace_id: this.request.getWorkspaceId(),
      },
    } as any);
  }

  exportSkillVersion(skillId: string) {
    return this.request.post({
      url: `${this.prefix}/${skillId}/export`,
      query: {
        workspace_id: this.request.getWorkspaceId(),
      },
    } as any);
  }

  querySkillList(params = {}): Observable<any> {
    return this.request.get({
      url: `${this.prefix}`,
      params,
    } as any);
  }

  querySkillVersionList(skillId: string, offset: number, limit: number) {
    return this.request
      .get({
        url: `${this.prefix}/${skillId}/versions`,
        query: {
          offset,
          limit,
        },
      } as any)
      .pipe(
        catchError(() => of({})),
        map(res => customPropTransfer(res, SkillVersionListRes))
      );
  }

  querySkillDetail(skillId: string, messageConfig?: MessageConfig) {
    return this.request
      .get(
        {
          url: `${this.prefix}/${skillId}`,
        } as any,
        messageConfig
      )
      .pipe(map(res => customPropTransfer(res, SkillDetailRes).skillInfo));
  }

  /**
   * 流式下载 Skill 制品包内容（zip 字节流）。
   *
   * <p>请求同源后端接口，由后端代理读取 OBS 中的 zip 并流式返回，
   * 避免前端跨域直接请求 OBS 签名 URL（CORS 问题）。
   * 走 RequestService 框架以自动替换 {projectId}/{workspaceId} 占位符。</p>
   */
  getSkillPackageContent(skillId: string): Observable<ArrayBuffer> {
    return this.request.get({
      url: `${this.prefix}/${skillId}/package-content`,
      query: {
        workspace_id: this.request.getWorkspaceId(),
      },
      dataType: 'arraybuffer',
    } as any);
  }

  queryReference(skillId: string, offset = 0, limit = 100, messageConfig?: MessageConfig) {
    return this.request
      .get({
        url: this.isHc() ? `/v1/studio/resources/${skillId}/referenced-by` : `/v1/{projectId}/agent-manager/relation/resources/${skillId}`,
        params: {
          offset,
          limit,
          resource_type: 'skill',
        },
        messageConfig,
      } as any)
      .pipe(catchError(() => of({ relations: [] })));
  }

  queryResourceSkill({ offset, limit, tagId, name, description }: { offset: number; limit: number; tagId?: string; name?: string; description?: string }) {
    return this.request
      .get({
        url: this.prefix,
        params: {
          offset,
          limit,
          tag_id: tagId,
          name: name || undefined,
          description,
          published_asset: 1,
        },
      } as any)
      .pipe(map(res => customPropTransfer(res, SkillListRes)));
  }

  // 获取自动推荐的skill
  getSkillResource(params: any, agent_id: string) {
    return this.request.post({
      url: this.isHc() ? `/v1/studio/agents/${agent_id}/resources` : `/v1/{projectId}/agent-manager/agents/${agent_id}/resources?workspace_id={workspaceId}`,
      params,
    } as any);
  }
}
