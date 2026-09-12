import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ConversationWorkspaceComponent } from './conversation-workspace.component';

const routes: Routes = [
  {
    path: '',
    component: ConversationWorkspaceComponent,
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class ConversationWorkspaceRoutingModule {}
