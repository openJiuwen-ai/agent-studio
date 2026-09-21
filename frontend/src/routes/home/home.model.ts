export interface IMenuItem {
  id?: string;
  name: string;
  label: string;
  router?: any;
  routerList?: any[];
  children?: IMenuItem[];
  isGroup?: boolean;
  isHide?: boolean;
  hide?: boolean;
  icon?: string;
  iconSelected?: string;
  rightIcon?: string;
  tipIcon?: string;
  isSelected?: boolean;
  collapseStatus?: number;
  onlyOpAccount?: boolean;
  queryParams?: Record<string, string>;
}

interface LeftmenuConfig {
  config: any;
  items: Array<IMenuItem>;
}

export interface ViewModel {
  leftmenu: LeftmenuConfig;
}
