import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import {HasPermissionDirective} from "@shared/directives/has-permission.directive";
import {HasRoleDirective} from "@shared/directives/has-role.directive";
import {CanModifyDirective} from "@shared/directives/can-modify.directive";


@NgModule({
  declarations: [],
  imports: [CommonModule, HasRoleDirective, HasPermissionDirective, CanModifyDirective],
  exports: [HasPermissionDirective, HasRoleDirective, CanModifyDirective],
})
export class SharedModule {}
