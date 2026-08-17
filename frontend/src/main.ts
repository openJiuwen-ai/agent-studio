import 'reflect-metadata';
import {
  provideHttpClient,
  withInterceptorsFromDi,
} from '@angular/common/http';
import {
  EnvironmentProviders,
  importProvidersFrom,
  isDevMode,
  Provider,
} from '@angular/core';
import { bootstrapApplication } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { AppComponent } from '@app';
import { I18N_PROVIDERS } from '@core/providers/i18n.provider';
import { ROUTER_GUARD_PROVIDER } from '@core/providers/route-guard.provider';
import { ROUTER_PROVIDER } from '@core/providers/router.provider';
import { MONACO_PATH } from '@materia-ui/ngx-monaco-editor';
import { Network } from '@model';
import { I18nService } from '@agentcore/core/i18n.service';
import { provideMarkdown } from 'ngx-markdown';
import { NzModalModule } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';
import { initMessageService } from '@shared/services/cfdata.service';

const basePath = document.getElementsByTagName('base')[0]?.getAttribute('href') || '/';
const prifix = isDevMode() ? `${window.location.origin}/` : `${window.location.origin}${basePath}`;

const PROVIDERS: (Provider | EnvironmentProviders)[] = [
  ROUTER_PROVIDER,
  I18N_PROVIDERS,
  ROUTER_GUARD_PROVIDER,
  importProvidersFrom(BrowserAnimationsModule),
  importProvidersFrom(NzModalModule),
  importProvidersFrom(NzMessageService),
  {
    provide: MONACO_PATH,
    useValue: `${prifix}${Network.ASSETS_PATH}monaco-editor/min/vs`,
  },
  provideMarkdown(),
  provideHttpClient(withInterceptorsFromDi()),
];

function llog(e: any) {
  return e;
}

const ROOT_SERVICE_PROVIDER = [I18nService];

bootstrapApplication(AppComponent, {
  providers: [...PROVIDERS, ...ROOT_SERVICE_PROVIDER],
}).then((appRef) => {
  const messageService = appRef.injector.get(NzMessageService);
  initMessageService(messageService);
  return appRef;
}).catch((error) => {
  llog(error);
});
