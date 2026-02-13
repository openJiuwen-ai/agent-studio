# Overview

Prompt management is a complete prompt lifecycle management solution that helps you efficiently create, edit, debug, optimize, and manage prompts.

## Core Features

### 1. Flexible Message Template Construction

Supports four message types to build a complete conversational context:

- **System messages**: Define the AI’s role, behavioral guidelines, and output format.
- **User messages**: Simulate user input and provide task context.
- **Assistant messages**: Refine role guidance or provide historical conversation context.
- **Placeholder messages**: Reserve positions for dynamic content and inject real context at runtime.

### 2. Dual Template Engine Modes

- **Normal mode**: Simple variable substitution using the `{{variable_name}}` syntax, with automatic variable detection. Suitable for 80% of common scenarios.
- **Jinja2 mode**: A professional template engine that supports complex logic such as conditional statements and loops. Suitable for the remaining 20% of complex scenarios.

### 3. Multi-Instance Execution and Comparison Modes

- **Multi-instance execution**: Run multiple instances simultaneously to batch test and horizontally compare output quality, validating prompt stability.
- **Comparison mode**: Create baseline and control groups to compare the effects of different prompts or configurations under the same input, quickly identifying the optimal solution.

### 4. Intelligent Prompt Optimization

Provides multiple optimization methods to help you continuously improve prompt quality:

- **Quick optimization**: One-click global optimization of the entire prompt, with fast before-and-after comparison.
- **Feedback optimization**: Precisely optimize prompts locally or globally based on specific requirements. Supports three targeted optimization modes to improve prompts according to different needs:
  - Full-text feedback optimization: Apply global optimization to the entire prompt.
  - Selected-text feedback optimization: Optimize selected text fragments.
  - Insert feedback optimization: Insert optimized content at the cursor position.
- **Optimization based on debug results**: Optimize prompts based on AI responses from real debugging conversations through human evaluation.
- **Test-case-driven self-optimization**: Automatically iterate and optimize prompts using a test case set. The system compares actual outputs with expected outputs and optimizes prompts to reach the target accuracy.

## Core Concepts

- **Prompt**: Text instructions that guide AI models to generate specific outputs, composed of multiple messages to form a complete conversational context.
- **Message types**: System (role definition), User (user input), Assistant (refined guidance / historical context), Placeholder (dynamic content).
- **Variables**: Placeholders within prompts used to dynamically replace content at runtime, referenced using the `{{variable_name}}` syntax.
- **Template engines**: Normal mode (simple variable substitution) and Jinja2 mode (complex logic processing).
- **Self-optimization**: Automatic multi-round optimization based on test cases to continuously improve prompt accuracy.

## Related Documents

- [Quick Start](Quick Start.md): Quickly understand the prompt management workflow through a complete example
- [Writing Prompts](Writing Prompts.md): Learn how to create, write, and configure prompts
- [Debugging Prompts](Debugging Prompts.md): Master prompt testing and validation methods
- [Optimizing Prompts](Optimizing Prompts.md): Learn how to use various optimization methods
- [Managing Prompt Versions](Managing Prompt Versions.md): Understand the complete version management workflow
