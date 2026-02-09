# Input Component

The Input component is used to dynamically obtain specific information required from the user during workflow execution. When the workflow reaches this component, it automatically pauses and waits for the user to submit the necessary input before continuing with subsequent steps, ensuring that complex tasks dependent on user data are completed smoothly and accurately.

# Configuring the Component

## Steps

1. Go to the openJiuwen platform homepage.
2. Open the Workflow Orchestration module in the left navigation.
3. Click the Add Component button at the bottom of the page and select Input.

![image](../../../images/bfc9a546-eab3-4e15-ba98-ed635bd6296b.png)

4. Complete the configuration in the pop-up dialog.

![image](../../../images/999ac634-e493-41cf-9335-f7ba6437fb74.png)

The Input component supports one or more input parameters. Configure each parameter according to the following rules to ensure the workflow correctly collects data and runs:

| Field | Description |
|------|------|
| Input Variable Name | Required. Defines the unique identifier of the input parameter. This name will be referenced in later prompts or components using variable syntax (e.g., `{{parameter_name}}`). |
| Parameter Type (type) | Optional; defaults to `String`. Supports the following five data types:<br>• String: text<br>• Integer: integer<br>• Number: floating-point or numeric<br>• Boolean: true/false<br>• Object: JSON object for structured input |
| Description (description) | Optional. Provide details about the parameter to clarify its purpose and expected content. Improves workflow readability and maintainability. |
| Default Value (default value) | Optional. Sets the value to use when no specific value is provided. If no default is set and the parameter is required, the user must provide a valid value at runtime. |
| Required | A checkbox that specifies whether the parameter is required.<br>• If selected, a valid value must be provided when the workflow reaches this component; otherwise, execution will halt.<br>• If not selected, the parameter is optional and the workflow will continue even if it is left blank. |

## Example

Use the Input component to collect height and weight, then call the model component to compute the corresponding BMI.

![image](../../../images/afc771e8-8c33-47f8-b740-07b716f9fb0f.png)

The key components of this workflow are as follows:

| Component Type | Configuration | Example |
| :------: | :------ | :------: |
| Input Component | Add two required parameters:<br>● height (the person's height)<br>● weight (the person's weight) | ![image](../../../images/787edb5d-5d6e-48c5-820b-f89c37e9dd90.png) |
| Large Model Component | Configure the following:<br>● Input: add the two inputs, height and weight<br>● System prompt: the agent persona; design as needed<br>● User prompt: the question for the model; reference the two input parameters<br>● Output: keep the default settings | ![image](../../../images/c05ea191-b929-403c-bad2-2e516aea6ad7.png) |