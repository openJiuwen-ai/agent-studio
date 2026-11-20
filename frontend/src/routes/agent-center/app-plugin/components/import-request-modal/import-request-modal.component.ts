import {
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  OnInit,
  Output,
  QueryList,
  ViewChild,
  ViewChildren,
  inject,
} from '@angular/core';
import { NgForm } from '@angular/forms';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import YAML from 'yaml';
import { I18nNamespace } from '@i18n';
import { MODULES } from '@shared/modules';
import {
  MonacoEditorConstructionOptions,
  MonacoEditorLoaderService,
  MonacoEditorModule,
} from '@materia-ui/ngx-monaco-editor';
import { ArrTypeValidatorDirective } from '@shared/directives/array-type-validator.directive';
import { NonEmptyValidatorDirective } from '@shared/directives/variable-name-validator.directive';
import { MessageComponent } from '@shared/services/cfdata.service';
import { parseCurl } from './curl';
import { mapOpenApiParamLocation } from './openapi-param-location';
import { CommonUtils } from 'src/utils/common.util';
import { NzModalRef } from 'ng-zorro-antd/modal';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzAlertModule } from 'ng-zorro-antd/alert';

@Component({
  selector: 'meta-import-request-modal',
  standalone: true,
  templateUrl: './import-request-modal.component.html',
  styleUrl: './import-request-modal.component.scss',
  imports: [
    MODULES,
    MonacoEditorModule,
    ArrTypeValidatorDirective,
    NonEmptyValidatorDirective,
    NzButtonModule,
    NzAlertModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class ImportRequestModalComponent implements OnInit {
  readonly modalRef = inject(NzModalRef);

  @ViewChild('paramForm') paramForm: NgForm;

  @ViewChildren('exeEditor') editors: QueryList<any>;

  @Input() isEdit = false;

  @Output('confirm') confirm = new EventEmitter();

  public changeUrl = cdnAssetUrl;

  public lang: string = CommonUtils.getLanguage();

  public jsonData = '';

  public editorOps: MonacoEditorConstructionOptions = {
    theme: 'vs',
    language: 'yaml',
    minimap: {
      enabled: false,
    },
    lineNumbers: 'off',
  };

  placeholder = this.i18n.transform('api_import_placeholder');

  exampleUrl: string = '';

  constructor(
    private readonly cdr: ChangeDetectorRef,
    private readonly i18n: I18NextEagerPipe,
    private readonly monacoLoader: MonacoEditorLoaderService,
  ) {}

  ngOnInit() {
    if (this.lang === 'zh-cn') {
      this.exampleUrl = 'assets/images/example_zh.png';
    } else {
      this.exampleUrl = 'assets/images/example_en.svg';
    }
    this.exampleUrl = this.changeUrl(this.exampleUrl);
  }

  onConfirm() {
    if (
      this.jsonData.startsWith('swagger') ||
      this.jsonData.startsWith('openapi')
    ) {
      this.parseYaml();
    } else {
      this.parsecurl();
    }
    this.modalRef.destroy();
  }

  parseYaml() {
    let json = YAML.parse(this.jsonData);
    let url = json.servers?.[0]?.url || '';
    let path = Object.keys(json.paths)[0];
    let method = Object.keys(json.paths[path])[0];
    let data = json.paths[path][method];
    let headers = data.headers || [];
    if (headers) {
      headers = Object.keys(headers).map((key) => ({
        key: key,
        value: headers[key].schema.default || headers[key].schema.example,
      }));
    }
    let parameters = this.getYamlParameters(data.parameters);
    let requestBody = this.getYamlRequestBody(data.requestBody);
    let apiInfo = {
      method: method.toUpperCase(),
      url: url + path,
      headers: headers,
      params: [...parameters, ...requestBody],
    };
    this.confirm.emit(apiInfo);
  }

  parsecurl() {
    let data = parseCurl(this.jsonData);
    if (!data.error) {
      let parameters = this.getcurlParameters(data.node.params);
      let requestBody = this.getcurlRequestBody(data.node.body);
      let apiInfo = {
        method: data.node.method.toUpperCase(),
        url: data.node.url,
        headers: this.getHeaders(data.node.headers),
        params: [...parameters, ...requestBody],
      };
      this.confirm.emit(apiInfo);
    } else {
      MessageComponent.showError(data.error);
    }
  }

  getHeaders(str) {
    let header: string[] = str.split('\n');
    return header.map((item) => {
      if (item.includes(':')) {
        let key = item.split(':')[0].trim();
        let value = item.split(':')[1]?.trim();
        return {
          key,
          value,
        };
      } else {
        return {
          key: item.slice(0, -1),
          value: '',
        };
      }
    });
  }

  getcurlParameters(str) {
    if (!str) {
      return [];
    }

    let params: string[] = str.split('\n');

    return params.map((item) => {
      let key = item.split(':')[0].trim();
      let value = item.split(':')[1].trim();
      return {
        name: key,
        default: value,
        type: 'string',
        location: 'Query',
      };
    });
  }

  getcurlRequestBody(body) {
    if (!body.data || !body.data[0]?.value) {
      return [];
    }

    try {
      let value = JSON.parse(body.data[0]?.value);
      return Object.keys(value).map((key) => ({
        name: key,
        default:
          typeof value[key] !== 'string'
            ? JSON.stringify(value[key])
            : value[key],
        type: typeof value[key] !== 'object' ? typeof value[key] : 'string',
        location: 'Body',
      }));
    } catch (error) {
      return [];
    }
  }

  getYamlParameters(parameters) {
    if (!parameters) {
      return [];
    }

    return parameters.map((item) => ({
      name: item.name,
      default: item.schema.default,
      type: item.schema.type,
      schema: item.schema,
      // OpenAPI uses "header"; tool schema tabs/backend expect "Headers".
      location: mapOpenApiParamLocation(item.in),
    }));
  }

  getYamlRequestBody(requestBody) {
    if (!requestBody) {
      return [];
    }

    const properties =
      requestBody.content['application/json'].schema.properties;

    if (!properties) {
      return [];
    }

    return Object.keys(properties).map((key) => ({
      name: key,
      default: properties[key].example,
      type: properties[key].type,
      location: 'Body',
    }));
  }

  public onInputJSONChange() {
    this.cdr.detectChanges();
  }

  dismiss() {
    this.modalRef.destroy();
  }
}
