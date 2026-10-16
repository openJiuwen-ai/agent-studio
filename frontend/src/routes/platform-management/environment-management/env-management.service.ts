import { Injectable } from '@angular/core';
import { ContextService } from '@services/context.service';
import { HttpService } from '@services/http.service';

@Injectable({
  providedIn: 'root',
})
export class EnvManagementService {
  get prefix() {
    return `${this.ctxServ.baseUrl}/agent-manager/environments`;
  }

  constructor(private http: HttpService, private ctxServ: ContextService) {}

  // 查询环境列表
  public getEnvironmentList(params): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}`,
      query: {
        offset: params.offset,
        limit: params.limit,
        ...(params?.name && { name: params.name }),
        // 按默认环境过滤（服务端单条返回，避免首页分页截断导致默认环境漏判）
        ...(params?.isDefault !== undefined && { is_default: params.isDefault }),
      },
    });
  }

  // 查询环境详情
  public getEnvironmentDetail(environment_id): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/${environment_id}`,
    });
  }

  // 删除环境信息
  public deleteEnvironment(environment_id: string): Promise<any> {
    return this.http.deleteAsync({
      url: `${this.prefix}/${environment_id}`,
    });
  }

  // 创建环境
  public createEnvironment(params): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}`,
      params,
    });
  }

  // 编辑环境
  public editEnvironment(environment_id, params): Promise<any> {
    return this.http.putAsync({
      url: `${this.prefix}/${environment_id}`,
      params,
    });
  }

  // 设置为默认环境
  public setDefaultEnvironment(environment_id): Promise<any> {
    return this.http.putAsync({
      url: `${this.prefix}/${environment_id}/is_default`,
    });
  }

  // 查询环境中关联的实例信息
  public queryAssociatedInstance(environment_id, params): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/${environment_id}/instance`,
      query: {
        pageNo: params.page,
        pageSize: params.pageSize,
      },
    });
  }

  // 查询vpc列表
  public queryVpcs(): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/vpc/vpcs`,
    });
  }

  // 查询vpc子网
  public querySubnets(params): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/vpc/subnets`,
      query: params,
    });
  }

  // 查看权限
  public checkPermission(): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/check-permission`,
    });
  }

  // 查询是否委托
  public getEntrust(key): Promise<any> {
    let noIdPath = this.getBasePath(this.ctxServ.baseUrl);
    return this.http.getAsync({
      url: `${noIdPath}mgmtconsole/webapi/agency/query-agency-roles`,
      query: {
        businessCode: key,
      },
      headers: {
        'Endpoint-Scope': 'global',
      },
    });
  }

  // 授权委托
  public postEntrust(key): Promise<any> {
    let noIdPath = this.getBasePath(this.ctxServ.baseUrl);
    return this.http.postAsync({
      url: `${noIdPath}mgmtconsole/webapi/agency/create-agency`,
      params: {
        business_code: key,
      },
      headers: {
        'Endpoint-Scope': 'global',
      },
    });
  }

  getBasePath(url) {
    // 匹配 /v1/ 及之前的内容
    const match = url.match(/^(.*?\/v\d+\/)/);
    return match ? match[1] : null;
  }

  // 查询agentrun开通状态
  public getAgentRunStatus(): Promise<any> {
    return this.http.getAsync({
      url: `${this.ctxServ.baseUrl}/ops/query/agentrun/openstatus`,
      headers: {
        'Endpoint-Scope': 'global',
      },
    });
  }
}
