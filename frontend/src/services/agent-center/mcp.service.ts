import { Injectable } from '@angular/core';
import { IMappings } from '@routes/agent-center/types/common.types';
import { ContextService } from '@services/context.service';
import { HttpService } from '@services/http.service';

@Injectable({
  providedIn: 'root',
})
export class MCPService {
  get prefix() {
    return `${this.ctxServ.baseUrl}/mcp`;
  }

  constructor(private http: HttpService, private ctxServ: ContextService) {}

  // 查询我的MCP服务
  public getServiceList(query, params): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/service/list`,
      query,
      params,
    });
  }

  // 查询平台预置的MCP服务用于创建用户自己的MCP服务
  public getServerList(query: any): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/server/list`,
      query
    })
  }

  public getRecommendList() {
    return this.http.getAsync({
      url: `${this.prefix}/server/recommendation`,
    })
  }

  public testService(params): Promise<any> {
    return this.http.postAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/mcp-servers/test`,
      params,
    });
  }

  public createService(params: any): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/mcp-servers`,
      params,
    });
  }

  public getToolsList(query: any, params: any): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/mcp-servers/tools/search`,
      query,
      params,
    });
  }

  // 获取MCP工具的Input和Output信息
  public getMcpToolInfo(serviceId: string): Promise<any> {
    return Promise.all([
      this.http.getAsync({ url: `${this.prefix}/service/detail/${serviceId}` }),
      this.http.getAsync({ url: `${this.prefix}/service/tools/info/${serviceId}` }),
    ]).then(([info, rawTools]) => {
      return { ...(info as Object), tools: (rawTools as any)?.tools };
    });
  }

  // 获取工具信息
  public getMcpTools(serviceId: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/service/tools/list/${serviceId}`,
    })
  }

  // MCP评分接口
  public updateMcpRate(params: any): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/server/rating`,
      params: params,
    })
  }

  // 测试MCP工具
  public testMcpTools(params: any): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/service/tools/test`,
      params,
    })
  }

  public updateService(params: any): Promise<any> {
    const { serverId, ...rest } = params;
    return this.http.putAsync({
      url: `${this.prefix}/mcp-servers/${serverId}`,
      params: rest,
    });
  }

  public deployMcpServer(mcpId: string, params:  any): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/deploy/${mcpId}`,
      params: params,
    })
  }

  public modifyMcpService(params:  any): Promise<any> {
    return this.http.putAsync({
      url: `${this.prefix}/service/modify`,
      params: params,
    })
  }

  public getServiceDetail(serviceId: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/service/detail/${serviceId}`,
    })
  }

  public getServerDetail(serverId: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/server/detail/${serverId}`,
    });
  }

  public deleteService(serverId: string): Promise<any> {
    return this.http.deleteAsync({
      url: `${this.prefix}/service/delete/${serverId}`,
    });
  }

  /**
   * 将已部署的 MCP 服务实例上架到资产广场（FRS-091）
   */
  public publishServer(serviceId: string, category?: string, readme?: string): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/server/on-shelf`,
      params: {
        service_id: serviceId,
        ...(category ? { category } : {}),
        ...(readme ? { readme } : {}),
      },
    });
  }

  /**
   * 将 MCP 服务目录条目从资产广场下架（支持传目录条目标识或上架来源实例ID）
   */
  public unpublishServer(serverId: string): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/server/off-shelf/${serverId}`,
    });
  }

  public getReferenceList(serverId: string, query: any): Promise<IMappings> {
    return this.http.getAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/relation/resources/${serverId}`,
      query,
    });
  }

  public provisionService(params: any): Promise<any> {
    const { serverId, ...rest } = params;
    return this.http.postAsync({
      url: `${this.prefix}/mcp-servers/${serverId}/configs`,
      params: rest,
    });
  }

  public updateProvisionData(params: any): Promise<any> {
    const { serverId, ...rest } = params;
    return this.http.putAsync({
      url: `${this.prefix}/mcp-servers/${serverId}/configs`,
      params: rest,
    });
  }

  public deleteProvisionData(serverId: string): Promise<any> {
    return this.http.deleteAsync({
      url: `${this.prefix}/mcp-servers/${serverId}/configs`,
    });
  }

  public runToolTest(params: any): Promise<any> {
    const { serverId, ...rest } = params;
    return this.http.postAsync({
      url: `${this.prefix}/mcp-servers/${serverId}/tools/run`,
      params: rest,
    });
  }

  // 查询我的MCP服务
  public getDataProcessList(query, params): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/dataProcess/list`,
      query,
      params,
    });
  }
  public getAuth(): Promise<any> {
    return this.http.getAsync({
      url: `${this.ctxServ.baseUrl}/queryAuthorization`,
      query:{
        workspace_id: this.ctxServ.workspaceId,
      }
    });
  }
  public doAuth(): Promise<any> {
    return this.http.postAsync({
      url: `${this.ctxServ.baseUrl}/doAuthorization`,
      params: {
        workspace_id: this.ctxServ.workspaceId,
      }
    });
  }
}
