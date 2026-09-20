import { Injectable } from '@angular/core';
import { IBatchMappings } from '@routes/agent-center/types/common.types';
import {
  IDatasourceDetail,
  IDatasourceList,
  IModifyDatasourceBody,
} from '@routes/agent-center/types/datasource.types';
import { ContextService } from '@services/context.service';
import { HttpService } from '@services/http.service';

@Injectable({
  providedIn: 'root',
})
export class DataSourceManagementRepoService {
  get prefix() {
    return `${this.ctxServ.baseUrl}/agent-manager`;
  }

  constructor(private http: HttpService, private ctxServ: ContextService) {}

  /** 查询数据源列表 */
  public getDatasourceList(params: any): Promise<IDatasourceList> {
    return this.http.getAsync({
      url: `${this.prefix}/datasource`,
      query: {
        ...params,
      },
    });
  }

  // 查询数据表
  public getSqlTableList(params: any, datasource_id: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/datasource/${datasource_id}/tables`,
      query: {
        ...params,
      },
    });
  }

  // 查询数据表字段
  getSqlTableColumn(params: any, datasource_id: string, table_name: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/datasource/${datasource_id}/tables/${table_name}/columns`,
      query: {
        ...params,
      },
    });
  }

  /** 单个删除数据源 */
  public deleteDatasource(id: string) {
    return this.http.deleteAsync({
      url: `${this.prefix}/datasource/${id}`,
    });
  }

  /** 新建数据源 */
  public createDatasource(params: IModifyDatasourceBody) {
    return this.http.postAsync({
      url: `${this.prefix}/datasource`,
      params,
    });
  }

  /** 查询单个数据源详情 */
  public getDatasourceDetail(id: string): Promise<IDatasourceDetail> {
    return this.http.getAsync({
      url: `${this.prefix}/datasource/${id}`,
    });
  }

  /** 更新数据源 */
  public modifyDatasource(id: string, params: IModifyDatasourceBody) {
    return this.http.putAsync({
      url: `${this.prefix}/datasource/${id}`,
      params,
    });
  }

  /** 批量删除数据源 */
  public batchDeleteDatasource(datasourceIds: string[]) {
    return this.http.postAsync({
      url: `${this.prefix}/datasource/batch-delete`,
      params: { datasourceIds },
    });
  }

  /** 批量删除数据源时，获取被引用的列表 */
  public getBatchRefList(params: any): Promise<IBatchMappings> {
    return this.http.getAsync({
      url: `${this.prefix}/relation/resources`,
      query: {
        ...params,
      },
    });
  }
}
