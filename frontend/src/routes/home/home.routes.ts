import { Routes } from '@angular/router';
import { I18NEXT_NAMESPACE_RESOLVER } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { AGENT_CORE, I18N_NAMESPACE } from '@agentcore/constants/common';
import { agentCoreRoutes, cfServiceGuard } from '@agentcore/routes';
/**
 * 主页路由
 */
export const HOME_ROUTES: Routes = [
  {
    path: 'overview',
    loadChildren: () =>
      import('@routes/overview').then(
        (module) => module.OverviewRoutingModule,
      ),
    data: {
      i18nextNamespaces: [I18nNamespace.AGENT_CENTER,I18nNamespace.PROMPT_PLATFORM],
    },
    resolve: {
      i18next: I18NEXT_NAMESPACE_RESOLVER,
    },
  },
  {
    path: 'chat',
    loadChildren: () =>
      import('@routes/web-page-experience').then(
        (module) => module.WebPageRoutingModule,
      ),
    data: {
      i18nextNamespaces: [I18nNamespace.AGENT_CENTER],
    },
    resolve: {
      i18next: I18NEXT_NAMESPACE_RESOLVER,
    },
  },
  {
    path: 'scheduler',
    loadChildren: () =>
      import('@routes/scheduler').then(
        (module) => module.SchedulerRoutingModule,
      ),
    data: {
      i18nextNamespaces: [I18nNamespace.AGENT_CENTER],
    },
    resolve: {
      i18next: I18NEXT_NAMESPACE_RESOLVER,
    },
  },
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'overview',
  },
  {
    path: 'prompt',
    loadChildren: () =>
      import('@routes/prompt').then((m) => m.PromptRoutingModule),
    data: {
      i18nextNamespaces: [I18nNamespace.PROMPT_PLATFORM],
    },
    resolve: {
      i18next: I18NEXT_NAMESPACE_RESOLVER,
    },
  },
  {
    path: 'agent-center',
    loadChildren: () =>
      import('@routes/agent-center').then(
        (module) => module.AgentCenterRoutingModule,
      ),
    data: {
      i18nextNamespaces: [I18nNamespace.AGENT_CENTER, I18nNamespace.KNOWLEDGE],
    },
    resolve: {
      i18next: I18NEXT_NAMESPACE_RESOLVER,
    },
  },
  {
    path: 'knowledge-center',
    loadChildren: () =>
      import('@routes/knowledge-center').then(
        (module) => module.KnowledgeCenterRoutingModule,
      ),
    data: {
      i18nextNamespaces: [I18nNamespace.AGENT_CENTER],
    },
    resolve: {
      i18next: I18NEXT_NAMESPACE_RESOLVER,
    },
  },
  {
    path: 'app-library',
    loadChildren: () =>
      import('@routes/app-center').then(
        (module) => module.AppCenterRoutingModule,
      ),
    data: {
      i18nextNamespaces: [I18nNamespace.AGENT_CENTER,I18nNamespace.PROMPT_PLATFORM],
    },
    resolve: {
      i18next: I18NEXT_NAMESPACE_RESOLVER,
    },
  },
  {
    path: 'intent-package',
    loadChildren: () =>
      import('@routes/intent-package').then(
        (module) => module.IntentPackageRoutingModule,
      ),
    data: {
      i18nextNamespaces: [I18nNamespace.AGENT_CENTER],
    },
    resolve: {
      i18next: I18NEXT_NAMESPACE_RESOLVER,
    },
  },
  {
    path: 'plugin-market',
    loadChildren: () =>
      import('@routes/plugin-market').then(
        (module) => module.PluginMarketRoutingModule,
      ),
    data: {
      i18nextNamespaces: [I18nNamespace.AGENT_CENTER],
    },
    resolve: {
      i18next: I18NEXT_NAMESPACE_RESOLVER,
    },
  },
  {
    path: 'skill-market',
    loadChildren: () => import('@routes/skill-market').then(module => module.SkillMarketRoutingModule),
    canActivate: [cfServiceGuard],
    data: {
      i18nextNamespaces: [I18N_NAMESPACE.Skill, I18N_NAMESPACE.Common].map(v => `${AGENT_CORE}.${v}`),
    },
    resolve: {
      i18next: I18NEXT_NAMESPACE_RESOLVER,
    },
  },
  {
    path: 'model-square',
    loadChildren: () =>
      import('@routes/model-square').then(
        (module) => module.ModelSquareRoutingModule,
      ),
    data: {
      i18nextNamespaces: [I18nNamespace.JIUWEN_MODEL],
    },
    resolve: {
      i18next: I18NEXT_NAMESPACE_RESOLVER,
    },
  },
  {
    path: 'service-market',
    loadChildren: () =>
      import('@routes/service-market').then(
        (module) => module.ServiceMarketRoutingModule,
      ),
    data: {
      i18nextNamespaces: [I18nNamespace.AGENT_CENTER],
    },
    resolve: {
      i18next: I18NEXT_NAMESPACE_RESOLVER,
    },
  },
  {
    path: 'model',
    loadChildren: () =>
      import('@routes/model-management/model-management-routing.module').then(
        (module) => module.ModelManagementRoutingModule,
      ),
    data: {
      i18nextNamespaces: [I18nNamespace.MODEL_ACCESS, I18nNamespace.JIUWEN_MODEL,I18nNamespace.AGENT_CENTER],
    },
    resolve: {
      i18next: I18NEXT_NAMESPACE_RESOLVER,
    },
  },
  {
    path: 'datasource',
    loadChildren: () =>
      import(
        '@routes/datasource-management/datasource-management-routing.module'
      ).then((module) => module.DatasourceManagementRoutingModule),
    data: {
      i18nextNamespaces: [I18nNamespace.AGENT_CENTER],
    },
    resolve: {
      i18next: I18NEXT_NAMESPACE_RESOLVER,
    },
  },
  {
    path: 'information',
    loadChildren: () =>
      import('@routes/information-template/information-template-routing.module').then(
        (module) => module.InformationTemplateRoutingModule,
      ),
    data: {
      i18nextNamespaces: [I18nNamespace.AGENT_CENTER],
    },
    resolve: {
      i18next: I18NEXT_NAMESPACE_RESOLVER,
    },
  },
  { path: 'platform-management',
    loadChildren: () =>
      import('@routes/platform-management/platform-management-routing.module').then(
        (module) => module.PlatformManagementRoutingModule,),
    data: {
       i18nextNamespaces: [I18nNamespace.PLATFORM_MANAGEMENT],
    },
    resolve: {
       i18next: I18NEXT_NAMESPACE_RESOLVER,
    },
  },
  {
    path: 'ai-assist-create-home',
    loadChildren: () =>
      import('@routes/ai-assist-create-home/ai-assist-create-home-routing.module').then(
        (module) => module.AiAssistCreateHomeRoutingModule,
      ),
    data: {
      i18nextNamespaces: [I18nNamespace.AGENT_CENTER,I18nNamespace.PROMPT_PLATFORM],
    },
    resolve: {
      i18next: I18NEXT_NAMESPACE_RESOLVER,
    },
  },
  {
    path: 'ai-assist-create-agent',
    loadChildren: () =>
      import('@routes/ai-assist-create-agent/ai-assist-create-agent-routing.module').then(
        (module) => module.AiAssistCreateAgentRoutingModule,
      ),
    data: {
      i18nextNamespaces: [I18nNamespace.AGENT_CENTER,I18nNamespace.PROMPT_PLATFORM],
    },
    resolve: {
      i18next: I18NEXT_NAMESPACE_RESOLVER,
    },
  },
  {
    path: 'ai-assist-create-workflow',
    loadChildren: () =>
      import('@routes/ai-assist-create-workflow/ai-assist-create-workflow-routing.module').then(
        (module) => module.AiAssistCreateWorkflowRoutingModule,
      ),
    data: {
      i18nextNamespaces: [I18nNamespace.AGENT_CENTER,I18nNamespace.PROMPT_PLATFORM],
    },
    resolve: {
      i18next: I18NEXT_NAMESPACE_RESOLVER,
    },
  },
  {
    path: 'development-configuration',
    loadChildren: () =>
      import('@routes/development-configuration/development-configuration-routing.module').then(
        (module) => module.DevelopmentConfigurationRoutingModule,
      ),
    data: {
      i18nextNamespaces: [I18nNamespace.AGENT_CENTER,I18nNamespace.PROMPT_PLATFORM],
    },
    resolve: {
      i18next: I18NEXT_NAMESPACE_RESOLVER,
    },
  },
  ...agentCoreRoutes,
  {
    path: 'memory-lib',
    loadChildren: () => import('@routes/memory-lib/memory-lib-routing.module').then(module => module.MemoryLibRoutingModule),
    data: {
      i18nextNamespaces: [I18nNamespace.MEMORY_LIB, I18N_NAMESPACE.Common],
    },
    resolve: {
      i18next: I18NEXT_NAMESPACE_RESOLVER,
    },
  },
  {
    path: 'conversation',
    loadChildren: () =>
      import('@routes/conversation-workspace/conversation-workspace-routing.module').then(
        (module) => module.ConversationWorkspaceRoutingModule,
      ),
  },
  {
    path: '**',
    redirectTo: 'overview',
  },
];
