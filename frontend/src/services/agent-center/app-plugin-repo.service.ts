import { Injectable } from '@angular/core';
import {
  IPlugin,
  PluginListReq,
  PluginListResponse,
  IDebugPluginResponse, ListIPluginWithToolsResponse, IPluginWithTools
} from '@routes/agent-center/app-plugin/app-plugin.interface';
import { ContextService } from '@services/context.service';
import { HttpService } from '@services/http.service';
import { MessageComponent } from '@shared/services/cfdata.service';
import { IResponse } from '@routes/agent-center/interfaces/plugin/app-plugin.interface';

@Injectable({
  providedIn: 'root',
})
export class AppPluginRepoService {
  get prefix() {
    return `${this.ctxServ.baseUrl}/agent-manager/plugins`;
  }
  get baseUrlV2() {
    return this.ctxServ.baseUrl.replace('/v1/','/v2/');
  }

  constructor(private http: HttpService, private ctxServ: ContextService) {}

  /** 获取插件列表 */
  public getPluginList(
    params: PluginListReq,
    signal?: AbortSignal,
  ): Promise<ListIPluginWithToolsResponse> {
    const {
      offset,
      limit,
      id,
      name,
      type,
      tool_desc,
      tool_chinese_name,
      ids,
      intf_type,
      customize_node,
      published,
      call_mode,
      entry_point,
      label,
      category,
    } = params;

    return this.http.getAsync({
      url: `${this.prefix}`,
      query: {
        ...(offset !== undefined && { offset }),
        ...(limit !== undefined && { limit }),
        ...(id !== undefined && { id }),
        ...(name !== undefined && { en_name: name }),
        ...(type !== undefined && { type }),
        ...(tool_desc !== undefined && { desc: tool_desc }),
        ...(tool_chinese_name !== undefined && { cn_name: tool_chinese_name }),
        ...(ids !== undefined && { ids }),
        ...(intf_type !== undefined && { intf_type }),
        ...(customize_node !== undefined && { customize_node }),
        ...(published !== undefined && { published }),
        ...(call_mode !== undefined && { call_mode }),
        ...(entry_point !== undefined && { entry_point }),
        ...(label !== undefined && { label }),
        ...(category !== undefined && { category }),
      },
      signal,
    });
  }
  public deleteTool(pluginId: string ,toolId: string): Promise<any> {
    return this.http.deleteAsync({
      url: `${this.baseUrlV2}/agent-manager/tools/${toolId}`,
      query:{
        plugin_id:pluginId
      }
    });
  }
  public deletePlugin(pluginId: string ): Promise<any> {
    return this.http.deleteAsync({
      url: `${this.prefix}/${pluginId}`,
    });
  }

  /**
   * 将插件上架到资产广场（FRS-091，锚定发布版本，version_id 可选）
   */
  public publishPlugin(pluginId: string, versionId?: string, category?: string): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/${pluginId}/on-shelf`,
      params: {
        ...(versionId ? { version_id: versionId } : {}),
        ...(category ? { category } : {}),
      },
    });
  }

  /**
   * 将插件从资产广场下架（FRS-091）
   */
  public unpublishPlugin(pluginId: string): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/${pluginId}/off-shelf`,
    });
  }

  public getPluginById(id: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/${id}`,
    });
  }

  public getToolsByPluginId(id: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/tools/${id}`,
    });
  }
  public registerTool(params): Promise<IPlugin> {
    return this.http.postAsync({
      url: `${this.baseUrlV2}/agent-manager/tools`,
      params,
    });
  }
  public registerToolBatch(params): Promise<IPlugin> {
    return this.http.postAsync({
      url: `${this.baseUrlV2}/agent-manager/batchtools`,
      params:{
        tools:params
      },
    });
  }


  public registerFunctionTool(plugin_id, params): Promise<any> {
    return this.http.postAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/plugins/${plugin_id}/bind-function`,
      params,
    });
  }

  public copyFunction(plugin_id): Promise<any> {
    return this.http.postAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/plugins/${plugin_id}/copy-function`,
    });
  }


  public registerPlugins(params): Promise<IPlugin> {
    return this.http.postAsync({
      url: `${this.prefix}`,
      params,
    });
  }

  public updateTool(params: {
    data,
    id: string;
  }): Promise<any> {
    return this.http.putAsync({
      url: `${this.baseUrlV2}/agent-manager/tools/${params.id}`,
      params: params.data,
    });
  }
  public updatePlugins(params: {
    data,
    id: string;
  }): Promise<IPlugin> {
    return this.http.putAsync({
      url: `${this.prefix}/${params.id}`,
      params: params.data,
    });
  }

  /** 导入插件 */
  public importPlugin(formatData: FormData): Promise<any> {
    return this.http.postAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/plugins/import`,
      body: formatData,
    });
  }

  /** 导出插件 */
  public exportPlugins(params: any): Promise<any> {
    return this.http.postBlobAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/plugins/export`,
      params,
      dataType: 'blob',
    }).catch(error=>{
      if (error.data instanceof Blob) {
        this.http.parseBlobError(error.data).subscribe({
          error: (err) => {
            MessageComponent.showError(err.error_msg);
          },
        });
      }
    });
  }

  /** 插件调测时，获取运行面tool_id */
  public getDebugPluginId(params: IPlugin): Promise<any> {
    return this.http.postAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/tools/openapi`,
      params,
    });
  }

  /** 修改插件调测时，获取运行面tool_id */
  public modifyDebugPluginId(
    plugin_id: string,
    tool_id: string,
  ): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/openapi/${plugin_id}`,
      query:{
        tool_id:tool_id
      },
    });
  }

  /** 插件调测 */
  public debugPluginById(
    tool_id: string,
    parameter: string,
  ): Promise<IDebugPluginResponse> {
    let filterToolId = tool_id.replaceAll("#", "")
    return this.http.postAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/tools/${filterToolId}`,
      // url: `${this.ctxServ.baseUrl}/tools/RT_weather`,
      params: {
        parameter,
        tool_obs_key: tool_id
      },
      timeout: 300_000,
    });
  }


  /**
   * 设置插件凭据
   * @param tool_id
   * @param params
   * @param need_validate 是否需要进行校验，默认不校验
   */
  public setPluginCredentials(
    tool_id: string,
    params:any,
    need_validate?:boolean
  ): Promise<any> {
    return this.http.postAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/tools/${tool_id}/credentials`,
      params,
      query:{
        need_validate
      }
    });
  }


  public deletePluginCredentials(
    tool_id: string,
  ): Promise<IDebugPluginResponse> {
    return this.http.deleteAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/tools/${tool_id}/credentials`,
    });
  }

  public putPluginCredentials(
    tool_id: string,
    parameter: string,
  ): Promise<IDebugPluginResponse> {
    return this.http.putAsync({
      url: `${this.prefix}/${tool_id}/credentials`,
      params: {parameter},
    });
  }
  public parsePlugin(openAPI: string): Promise<IResponse> {
    return this.http.postAsync({
      url: `${this.prefix}/parse-plugin`,
      params: {
        content: openAPI,
      }
    });
  }
}
