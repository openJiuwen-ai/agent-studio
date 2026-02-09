# End Component

The End node outputs the workflow result. It is the final (required) node of a workflow and marks its termination. After the workflow finishes running, it returns the specified output directly.
![image](../../../images/5cde4461-85ee-409e-baab-74ace0f9f21e.png)

# Configure the Component

## Steps

1. Go to the openJiuwen platform homepage.
2. Open the Workflow Orchestration module in the left navigation.
3. Click the End component on the canvas to open its editing interface.

![image](../../../images/e57a423f-d8a7-4fe1-8358-ba0919444561.png)

4. Add or delete input parameters: click `+` to add a parameter, click ![image](../../../images/9bc87254-e58f-48f6-9cf9-d7a946887e83.png) to delete a parameter.

![image](../../../images/a8d5beeb-393d-4e5c-9fc1-a1573ea07047.png)

Parameter descriptions for the End component:

| Parameter | Description |
| --- | --- |
| Left input box | Key of the output parameter |
| Right input box | Data type: supports configuring various parameter types such as `String`, `Number`, and `Object`. The variable value can be a fixed value or reference the output of upstream components. |