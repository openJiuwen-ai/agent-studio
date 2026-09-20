export interface IDatasourceList {
  total: number;
  datasources: IDatasourceItem[];
}

export interface IDatasourceItem {
  id: string;
  name: string;
  desc: string;
  type: string;
  status: string;
  lastErrorMessage: string;
  createdBy: string;
  createdOn: string;
  updatedBy: string;
  updatedOn: string;
  connectionInfo: IConnectionInfo;
}

export interface IDatasourceDetail {
  id: string;
  name: string;
  desc: string;
  type: string;
  status: string;
  lastErrorMessage: string;
  createdBy: string;
  createdOn: string;
  updatedBy: string;
  updatedOn: string;
  connectionInfo: IConnectionInfo;
}

export interface IConnectionInfo {
  host: string;
  port: string;
  sslEnabled: boolean;
  databaseName: string;
  user: string;
  password: string;
  sqlVersion?: string;
  metadata?: Record<string, string>;
}

export interface IModifyDatasourceBody {
  name: string;
  desc: string;
  type: string;
  connectionInfo: IConnectionInfo;
}
