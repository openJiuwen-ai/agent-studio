import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { SchedulerComponent } from './scheduler.component';
import ShowLeftmenuGuard from '@shared/guard/showLeftmenu.guard';
import DevelopGuard from '@shared/guard/develop.guard';

const routes: Routes = [
  {
    path: '',
    component: SchedulerComponent,
    canActivate: [ShowLeftmenuGuard, DevelopGuard],
    children: [],
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class SchedulerRoutingModule {}
