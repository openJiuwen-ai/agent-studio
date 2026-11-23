import { Injectable } from '@angular/core';
import { ContextService } from '@services/context.service';
import { HttpService } from '@services/http.service';

@Injectable({
  providedIn: 'root',
})
export class CardService {
  get prefixBase() {
    return `${this.ctxServ.baseUrl}`;
  }

  constructor(private http: HttpService, private ctxServ: ContextService) {}

  // 卡片列表
  public getCardList(query: any): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefixBase}/agent-manager/cards`,
      query: query,
    });
  }

  // 新增卡片
  public addCard(params: any): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefixBase}/agent-manager/cards`,
      params: params,
    });
  }

  // 更新卡片
  public updateCard(params: any): Promise<any> {
    return this.http.putAsync({
      url: `${this.prefixBase}/agent-manager/cards`,
      params: params,
    });
  }

  // 删除卡片
  public deleteCard(id: any): Promise<any> {
    return this.http.deleteAsync({
      url: `${this.prefixBase}/agent-manager/card/${id}`,
    });
  }

  // 查询卡片详细
  public detailsCard(id: any, version_id: any): Promise<any> {
    let query: any = {};
    if (version_id && version_id.length > 0) {
      query = { version_id: version_id };
    }

    return this.http.getAsync({
      url: `${this.prefixBase}/agent-manager/card/${id}`,
      query: query,
    });
  }

  // 查询卡片版本列表
  public getCardVersionList(id: any): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefixBase}/agent-manager/card/${id}/versions`,
    });
  }

  // 发布卡片,还原版本 version_id
  public postCardVersionDetails(params: any): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefixBase}/agent-manager/card/${params.id}/versions`,
      params: params,
    });
  }

  // 删除卡片版本
  public deleteCardVersion(params: any): Promise<any> {
    return this.http.deleteAsync({
      url: `${this.prefixBase}/agent-manager/card/${params.id}/versions/${params.version_id}`,
    });
  }

  // 引用列表
  // cancelGlobalError: 跳过 handleError 全局错误 toast，由调用方自行 catch 处理
  // （下架前引用确认失败走通用确认，不应再弹全局 toast 致双提示）
  public selectQuoteList(id: any, query: any, cancelGlobalError = false): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefixBase}/agent-manager/relation/resources/${id}`,
      query: query,
      cancelGlobalError,
    });
  }
}
