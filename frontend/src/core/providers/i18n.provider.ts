import {
  APP_INITIALIZER,
  EnvironmentProviders,
  LOCALE_ID,
  Provider,
  importProvidersFrom,
} from '@angular/core';
import {
  I18NEXT_SERVICE,
  I18NextModule,
  ITranslationService,
} from 'angular-i18next';
import i18nextHttpBackend from 'i18next-http-backend';
import { en_US, NZ_I18N, zh_CN } from 'ng-zorro-antd/i18n';

import { ConsoleFrameworkService } from '@core/services';
import { I18NEXT_CONFIG } from '@i18n';
import { Lang } from '@model';

/**
 * I18N provider
 */
export const I18N_PROVIDERS: (Provider | EnvironmentProviders)[] = [
  {
    provide: APP_INITIALIZER,
    multi: true,
    deps: [I18NEXT_SERVICE, ConsoleFrameworkService],
    useFactory:
      (
        i18NextService: ITranslationService,
        consoleFrameworkService: ConsoleFrameworkService,
      ) =>
      () =>
        new Promise((resolve) => {
          (async () => {
            try {
              await i18NextService.use(i18nextHttpBackend).init(I18NEXT_CONFIG);
              const language =
                Lang.LANGUAGE_MAP.get(
                  // eslint-disable-next-line @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
                  consoleFrameworkService.dataService?.getLocale() as string,
                ) ?? Lang.Language['zh-CN'];

              await i18NextService.changeLanguage(language);
            } catch {
              // 空捕获
            }

            return resolve(null);
          })();
        }),
  },
  {
    provide: APP_INITIALIZER,
    multi: true,
    deps: [],
    useFactory:
      () =>
      () =>
        new Promise((resolve) => {
          (async () => {
              try {
                let result = {};
                (<any>window).HELP_CENTER_LINKS = result ? result : {};
                } catch (error) {
                  /** cf框架加载异常 */
                }
            return resolve(null);
          })();
        }),
  },
  {
    provide: LOCALE_ID,
    deps: [I18NEXT_SERVICE],
    useFactory: (i18NextService: ITranslationService) =>
      i18NextService.language,
  },
  {
    provide: NZ_I18N,
    deps: [ConsoleFrameworkService],
    useFactory: (consoleFrameworkService: ConsoleFrameworkService) => {
      const language =
        Lang.LANGUAGE_MAP.get(
          // eslint-disable-next-line @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
          consoleFrameworkService.dataService?.getLocale() as string,
        ) ?? Lang.Language['zh-CN'];
      return language === Lang.Language['en-US'] ? en_US : zh_CN;
    },
  },
  importProvidersFrom(I18NextModule.forRoot()),
];

export default I18N_PROVIDERS;
