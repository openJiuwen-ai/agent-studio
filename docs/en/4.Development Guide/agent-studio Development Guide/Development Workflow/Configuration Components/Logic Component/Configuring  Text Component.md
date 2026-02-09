# Configure the Text Editing Component

The Text Editing component is a functional component in workflows for processing text data. It is designed for developers who need to handle text within workflows, suitable for scenarios such as secondary summarization, string concatenation, and text escaping. It solves issues like inconsistent text data formats and the need to combine or split strings within workflows.

# Configure the Component

## Steps
1. Go to the openJiuwen platform homepage.
2. Open the Workflow Orchestration module from the left navigation bar.
3. Click the Add Component button at the bottom of the page and select the Text Editing component.<br>
![image](../../../images/bbfce989-740e-43b0-97fd-6344ec66bb02.png)

4. Click the Text Editing component that appears on the canvas to start configuring it.<br>
![image](../../../images/c3180900-8381-4202-8186-accc1bcdb339.png)

5. Choose the text processing method. Two main methods are supported: **String Concatenation** and **String Split**.<br>
![image](../../../images/9b2061f6-4086-428a-8f34-f1ff68583c41.png)

6. Configure input parameters.<br>
![image](../../../images/f88ae71e-cfea-4af5-954e-e64bd226c199.png)

7. Add and configure multiple input parameters.<br>
![image](../../../images/bb4ef983-dfab-4933-b02c-c5168300a09b.png)

8. Configure input parameter names.<br>
![image](../../../images/b9bb35a5-32ad-4647-b8c7-f5237b96643f.png)

9. Configure processing rules.
    1. String Concatenation — configure concatenation rules.<br>
    ![image](../../../images/c12bbbfa-66bf-4c16-a73b-c4dc2655cfd5.png)
    2. String Split — configure the delimiter.<br>
    ![image](../../../images/018b0c3e-8176-46ce-ae4a-0903efa009e9.png)

The configuration of the Text Editing component is as follows:

| Configuration | Description |
| :------: | :------ |
| Text Processing Method | The processing methods supported by the Text Editing component currently include two main options:<br> 1. **String Concatenation**: Concatenate specified inputs in a defined order into a single string. This is useful for combining key information from upstream components to be used as inputs for downstream components.<br> 2. **String Split**: Split the input content into an array of strings using a specified delimiter to facilitate processing by subsequent components. You need to specify the delimiter for splitting. Supported delimiters include: newline, comma, semicolon, period, and tab, and custom delimiters are also supported. |
| Input Parameters | The input parameters required for text processing; various types are supported. |
| Concatenation Template | Fill in when selecting the String Concatenation method; customize the output concatenation template. |
| Delimiter | Fill in when selecting the String Split method; specify the delimiter used to split the input, with support for custom delimiters. |

## Examples
1. String Concatenation
Example usage of String Concatenation is as follows:<br>
![image](../../../images/e4fa0752-bdaf-4e5a-9780-ec87507f799d.png)<br>
Execution result is as follows:<br>
![image](../../../images/458e498a-169e-46e9-81f9-db81fe72373d.png)

2. String Split
Example usage of String Split is as follows, using "," as the delimiter:<br>
![image](../../../images/7eb81680-7201-4e40-885f-af8f17743a49.png)<br>
Execution result is as follows:<br>
![image](../../../images/ea148232-0a8f-478e-b8e3-02e69f3a2d3d.png)