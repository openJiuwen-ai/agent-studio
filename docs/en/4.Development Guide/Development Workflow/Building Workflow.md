# Build a Workflow

This chapter explains in detail how to create, configure, and connect workflow components in the workflow editor, helping users quickly build workflows that are well-structured and logically correct. The openJiuwen workflow provides a feature-rich visual designer that supports intuitive drag-and-drop operations and intelligent connection configuration: users can easily drag components onto the canvas for free layout, and the system automatically validates connections to ensure logical correctness. It also supports real-time execution preview, custom component positioning, canvas zooming and panning, as well as undo/redo for flexible edits, and copy-paste to efficiently reuse existing components and workflow structures.

## Create a New Workflow

### Steps

1. Go to the openJiuwen homepage.
2. Open Workflow Orchestration from the left navigation.

![image](../images/fd0e28b5-0df7-47e3-a0cc-25af1ed70061.png)

3. Click Create.
On the Workflow Orchestration page, you will see a list of workflows. Click the Create Workflow button in the upper-right corner to start creating a new workflow.

![image](../images/eea7cd3e-3de1-4787-8b0e-1860228c4006.png)

4. Enter basic information.
Provide the following basic information for your workflow:

   | Parameter | Description |
   | --- | ---|
   | Workflow Name | A descriptive name. Only letters, numbers, and underscores are supported and it must start with a letter. |
   | Workflow Description | A brief description explaining the workflow’s main function and use case. |

   ![image](../images/b9ffb9cb-1e33-4d8e-903b-c1f80323433c.png)

5. Confirm creation.

   After completing the information, click Create Workflow. The system will automatically generate a unique workflow ID and navigate to the workflow editor, where you can start building the logic.

   ![image](../images/488165ad-1fab-4eeb-ad08-b187c6ee8b6c.png)

## Orchestrating the Workflow

### Steps

   1. Click a workflow to enter the workflow editor.

      ![image](../images/65d07d6b-bc5b-49c1-81c5-b24f541d5ad0.png)

   2. Add components: Drag the required components from the component library onto the canvas. Each component represents a specific functional node, such as workflow, input/output, or business logic.

      ![image](../images/2b9e5345-916a-4779-8f4f-87199f5b14c5.png)

   3. Configure components: After adding a component, click it to open its configuration panel on the right. In the panel, you can set the component’s parameters, input/output formats, execution logic, and more. Adjust these according to the component type and your actual needs. For details, see [Configuration Components](./Configuration%20Components/README.md).

      ![image](../images/67fe5f90-59fe-4bf3-bf59-cca7d9a80e7c.png)

   4. Connect components: To define executable logic, connect components by clicking an output port of one component and dragging to the input port of another. These connections determine execution order and data flow paths.

      ![image](../images/76b241ad-87b5-4bd1-8ffe-205a32c6eded.png)

   5. Adjust layout: To improve readability and maintainability, drag components to reposition them on the canvas. It’s recommended to arrange components in logical order for clarity.

      ![image](../images/微信图片_2025-12-10_193516_642.png)

   6. Save the workflow: After adding, configuring, and connecting components, click Save in the top toolbar to store the current configuration. You can return to the editor at any time to modify or optimize it.

      ![image](../images/20719310-3e7f-4c9c-96fb-29017fbd07fd.png)

## Test Run

### Steps

1. Click Trial Run to manually trigger the workflow execution.

   ![image](../images/418d8915-d264-4091-b358-53790a931fff.png)

2. Observe the results to verify whether the logic is correct.

   ![image](../images/4d6da567-bb85-4c16-b8e6-a256e00b37dc.png)

## Save a Version

### Steps

1. Click Submit New Version to save a version.

   ![image](../images/e84e6981-c756-4a91-ba19-0eaefd07a2f9.png)

## View and Roll Back Versions

### Steps

1. Click Version History to view all versions.

   ![image](../images/c0be7bbb-cbda-46cd-85cd-fad753fda928.png)

   ![image](../images/86e21a68-1306-45c6-a065-8e98d98fceab.png)

2. Click any saved version to manage it, including creating a copy, restoring to that version, or deleting it. Click Restore to This Version to roll back the canvas to the selected version.

   ![image](../images/9c169e5a-3075-4c07-b0a4-2413d0c748a6.png)