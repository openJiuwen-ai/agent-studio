# Selector Component

The selector component is used to connect multiple downstream branches and control the workflow execution path by setting conditions. Only the branch whose conditions are met will be executed, equivalent to an if-else conditional node in software development. This component helps developers build complex branching logic and is suitable for scenarios where different processes need to run based on different conditions.

## Notes

* Condition evaluation is based on the workflow’s runtime context data; ensure the referenced variables are available.
* When multiple conditions are satisfied at the same time, only the first matching branch will be executed.
* It is recommended to configure a default branch to handle cases where none of the conditions are met.

## Steps

1. Log in to the openJiuwen platform.

2. Go to the Workflow Orchestration module in the left navigation bar.

3. Enter the workflow editing page.

4. Click the Add Component button at the bottom of the page, then click Selector.
    ![image](../../../images/c140ca73-c963-4f70-a8c0-c4568894102a.png)

5. Click the selector component node to open the component configuration panel.

6. Click the "Select Condition" button and choose a condition type.
   
   ![image](../../../images/ed40cd6f-14f6-4ef5-9d46-9cc9da51bf4a.png)
   
   ![image](../../../images/673be27b-7531-47bc-ad7e-367e707a5f9e.png)

7. Enter the specific condition content in the input box.
   
   ![image](../../../images/fa73f986-6558-4278-8d67-7136fa685af5.png)

8. Click the `+` button to add conditions. Multiple conditions and multiple conditional branches are supported.
   
   ![image](../../../images/452f968f-8571-46d8-b017-d3ffecda825f.png)

9. Configure the corresponding downstream nodes for each conditional branch to complete the selector component configuration.