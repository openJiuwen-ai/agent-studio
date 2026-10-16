import { inject, Injectable } from '@angular/core';

import {
  ICreateInstanceParams,
  ICreateInstanceResponse,
  IInstanceDetail,
  IListInstancesResponse,
  IModifyInstanceParams,
} from '@routes/memory-lib/memory-service-instance-interfaces';
import { HttpService } from '@services/http.service';
import { ContextService } from '@services/context.service';

@Injectable({
  providedIn: 'root',
})
export class MemoryServiceInstanceApiService {
  readonly ctxServ = inject(ContextService);
  readonly http = inject(HttpService);

  get prefix() {
    return `${this.ctxServ.baseUrl}/agent-manager`.replaceAll('/v1/', '/v2/');
  }

  listInstances(workspaceId: string, name?: string): Promise<IListInstancesResponse> {
    return this.http.getAsync({
      url: `${this.prefix}/memory-service-instances`,
      query: { workspace_id: workspaceId, name: name ?? '' },
    });
  }

  createInstance(workspaceId: string, params: ICreateInstanceParams): Promise<ICreateInstanceResponse> {
    return this.http.postAsync({
      url: `${this.prefix}/memory-service-instances`,
      query: { workspace_id: workspaceId },
      params,
    });
  }

  modifyInstance(workspaceId: string, instanceId: string, params: IModifyInstanceParams): Promise<void> {
    return this.http.putAsync({
      url: `${this.prefix}/memory-service-instances/${instanceId}`,
      query: { workspace_id: workspaceId },
      params,
    });
  }

  deleteInstance(workspaceId: string, instanceId: string): Promise<void> {
    return this.http.deleteAsync({
      url: `${this.prefix}/memory-service-instances/${instanceId}`,
      query: { workspace_id: workspaceId },
    });
  }

  showInstance(workspaceId: string, instanceId: string): Promise<IInstanceDetail> {
    return this.http.getAsync({
      url: `${this.prefix}/memory-service-instances/${instanceId}`,
      query: { workspace_id: workspaceId },
    });
  }

  healthCheck(workspaceId: string, instanceId: string): Promise<IInstanceDetail> {
    return this.http.postAsync({
      url: `${this.prefix}/memory-service-instances/${instanceId}/health`,
      query: { workspace_id: workspaceId },
    });
  }
}
