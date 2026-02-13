This guide provides a detailed introduction to the prompt version management system, including the official version submission workflow, version difference comparison, historical version viewing and operations, helping you establish a complete prompt version control and collaboration process.

# Submit a New Version

## Steps

1. Click the **“Submit New Version”** button at the top of the page. The system will automatically retrieve detailed information about the current draft and the latest official version. If an official version already exists, the system will display a version difference comparison.

   ![image](../images/56629bf1cfb7216d5ee2ee0c1f43c2e4.png)

2. If an official version already exists, the system will display a detailed version difference comparison. The system automatically detects whether there are substantive changes. If no changes are detected, submission is not allowed. If this is the first time submitting a new version, no difference comparison will be shown.

   Example:

   ![image](../images/835c84c2-9fdb-4307-adcf-d27fd6c04d5e.png)

3. After confirming the differences (or directly entering this step for the first submission), fill in the version information.

   The prompt version information parameters are as follows:

   | Parameter Name | Description | Constraints |
   |---------------|-------------|-------------|
   | Version Number | Enter a version number that conforms to the specification | Required, up to 50 characters |
   | Version Description | Enter the version update description | Optional, up to 200 characters |

   Example of filling in version information for the first submission:

   ![image](../images/1d476e74-2333-44a7-a11e-e686e238a654.png)

   Example of filling in version information for subsequent submissions:

   ![image](../images/ca32bb7f-77c4-47e3-8d4f-df342c71f901.png)

4. Click **“Confirm Submit New Version”** to complete the version release.

# View Version History

Version history records all official versions for easy traceability and collaboration.

## Steps

1. Click the **“Version History”** button at the top of the page. In the pop-up panel, you can view the release time, creator, and description of each version.

   ![image](../images/a82f6628-6d58-43bf-961f-722d9492c711.png)

2. Select a specific version to load its content into the editing area. Selecting a draft will load the draft content into the editing area.

   ![image](../images/a04fb446-ac37-4e4c-9ce8-f3d64be67911.png)

# Create a Copy

## Steps

1. Select the target version from the version history list.
2. Click the **“Create Copy”** button.
3. In the pop-up dialog, fill in the basic information for the new prompt:

   ![image](../images/5d3ee181-2b5a-483a-9b08-13f5083e6e67.png)

   The parameters for creating a prompt copy are as follows:

   | Parameter Name | Description | Default Value |
   |---------------|-------------|---------------|
   | Prompt Identifier | Unique identifier for the new prompt | original_identifier_copy |
   | Prompt Name | Display name of the new prompt | original_name_copy |
   | Description | Description of the new prompt | - |

4. Click the **“Create”** button to create a new prompt copy and automatically navigate to the editing page of the new prompt copy.

# Restore a Version

## Notes

- Restoring a version will overwrite the latest edited prompt. Please proceed with caution.

## Steps

1. Select the target version from the version history list.
2. Click the **“Restore to This Version”** button.

   ![image](../images/a4b87606-5a1f-4fda-83d2-e1e181a55b4e.png)

3. Click the **“Confirm Restore”** button to confirm restoring to the specified version.

   ![image](../images/8d3ea914-8257-41d3-b2b0-fcef0a65d733.png)
