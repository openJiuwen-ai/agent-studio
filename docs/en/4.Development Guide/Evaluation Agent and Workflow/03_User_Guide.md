# OpenJiuwen Evaluation System — Complete User Guide

> **Who this guide is for:** Anyone using OpenJiuwen who wants to measure how well their workflows and agents perform. No technical background required.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Core Concepts](#2-core-concepts)
3. [How the Evaluation System Works](#3-how-the-evaluation-system-works)
4. [Using Evaluation in the Frontend](#4-using-evaluation-in-the-frontend)
5. [Understanding Evaluation Results](#5-understanding-evaluation-results)
6. [Creating and Managing Evaluation Suites](#6-creating-and-managing-evaluation-suites)
7. [When and Why to Use Evaluation](#7-when-and-why-to-use-evaluation)
8. [Glossary](#8-glossary)
9. [FAQ](#9-faq)
10. [Additional Resources](#10-additional-resources)

---

## 1. Introduction

### What Is the Evaluation System?

The OpenJiuwen Evaluation System is a built-in testing and measurement tool for your AI workflows and agents. Think of it as a **quality control layer** that sits alongside your regular runs.

When you build a workflow or an agent — say, one that routes customer messages to the right department, or a research agent that produces a structured report — you naturally want to know: *Does it actually work? Does it work reliably? Does it still work after I change something?*

The evaluation system answers exactly those questions. It lets you:

- **Define test cases** describing inputs your workflow or agent should handle and what a correct response looks like
- **Run those test cases automatically** against any workflow or agent in your space
- **Measure reliability** by running each test multiple times and seeing how often it succeeds
- **Read detailed reports** showing exactly what went right, what went wrong, and why

Workflows and agents are **treated identically** by the evaluation system. Everything in this guide applies equally to both unless explicitly noted.

### Why Was It Added to OpenJiuwen?

AI systems — workflows, agents, language model chains — behave differently from traditional software. A regular program either does the right thing or crashes. An AI workflow or agent might give the right answer 80% of the time and a wrong answer 20% of the time, or it might work perfectly on one kind of input but fail on another.

This makes AI systems uniquely challenging to test. The evaluation system was built to handle this challenge by:

- **Treating reliability as a number**, not a yes/no question
- **Running tests multiple times** so you can see the true pass rate
- **Checking not just the final output** but also the internal behaviour (which tools were called, which branches were taken, how the workflow or agent was structured)
- **Providing pattern-aware checks** that understand the structural patterns OpenJiuwen workflows and agents can exhibit

### What Problems Does It Solve?

| Problem | Without Evaluation | With Evaluation |
|---|---|---|
| "Did my change break something?" | Manual testing, hope for the best | Run the evaluation suite and see immediately |
| "How reliable is this workflow or agent?" | Anecdotal, unclear | Measured pass rate with exact percentages |
| "Does it route correctly?" | Hard to verify systematically | Pattern-aware checks detect routing behaviour |
| "Which version of my workflow or agent is better?" | Guess based on a few tries | Compare run results side by side |
| "Is this ready for production?" | Gut feeling | Measurable quality gate |

### How It Helps You Build Better Workflows and Agents

The evaluation system turns the question "does this work?" into a measurement you can track over time. Each time you improve a workflow or agent, you can re-run the same suite of tests and compare the numbers. Over time you build up a reliable, testable system rather than a fragile one.

---

## 2. Core Concepts

This section explains every major concept in plain language. If you're new to evaluation systems, start here.

---

### 2.1 Evaluation Task

An **evaluation task** is a single test case. It's a description of one specific thing you want your workflow or agent to do, along with a way to check whether it did it correctly.

Think of it like a question on an exam:
- The **question** is the input you give the workflow or agent
- The **answer key** is what a correct response looks like
- The **grader** is the logic that compares the actual answer to the answer key

A task has:
- A **name** (e.g., "Route positive sentiment to support team")
- **Input data** — what to send to the workflow or agent (e.g., `{"message": "I love this product!"}`)
- **Expected output** — what a correct response looks like (e.g., `{"branch": "positive"}`)
- **Graders** — the rules used to decide if the run passed
- **Trials** — how many times to run this task independently (more on this below)
- A **difficulty** tag (Easy / Medium / Hard) to help you organise tasks — this is a display-only label and does not change how tasks are executed
- **Pattern checks** — zero or more structural patterns to validate. Each checked pattern (Routing, Chaining, Parallelisation, etc.) adds a pass/fail result based on whether the execution trace showed that structure. Leave all unchecked if you only care about the final output

---

### 2.2 Evaluation Suite

An **evaluation suite** is a collection of related tasks. You can think of it as a **test file** or a **test folder**.

For example:
- A suite called "Customer Support Routing" might contain 10 tasks that each test a different kind of incoming message
- A suite called "Research Agent Regression Tests" might contain all the important cases you've accumulated over time
- A suite called "Routing Pattern Benchmark" is a pre-built standard set of tasks designed to measure routing capability in general

You run an entire suite at once, against a specific workflow or agent, and get one consolidated report.

---

### 2.3 Trials

A **trial** is one single execution of a task. If a task has `trials: 5`, the system runs that task five separate times and records each result independently.

Why run more than once? Because AI systems are probabilistic. A language model might answer a question correctly 4 times out of 5, or 1 time out of 5. Running a single time gives you almost no useful information. Running multiple times reveals the true reliability.

**Key rule:** Each trial is completely independent — a fresh execution with a new conversation ID, no shared memory from previous trials.

---

### 2.4 Graders

A **grader** is the logic that decides whether one trial passed or failed. Every task has at least one grader, and tasks can have multiple graders that are combined together.

There are three types of graders:

#### Deterministic Graders

The simplest and fastest type. These apply a fixed rule to the output, with no AI involved. Available check types:

| Check Type | What It Does | Example |
|---|---|---|
| `output_check` | Compares the entire final output against an expected value or condition | `{"result": 6.0}` equals expected |
| `state_check` | Checks a single field inside the output by dot-separated path | `result` field equals `6.0` |
| `tool_call_check` | Verifies that specific tools were called during execution | `send_email` tool was called |
| `transcript_check` | Counts tool calls or component invocations and compares the count | At least 2 tool calls |
| `pattern_check` | Applies a regex pattern to the serialised execution trace | Output contains a specific ID format |

Deterministic graders are instant, free (no LLM call needed), and completely reproducible. Use them whenever you can express your quality criteria as a simple rule.

#### Model-Based Graders

These use a language model (an LLM) to judge the quality of the output. You provide a **rubric** — a description in plain language of what a good answer looks like — and the LLM scores the output against that rubric.

Example rubric: *"The response clearly identifies whether the customer is happy or unhappy, provides a routing decision, and explains the reasoning in one sentence."*

Model-based graders are more flexible — they can handle nuanced, subjective quality criteria that can't easily be expressed as rules. They are slower and cost LLM tokens, so use them for the parts of your evaluation that genuinely require human-like judgment.

#### Code-Based Graders

For advanced users who want complete control: you write a small Python function that receives the execution trace and expected output, and returns a pass/fail decision. This is useful for highly custom logic that doesn't fit either of the other grader types.

---

### 2.5 Pattern-Aware Evaluation

OpenJiuwen workflows and agents can be built using six structural patterns. The evaluation system understands these patterns and can automatically check whether execution used the correct pattern.

| Pattern | What It Means | Example |
|---|---|---|
| **Routing** | A conditional decision (IF component) was made and one path taken | Categorising a support ticket and sending it to the right team |
| **Chaining** | Two or more steps ran in sequence, each step's output feeding the next | Summarise → Translate → Format |
| **Parallelisation** | Multiple branches ran simultaneously and results were merged | Simultaneously checking grammar, tone, and factual accuracy |
| **Orchestrator–Worker** | A top-level workflow or agent delegated subtasks to sub-workflows or sub-agents | A research orchestrator calling specialist sub-agents |
| **Evaluator–Optimizer** | Execution ran in a loop, generating output and then evaluating/improving it | Write a draft → critique it → revise → repeat |
| **Memory Usage** | The workflow or agent read or wrote persistent state using variables | Accumulating results across multiple steps, remembering context |

Pattern checks verify that the *structure* of execution matched what you expected, not just the output. This is powerful because it lets you detect when a workflow or agent unexpectedly changed its structural behaviour — even if the output happened to look correct.

> **When to use pattern checks:** In the task editor, tick any structural patterns your workflow should exhibit. Each ticked pattern is validated against the execution trace and contributes a separate pass/fail result alongside your graders. You can tick multiple patterns simultaneously — for example, a workflow that routes and then chains steps can be checked for both Routing and Chaining. Leave all boxes unchecked when you only care about the final output — this skips pattern validation entirely.

---

### 2.6 pass@k

**pass@k** answers the question: *"If I ran this task k times, what's the probability that at least one of those runs would succeed?"*

It's expressed as a number from 0 to 100%.

Examples:
- **pass@1 = 60%** means: if you run the task once, there's a 60% chance it passes. This is the plain pass rate.
- **pass@3 = 90%** means: if you run the task three times, there's a 90% chance at least one of the three will pass. Even a workflow or agent that only works 60% of the time individually can achieve 90% with three tries.
- **pass@5 = 99%** — high confidence that at least one of five attempts succeeds.

**When to use it:** pass@k is the right metric when you can afford to run a task multiple times and you just need it to work at least once. For example, generating creative text where you run three times and pick the best result. pass@3 tells you how confident you can be that at least one will be good.

---

### 2.7 pass^k (pass-power-k)

**pass^k** answers the opposite question: *"If I ran this task k times, what's the probability that ALL of those runs would succeed?"*

Examples:
- **pass^1 = 60%** — same as plain pass rate.
- **pass^3 = 22%** — all three of three runs need to pass. Much harder to achieve.
- **pass^5 = 8%** — all five runs must pass.

**When to use it:** pass^k measures the strictest possible reliability. Use it when every single execution must succeed — for example, a workflow that sends a payment confirmation, or an agent that must always respond correctly. A high pass^k means highly reliable; a low pass^k but high pass@k means the workflow or agent works often but isn't perfectly consistent.

---

### 2.8 Execution Traces and Transcripts

When OpenJiuwen runs a workflow or agent, it records a detailed **execution trace** — a log of everything that happened:

- Which components were activated, and in what order
- Which tools were called, with what arguments, and what they returned
- Which conditional branches were taken
- How long each step took
- How many tokens were used
- Any error messages

The **Results & Traces** view in the evaluation UI lets you inspect this trace at the individual trial level, with a table showing each grader's verdict, the **expected value**, the **actual value returned**, and the comparison condition. You can see exactly where and why a trial went wrong.

---

### 2.9 Benchmarks vs Regression Tests

Two common ways to use the evaluation system:

**Benchmark suites** are standardised test collections that measure capability in absolute terms. OpenJiuwen ships **17 pre-built benchmark suites** in two groups: 10 domain benchmarks (real-world use cases such as customer support, RAG, code generation, SQL, translation, and more) and 7 pattern benchmarks (structural workflow patterns: Routing, Chaining, Parallelisation, Orchestrator–Worker, Evaluator–Optimizer, Memory Usage, plus the Calculator benchmark). These were designed to be objective, task-agnostic measures of capability. You run a benchmark to see how your workflow or agent scores on a standard scale.

**Regression test suites** are collections of test cases you build yourself, specific to your workflow or agent. They capture important scenarios from production use. Every time you change the workflow or agent, you re-run the regression suite to make sure you didn't break anything that was working before.

A good evaluation strategy uses both: benchmarks to understand general capability, regression tests to protect against breaking changes.

---

## 3. How the Evaluation System Works

This section explains the full process from start to finish, without technical detail.

---

### 3.1 How OpenJiuwen Runs a Workflow or Agent Normally

Normally, when you invoke a workflow or agent in OpenJiuwen:
1. You provide an input (a message, a document, some data)
2. The workflow or agent executes — components activate, tools are called, LLMs generate text
3. You receive a final output
4. The run ends

You see the output. You might see a brief execution log. But nothing systematically checks whether the output is correct.

---

### 3.2 What Changes When Running "With Evaluation"

When you run a workflow or agent *with evaluation*, the evaluation system:

1. Takes over the execution loop
2. Runs the workflow or agent not once but **N trials** for each task
3. After each trial, captures the complete execution trace
4. Passes that trace to each of the task's **graders**
5. Collects pass/fail and score from every grader
6. Stores all results in the database
7. Computes aggregate metrics (pass rate, pass@k, pass^k, latency, token usage)
8. Makes all results available in the Results & Traces view

The key difference is: the workflow or agent doesn't know it's being evaluated. It runs exactly as it would normally. The evaluation layer wraps around it without changing its behaviour.

---

### 3.3 How the Evaluation Harness Wraps Execution

The **evaluation harness** is the component that orchestrates everything. When you start a run, the harness:

1. Loads all tasks from the suite
2. Decides whether to run them sequentially or in parallel (based on your parallel setting)
3. For each task, runs the required number of trials
4. After each trial finishes, collects the execution trace
5. Sends the trace to each grader and collects their verdicts
6. Saves the trial result to the database
7. After all tasks complete, computes aggregate metrics for the whole run
8. Updates the run status to "Completed"

If any trial encounters an unexpected error, it's recorded as a failed trial with the error message captured and displayed in the Trace Viewer. The harness continues with the remaining trials rather than stopping the whole run.

---

### 3.4 How Graders Analyse the Results

After each trial:

- **Deterministic graders** apply their rules immediately and return a pass/fail result in milliseconds. The grader records the **expected value**, the **actual value** it found, and the **comparison condition** — all of which are visible in the Trace Viewer.
- **Model-based graders** send the output plus the rubric to an LLM and receive a structured verdict (passed true/false, score 0–1, feedback text)
- **Code-based graders** execute the custom Python function against the trace

If a task has multiple graders, a trial is considered **passed** only if every grader passes. The overall score is a weighted average of individual grader scores.

---

### 3.5 How Metrics Are Computed

After all trials for all tasks have completed, the system computes a comprehensive set of metrics:

**Pass / Fail**
- **Success rate** — fraction of total trials that passed
- **Error rate** — fraction of trials that raised an execution error (distinct from a graded failure)

**Sampling metrics**
- **pass@k** — probability that at least 1 of k picks passes, given c successes in n trials
- **pass^k** — probability that all k picks pass

**Score quality** (when graders return numeric scores)
- **Average score** — mean grader score across all trials
- **Score std** — standard deviation; low = consistent results, high = variable
- **Perfect score rate** — fraction of trials that scored exactly 1.0
- **Score distribution** — histogram: fraction of trials in each 20% score bucket

**Latency**
- **Average latency** — mean execution time per trial
- **Median latency (p50)** — typical latency, less affected by outliers than the mean
- **p95 latency** — worst-case latency for 95% of trials
- **Min / Max latency** — fastest and slowest individual trials

**Token usage**
- **Total tokens** — sum of prompt + completion tokens across all trials
- **Tokens per trial** — average prompt / completion / total tokens per individual trial

**Reliability** (multi-trial tasks only)
- **Flakiness** — mean standard deviation of pass/fail per unique task; `0` = perfectly consistent, `0.5` = maximally random

**Per-grader breakdown**
- Pass rate, average score, and trial count grouped by grader name — shows which specific criterion is causing failures

**Custom metrics** (if defined on the suite)
- User-written Python `compute(results)` functions run after aggregation and shown in the Metrics tab

---

### 3.6 How Results Are Stored and Displayed

Every trial result is stored in the database with its grader verdicts, score, latency, and token counts. This means:

- You can re-examine results later without re-running the evaluation
- You can compare different runs of the same suite (to track improvement over time)
- Results are tied to a specific workflow or agent version, so you know exactly what you tested
- The workflow or agent name is captured at run-start time, so the Runs table always shows a human-readable name — not just an ID — even if you rename or delete the workflow or agent later

---

## 4. Using Evaluation in the Frontend

This section walks through every interaction point in the UI step by step.

---

### 4.1 Navigating to the Evaluation Page

1. In the left sidebar, click **Evaluation** (or "Benchmarks") to open the evaluation page
2. The page has two main areas:
   - **Left panel** — the list of evaluation suites in your space
   - **Right panel** — the detail view for the selected suite, with three tabs: **Tasks**, **Runs**, **Results & Traces**
3. The **Runs** tab is shown by default when you select a suite

---

### 4.2 Creating an Evaluation Suite

**Option A — Create a blank suite:**

1. Click the **Add Suite** button on the Evaluation page
2. Select **Blank Suite** in the chooser dialog
3. Enter a **Suite Name** and optional **Description**
4. Click **Create** — your new suite appears in the left panel, with the Tasks tab open

**Option B — Add from Library (pre-built benchmarks and quick-start templates):**

1. Click **Add Suite** → select **Add from Library**
2. The library dialog opens with four tabs:
   - **Domain Benchmarks** *(selected by default)* — 10 production-ready suites covering real-world domains (customer support, RAG, code generation, SQL, translation, email assistant, and more). Each includes 8–16 tasks with pre-configured graders. Cards marked "Needs AI model" require a model to be configured in Settings → Models.
   - **Pattern Benchmarks** — 6 suites validating structural workflow patterns (Routing, Chaining, Parallelisation, Orchestrator–Worker, Evaluator–Optimizer, Memory Usage). All tasks and graders are pre-configured.
   - **Quick Start Templates** — 4 minimal 1–3 task templates as starting points. After adding you will need to customise inputs, expected outputs, and graders to match your workflow.
   - **Debug & Testing** — developer sanity-check tasks (echo test, calculator function call). Useful for verifying basic I/O and tool calls during development.
3. Click any card to select it. The **Suite Name** field at the bottom pre-fills with the suite's default name — you can rename it.
4. If the selected suite uses AI judge graders, a warning banner appears above the name field. Configure a model in **Settings → Models** before running.
5. Click **Add to My Suites** — the suite is created immediately and appears in the left panel.

> If you have no suites yet, the empty state shows an "Add from Library" shortcut that opens the same dialog.

---

### 4.3 Adding Tasks to a Suite

1. Click on any suite in the left panel to select it
2. Click the **Tasks** tab
3. Click **+ Add Task**
4. A dialog opens with fields for:

   | Field | Description |
   |---|---|
   | **Task Name** | Human-readable name shown in results |
   | **Description** | Optional explanation of what this task tests |
   | **Difficulty** | Easy / Medium / Hard — an organisational label only; does not affect execution |
   | **Trials** | How many independent times to run this task. Hover the ⓘ icon: more trials reveal reliability via pass@k statistics. |
   | **Input Data** | JSON sent to the workflow or agent as input (top-left of the editor) |
   | **Expected Output** | JSON describing what a correct result looks like (top-right of the editor) |
   | **Graders Config** | JSON array of grader configurations. Use the **Add Grader** button above the field to open the grader wizard, or edit the JSON directly. (bottom-left of the editor) |
   | **Pattern Checks** | Checkboxes for structural patterns to validate alongside graders. Each ticked pattern (Routing, Chaining, etc.) adds a pass/fail result. Multiple patterns can be selected. Leave all unchecked for output-only checking. (bottom-right of the editor) |

5. Click **Add Task** — the task appears in the task list

You can add as many tasks as you need. A typical suite has 5–20 tasks covering the main cases your workflow or agent should handle.

**Editing tasks:** Click the pencil icon next to any task to edit it. Changes are saved to the existing task record (no duplicate is created).

---

### 4.4 Running an Evaluation

Once your suite has at least one task:

1. Click the **▶ Run Evaluation** button (top right of the detail panel)
2. A dialog opens asking you to configure the run:

   **Target Type:** Choose whether to evaluate a **Workflow** or an **Agent**. Both are equally supported.

   **Select Workflow / Select Agent:** A dropdown shows all workflows or agents in your space. Select the one you want to evaluate.

   **Run tasks in parallel:** Toggle on to run all tasks simultaneously (faster, uses more resources). Leave off when starting out or if tasks have resource conflicts.

3. Click **Start Run**
4. The dialog closes. The **Runs** tab is shown (or will show) the new run with status **Pending**, transitioning to **Running**

The run happens in the background. You can navigate away and return later. Click **Refresh** on the Runs tab to update statuses.

---

### 4.5 Viewing Runs

The **Runs** tab lists all runs for the selected suite:

| Column | Description |
|---|---|
| **Run ID** | Shortened unique identifier for this run |
| **Target** | The workflow or agent name that was evaluated |
| **Status** | Pending → Running → Completed / Failed / Cancelled |
| **Success Rate** | Percentage of trials that passed (shown once completed) |
| **View Results** | Button to open the full results view for this run |
| **Delete** | Trash icon at the far right — removes this run and its results |

The **View Results** button shows:
- **"View Results"** — for completed runs
- **"Live Results"** — for runs currently in progress (status **Running**); click to watch results populate in real time

Only **Pending** runs (not yet started) have the button disabled.

The **Target** column shows the workflow or agent name — not a truncated ID — because the name is captured at the moment the run starts.

---

### 4.6 Viewing Results and Traces

1. In the **Runs** tab, click **View Results** (completed run) or **Live Results** (running) on any non-pending run
2. The **Results & Traces** tab opens automatically showing the full results for that run
3. The results view has four sub-tabs — **Overview**, **Metrics**, **Graders**, **Traces** — described in the sections below

If no run has been selected, the tab shows:
> *"Go to the Runs tab and click View Results on any run to view its results and execution traces."*

---

### 4.7 The Four Results Sub-Tabs

The results view is divided into four sub-tabs. Tabs that have no data for a run are hidden automatically.

---

#### Overview tab — stat cards

Shows high-level metric cards grouped by category. Each card shows a value and an icon coloured green / amber / red based on the result.

**Pass / Fail group**

| Card | What It Shows |
|---|---|
| **Success Rate** | Percentage of all trials that passed. ≥80% = green, 50–80% = amber, <50% = red. |
| **Passed** | Raw count of passing trials out of total. |
| **Failed** | Raw count of failing trials. |
| **Error Rate** | Shown only when errors occurred — fraction of trials that raised an execution exception. |

**Score group** (shown only when graders return numeric scores)

| Card | What It Shows |
|---|---|
| **Avg Score** | Mean grader score across all trials. Click **· details** to open the Score Distribution histogram showing how scores are spread across five 20% buckets. |
| **Perfect (1.0)** | Fraction of trials that achieved a perfect score of 1.0. |
| **Consistency** | Score standard deviation with a label — "high" (≤5%), "medium" (≤15%), "low" (>15%). |
| **Flakiness** | Mean std-dev of pass/fail per task. Only shown when tasks have multiple trials. `0.000` = perfectly consistent. |
| **Total Tokens** | Total LLM tokens (also shown here when score data is present). Hover for prompt/completion breakdown and avg per trial. |

**Latency group**

| Card | What It Shows |
|---|---|
| **Avg Latency** | Mean execution time per trial. Click **· details** to open the Latency Breakdown popup showing median, p95, min, max, and total. |
| **Total Tokens** | Total LLM tokens (shown here when no score data is present). |

---

#### Metrics tab — sampling and custom metrics

This tab appears when pass@k data or custom metrics are present.

**pass@k / pass^k table** — one row per k value (k=1, k=3, k=5 by default):

| Column | What It Shows |
|---|---|
| **k** | Number of independent samples |
| **pass@k** | Probability ≥1 of k samples passes |
| **pass^k** | Probability all k samples pass |
| **bar** | Visual bar for pass@k |

**Custom Metrics table** — shows the name and computed value (or an error message) for each user-defined aggregate metric.

---

#### Graders tab — per-grader breakdown

This tab appears when grader-level data exists. Shows one row per grader name:

| Column | What It Shows |
|---|---|
| **Grader** | Grader name as defined in the task configuration |
| **Pass rate** | Fraction of trials where this grader passed, colour-coded |
| **Avg score** | Mean score returned by this grader |
| **Trials** | Number of individual grader evaluations |
| **Pass rate (bar)** | Visual bar showing pass rate |

Use this tab to answer "which specific criterion is failing?" — a grader with a low pass rate while others are high tells you exactly which requirement the workflow or agent is not meeting.

---

### 4.8 Managing Custom Aggregate Metrics

Custom aggregate metrics let you define your own scoring logic in Python that runs after all trials complete. Unlike graders (which evaluate individual trials), custom metrics operate over the *entire set of results* and appear in the **Metrics** tab.

**Accessing the custom metrics editor:**

1. In the **Runs** tab, click **View Results** on any run for the suite
2. The **Results & Traces** view opens — click the **Custom Metrics** tab
3. The tab lists existing metrics with name, description, and code

**Adding a new metric:**

1. Click **+ New Metric** in the dialog
2. Enter:
   - **Name** — a valid Python identifier (e.g., `weighted_accuracy`)
   - **Description** (optional) — explains what the metric measures
   - **Code** — Python defining `def compute(results): ...`
3. Click **Save** — the metric is stored in the suite's configuration

The `compute(results)` function receives a list of trial result dicts with these fields:

| Field | Type | Description |
|---|---|---|
| `task_id` | str | Task identifier |
| `passed` | bool | Whether the trial passed |
| `score` | float | Aggregate score for the trial |
| `latency_ms` | int | Trial latency in milliseconds |
| `token_usage` | dict | `{prompt_tokens, completion_tokens, total_tokens}` |
| `error_message` | str | Error message if the trial failed with an exception |
| `grader_results` | list | Individual grader verdicts for this trial |

**Example:** compute the fraction of trials that both passed and scored above 0.8:

```python
def compute(results):
    if not results:
        return 0.0
    high_quality = sum(
        1 for r in results
        if r.get("passed") and r.get("score", 0) >= 0.8
    )
    return high_quality / len(results)
```

Custom metrics are recomputed every time you view results for that suite, so you can add or edit them without re-running the evaluation.

---

### 4.9 Inspecting Per-Task Results (Trace Viewer)

Below the summary metrics, the **Trace Viewer** shows results broken down by task.

Each task section shows:
- The task name (with task ID in parentheses if different)
- How many trials passed (e.g., "2 / 3 passed")
- Individual trial results as expandable accordion rows

For each trial, the **collapsed summary row** shows:
- **Pass / Fail** — green checkmark (✓) or red X (✗)
- **N/M graders passed** — how many of the graders passed
- **Latency** — how long this trial took (e.g., `1.08s`)
- **Token usage** — how many tokens were consumed (if available)
- **Trace ID** — shortened identifier for this specific execution

**Expanding a trial row** reveals the full detail:

1. **Execution Error** (if the workflow or agent threw an exception) — shown as a red banner with the full error message
2. **Workflow Output** — the actual value returned by the workflow or agent, highlighted green on pass or red on fail
3. **Grader Details table** — one row per grader:
   | Column | Description |
   |---|---|
   | ✓/✗ | Pass or fail for this grader |
   | **Grader** | Name, type (deterministic / model_based / code_based), and check type |
   | **Score** | 0–100% score from this grader |
   | **Expected / Actual / Details** | The expected value, the actual value found, the comparison condition, and any additional details (missing tools, matched pattern, etc.) |
4. **Token usage breakdown** — per-category token counts if available

This is the primary place to understand *why* a trial failed. The Grader Details table shows you exactly what was expected, what the workflow or agent actually returned, and how they were compared.

---

### 4.10 Understanding the Trace View Details

When a deterministic grader fails, the details row shows:

```
Expected:  {"result": 6.0}
Actual:    null
Condition: eq
```

This tells you precisely: the grader expected the output to contain `result: 6.0`, but the workflow returned nothing (or something different). Common causes:
- **`actual: null`** — the workflow returned no output at all (execution error, or output format mismatch)
- **`actual` has the wrong type** — e.g., `"6"` (string) instead of `6.0` (number)
- **`actual` has the right value but wrong field name** — e.g., `sum` instead of `result`

When a model-based grader fails, the feedback field explains in plain language what was wrong.

When a code-based grader fails, the error message shows any exception thrown by the Python grading function.

---

### 4.11 Browsing and Importing Pre-built Benchmark Suites

OpenJiuwen ships **17 pre-built benchmark suites** in two groups.

**Domain Benchmarks (10 suites)** — real-world use cases:

| Benchmark | What It Tests | Notes |
|---|---|---|
| **Customer Support** | Intent routing, escalation detection, tone checking | AI judge graders |
| **RAG System** | Retrieval accuracy, citation quality, groundedness | AI judge graders |
| **Code Generation** | Syntax correctness, test passing, style compliance | AI judge graders |
| **Content Moderation** | Harmful content detection, false-positive rate | AI judge graders |
| **Data Extraction** | JSON schema compliance, field extraction accuracy | AI judge graders |
| **Research Agent** | Source coverage, claim accuracy, report structure | AI judge graders |
| **Translation Agent** | Translation quality, terminology consistency, length ratio | AI judge graders |
| **Email Assistant** | Email tone, action items, brevity, reply relevance | AI judge graders |
| **SQL Agent** | Query correctness, safe SQL, performance hints | AI judge graders |
| **Conversational Agent** | Coherence, context retention, helpfulness, safety | AI judge graders |

**Pattern Benchmarks (7 suites)** — structural workflow patterns, all with pre-configured deterministic graders:

| Benchmark | What It Tests | Tasks |
|---|---|---|
| **Routing Benchmark** | Conditional branching: positive/negative routing, threshold decisions | 3 |
| **Chaining Benchmark** | Sequential pipelines: summarise → translate, extract → format | 3 |
| **Parallelisation Benchmark** | Concurrent branches: parallel analysis, fan-out/fan-in patterns | 3 |
| **Orchestrator–Worker Benchmark** | Sub-workflow/agent delegation: multi-section research, multi-aspect review | 3 |
| **Evaluator–Optimizer Benchmark** | Improvement loops: essay refinement, code generation with test cycles | 3 |
| **Memory Usage Benchmark** | State management: conversation context, accumulating results | 3 |
| **Calculator Benchmark** | Arithmetic function: `add(a, b) → {result}` with integers, floats, negatives, and edge cases | 6 |

To import a benchmark:
1. Click **Add Suite** on the Evaluation page and choose **Add from Library**
2. The library dialog opens — select the **Domain Benchmarks** or **Pattern Benchmarks** tab
3. Click a suite card to select it. The Suite Name field pre-fills; rename it if you wish
4. If the suite uses AI judge graders, a warning banner appears — configure a model in **Settings → Models** before running
5. Click **Add to My Suites** — the suite is created immediately with all tasks
6. The dialog closes and the new suite appears in the left panel, selected and ready to run

---

## 5. Understanding Evaluation Results

---

### 5.1 What "Pass" and "Fail" Mean

A trial **passes** when every grader in the task returns a passing verdict. A trial **fails** when at least one grader fails.

What counts as "correct" is defined by your graders. If your graders are strict (e.g., exact output matching), even slightly different phrasing might cause a failure. If your graders are lenient (e.g., "the output must not be empty"), more variation is acceptable.

**Key insight:** A failed trial doesn't always mean the workflow or agent is broken. It might mean:
- Your grader is too strict for the natural variation in LLM outputs
- The task's expected output doesn't cover all acceptable responses
- The workflow or agent occasionally takes a different but still valid path

Use failed trials as an invitation to investigate, not as an automatic indication of a bug.

---

### 5.2 How to Interpret Success Rate

| Success Rate | Interpretation |
|---|---|
| **90–100%** | Excellent. Highly reliable. |
| **70–90%** | Good. Minor improvement may be worthwhile. |
| **50–70%** | Fair. Works more often than not, but reliability should be improved. |
| **30–50%** | Poor. Fails nearly half the time. Needs investigation. |
| **<30%** | Very poor. Fundamentally not working on these tasks. |

The right threshold depends on the use case. A workflow or agent that sends emails must be near 100%. One that generates creative inspiration can be acceptable at 60%.

---

### 5.3 How to Interpret pass@k and pass^k

Look at the pass@k table and ask yourself two questions:

**"Can I afford to try multiple times?"**
- If yes → look at **pass@k** for your k value. A workflow or agent with pass@3 = 90% means you can reliably get a good result if you try three times.
- If no (every single execution must succeed) → look at **pass^k**. A workflow or agent with pass^3 = 50% means only half of the time will all three trials succeed — probably not reliable enough.

**Practical example:**
- Success rate: 70%
- pass@3: 97% — if you can try 3 times, you'll almost certainly get a good result
- pass^3: 34% — if you need all 3 to be right simultaneously, only a 1-in-3 chance

This tells you: the workflow or agent is useful but not deterministic. Design your system to be able to retry if needed.

---

### 5.4 How to Interpret Score Quality Metrics

When graders return numeric scores (0.0–1.0), the Overview tab shows additional cards beyond pass/fail.

**Avg Score**

The mean score across all trials. Think of it as "how correct is the workflow or agent on average?", not just "does it pass or fail?". A workflow with 60% success rate but 0.85 average score is usually better than one with 60% success rate and 0.55 average score — the failures in the first case are near-misses; in the second they're complete misses.

**Perfect Score Rate**

The fraction of trials that achieved score = 1.0. Distinct from success rate because a trial can pass (score ≥ the grader's `passing_score` threshold) without being perfect. If your success rate and perfect score rate are both high, your workflow is not just passing — it's excelling.

**Consistency (Score Std)**

The standard deviation of scores across trials:
- **High (std ≤ 5%)** — the workflow or agent gives very similar quality every time
- **Medium (std 5–15%)** — moderate variation; acceptable for most uses
- **Low (std > 15%)** — large swings in quality between runs; the workflow is unpredictable

**Flakiness**

Measures how often the same input gets different pass/fail outcomes across trials:
- `0.000` — perfectly consistent: if it passes once, it passes every time
- `0.1–0.2` — mild flakiness; occasional inconsistency
- `> 0.3` — high flakiness; the workflow or agent is significantly non-deterministic

Flakiness is only meaningful when tasks have more than one trial (`trials ≥ 2`). It's displayed as `—` or hidden for single-trial tasks.

**Score Distribution (· details popup)**

Click **· details** on the Avg Score card to see a histogram of scores. Five colour-coded bars show what fraction of trials fell in each 20% bucket:
- A spike in the 80–100% bucket alongside a spike in 0–20% = bimodal distribution — the workflow sometimes nails it and sometimes completely fails
- A smooth distribution peaking in 60–80% = consistently good but rarely perfect
- Most mass in 0–20% = fundamentally not working

---

### 5.5 How to Read Grader Outputs

The Grader Details table in the Trace Viewer shows one row per grader. For each grader:

- **✓/✗** — whether this grader passed or failed
- **Score (0–100%)** — for deterministic graders this is always 0% or 100%; for model-based graders it reflects the LLM's quality score
- **Expected** — what the grader expected to find
- **Actual** — what the workflow or agent actually returned (highlighted red on mismatch)
- **Condition** — the comparison rule (`eq`, `contains`, `is_not_empty`, etc.)

**Tips:**
- If `actual` is `null` or `—`, the workflow or agent returned no output or the specific field didn't exist
- If a model-based grader fails, look for a `feedback` field in the details — it explains in plain language what was wrong
- If a code-based grader fails, look for an `error` field showing any exception from the Python function

---

### 5.6 How to Understand Pattern Checks

A pattern check fails when the execution trace didn't contain the expected structural pattern.

Common causes of pattern check failures:

| Pattern | Common Failure Cause |
|---|---|
| Routing | Workflow or agent didn't use an IF component, or took the wrong branch |
| Chaining | Only one step ran instead of multiple sequential steps |
| Parallelisation | Components ran sequentially instead of in parallel |
| Orchestrator–Worker | Sub-workflow or sub-agent was not invoked |
| Evaluator–Optimizer | Loop didn't execute, or ran only once |
| Memory Usage | Variable was not read or written |

A pattern check failure is a strong signal that the structure is wrong, not just the output. This is useful for catching architectural regressions — cases where refactoring accidentally changed how a workflow or agent is structured.

> Remember: if you leave all Pattern Checks unchecked on a task, no pattern check is performed — the task only evaluates the final output. This is the right choice for tasks where you don't care about internal structure.

---

### 5.7 How to Read the Execution Trace

When a trial fails and you need to dig deeper, the grader details in the expanded trial row are the first place to look. The **Actual** column tells you exactly what value the workflow or agent returned.

For deeper investigation:

1. **The execution error banner** (red) — if present, the workflow or agent threw an exception. The full error message is shown.
2. **The grader details table** — shows the comparison between what was expected and what was returned, for every grader.
3. **The trace ID** — a unique identifier you can cross-reference with server logs for low-level debugging.

Work backwards from the failure point. Often the root cause is several steps before the output was wrong.

---

### 5.8 How to Identify Regressions

A **regression** is when something that was working before stops working after a change.

To detect regressions:
1. Run your evaluation suite before making changes → note the results
2. Make your changes
3. Run the evaluation suite again
4. Compare the success rates in the Runs tab

If the success rate dropped, the Trace Viewer shows you which specific tasks now fail that didn't before. Look at those task traces to understand the impact of your change.

---

### 5.9 How to Compare Runs

The Runs tab lists all runs for the selected suite in chronological order. Each row shows the success rate and status. You can see at a glance whether recent runs are better or worse than earlier ones.

To do a deeper comparison:
1. Open the results for Run A (click its chart icon) and note which tasks failed
2. Navigate back to Runs, open Run B, note which tasks failed
3. The difference tells you exactly what your changes fixed or broke

---

### 5.10 The Reliability Tab — Holistic Reliability Profile

The **Reliability** tab is a deep diagnostic tool that goes beyond simple pass/fail rates. It computes a structured reliability profile across four engineering dimensions, grounded in academic research on AI agent dependability.

> **Methodology basis**: The metrics implement the framework from *"Towards a Science of AI Agent Reliability"* ([arXiv:2602.16666](https://arxiv.org/abs/2602.16666)). The paper argues that a single accuracy number is insufficient to assess whether an agent is production-ready, and proposes a holistic profile grounded in safety-critical systems engineering.

---

#### Overall Reliability Score (ℛ)

The top-level score is a **weighted geometric mean** of three primary dimensions:

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| Consistency | 40% | Does the agent produce the same result each time? |
| Robustness | 35% | Does it hold up under stress (faults, environment changes)? |
| Predictability | 25% | Is its confidence calibrated with its actual accuracy? |

Safety is evaluated separately as a **hard constraint** — it is not blended into the overall score because any safety violation is categorically different from a quality failure.

**Score thresholds:**

| Score | Meaning |
|-------|---------|
| ≥ 0.8 | Excellent — production-ready |
| 0.5–0.8 | Moderate — investigate failing dimensions |
| < 0.5 | Poor — not production-ready |

---

#### Consistency Dimension (ℛCon)

Measures how stable the agent is across repeated runs of the same input. Four sub-metrics:

**Outcome Consistency (Cout)**
Fraction of trials that share the same pass/fail outcome. Example: if 8 out of 10 trials pass, Cout ≈ 0.96. A score below 0.8 means the agent's pass/fail behaviour is erratic for this input.

**Trajectory Distribution (Ctraj-d)**
Compares the distribution of tool calls across trials using Jensen-Shannon divergence. Answers: "Does the agent use the same tools at the same rates?" High scores mean tool usage patterns are stable even if the exact order varies.

**Trajectory Sequence (Ctraj-s)**
Measures Longest Common Subsequence (LCS) similarity in tool call order. Unlike Ctraj-d, this cares about *sequence* — if the agent calls tools A, B, C every run (in that order), Ctraj-s is high. If sometimes it calls B, A, C, it will be lower.

**Resource Consistency (Cres)**
Uses the Coefficient of Variation (CV = std/mean) of latency and token usage. Measures: "Does the agent consistently use the same amount of time and tokens?" High variance means the agent has unpredictable resource usage, which complicates capacity planning.

---

#### Robustness Dimension (ℛRob)

Measures how well the agent maintains performance when conditions are not ideal. Three sub-metrics, each computed as `accuracy_perturbed / accuracy_nominal` (capped at 1.0):

**Fault Injection Robustness (Rfault)**
Tests the agent when tools fail with synthetic errors. A score of 1.0 means the agent handles tool failures as well as it handles normal conditions. A low score means tool errors cause cascading failures.

**Environment Robustness (Renv)**
Tests the agent when environmental inputs (e.g., context, available data) are changed. Measures adaptation to different but valid operating conditions.

**Prompt Robustness (Rprompt)**
Tests the agent with paraphrased versions of the same input. A high score means the agent is not "overfitted" to specific prompt phrasings and generalises well.

> **Note**: If perturbation data is not available (you didn't run trials with faults or variations), these sub-metrics will show `—`. They require multiple run configurations.

---

#### Predictability Dimension (ℛPred)

Measures whether the agent's confidence signals are reliable. Three sub-metrics based on calibration theory:

**Calibration (Pcal — 1 − ECE)**
Expected Calibration Error (ECE) measures how well confidence aligns with accuracy. If the agent says "I'm 80% confident" on a set of answers, it should be correct 80% of the time. Perfect calibration = Pcal of 1.0.

**AUROC (Discrimination)**
Area Under the ROC Curve — separates correct outcomes from incorrect ones using the agent's confidence score. 0.5 = random (confidence carries no information), 1.0 = perfect discrimination. A low AUROC means confidence scores are not useful predictors of correctness.

**Brier Score (Pbrier — 1 − BrierScore)**
The Brier Score (`mean((confidence − correct)²)`) is a proper scoring rule. Lower is better; the display inverts it so higher is better (Pbrier = 1 − BrierScore). Combines calibration and discrimination into a single number.

---

#### Safety Dimension (ℛSaf)

Tracked separately — not blended into the overall reliability score. Three metrics:

**Compliance Rate (Scomp)**
Fraction of trials with *zero* safety violations. A compliance rate below 1.0 means some trials triggered a constraint.

**Harm Avoidance (Sharm)**
Accounts for violation severity: `1 − mean_severity`, where severity weights are: low = 0.25, medium = 0.5, high = 1.0. A Sharm of 1.0 means no harm at any severity level.

**Violation Rate**
The percentage of trials that triggered at least one safety constraint. This should be 0% in any production system.

---

#### When to Use the Reliability Tab

The Reliability tab is most useful when:
- **Before production deployment**: Use as a checklist. All four dimensions should be satisfactory.
- **Comparing two agent versions**: The per-dimension breakdown shows exactly which engineering property improved or degraded.
- **Diagnosing flaky behaviour**: High Cout but low Ctraj-d suggests different tool paths reach the same answer — fine for correctness, but signals inconsistent decision-making.
- **After a prompt change**: Check Rprompt to verify the change didn't make the agent brittle to phrasing variations.

> The tab requires at least 3 trials per task to produce meaningful statistics. With only 1 trial, most metrics cannot be computed.

---

## 6. Creating and Managing Evaluation Suites

---

### 6.1 What an Evaluation Suite Is

A suite is a named container for related tasks. It keeps your tests organised. One suite might represent:

- "All tests for the customer support router workflow"
- "Regression tests for the research agent"
- "Standard routing benchmark"
- "Weekly performance check for the order-processing workflow"

Suites belong to a **space** — if your organisation uses multiple spaces, each space manages its own suites separately.

---

### 6.2 How Suites Are Organised

Each suite has:
- A unique ID (automatically assigned)
- A name and description (you set these)
- A list of tasks
- A history of all runs performed against it

When you run a suite, you choose which workflow or agent to run it against. This means the same suite can be used to compare:
- Different workflows solving the same problem
- The same workflow at different points in time
- Different agents with different models or prompts
- A workflow vs an agent doing equivalent tasks

---

### 6.3 Benchmark Suites vs Regression Suites

**Pre-built Benchmark Suites** come with OpenJiuwen:
- Objective and standardised
- Test abstract patterns, not your specific workflow or agent
- Help you understand how well your system handles common structural patterns
- Not customised to your use case

**Custom Regression Suites** you build yourself:
- Test your specific workflow's or agent's specific capabilities
- Customised to your exact input/output format
- Grow over time as you add more test cases
- Protect against regressions in your specific implementation

Most mature workflows and agents should have both: a benchmark run occasionally to see overall capability, and a regression suite run on every significant change.

---

### 6.4 How Tasks Are Defined

Every task is defined by answering a few simple questions:

1. **What input should I send?** Describe the input as a JSON object matching what your workflow or agent expects.

2. **What does a correct response look like?** Describe the expected output as a JSON object. This is the "answer key."

3. **How do I check correctness?** Choose one or more graders:
   - For simple field/value checks → use a Deterministic grader with `state_check` (single field) or `output_check` (full output)
   - For nuanced quality checks → use a Model-Based grader with a rubric
   - For complex custom logic → use a Code-Based grader

4. **How many times should I run it?** Choose trials:
   - 1 trial: smoke test, fastest
   - 3 trials: good balance for most tests — enables meaningful pass@k metrics
   - 5–10 trials: accurate reliability measurement for important or probabilistic tasks

5. **Does the structure matter?** Tick one or more Pattern Checks if you want to validate that the execution exhibited specific structural patterns (Routing, Chaining, etc.). Each ticked pattern adds a separate pass/fail result. Leave all boxes unchecked if you only care about the final output.

6. **How hard is this task?** Set Difficulty (Easy / Medium / Hard) as an organisational label. This doesn't change execution — it's for your own reference and reporting.

---

### 6.5 Grader Configuration Examples

**Simplest possible task (no graders, just runs):**
```json
Input Data:  {"message": "Hello"}
Expected:    {}
Graders:     []
```

**Check a specific field in the output:**
```json
Graders: [
  {
    "name": "result_equals_6",
    "grader_type": 0,
    "config": {
      "check_type": "state_check",
      "path": "result",
      "expected_value": 6.0,
      "condition": "eq"
    }
  }
]
```

**Check the full output is not empty:**
```json
Graders: [
  {
    "name": "output_not_empty",
    "grader_type": 0,
    "config": {
      "check_type": "output_check",
      "condition": "is_not_empty",
      "expected_value": null
    }
  }
]
```

**Check the output contains a keyword:**
```json
Graders: [
  {
    "name": "contains_order_reference",
    "grader_type": 0,
    "config": {
      "check_type": "output_check",
      "condition": "contains",
      "expected_value": "order"
    }
  }
]
```

**LLM quality check:**
```json
Graders: [
  {
    "name": "response_quality",
    "grader_type": 1,
    "config": {
      "model_id": "your-model-id",
      "rubric": "The response is helpful, acknowledges the customer's issue, and provides a clear next step.",
      "passing_score": 0.7
    }
  }
]
```

**Custom Python grader:**
```json
Graders: [
  {
    "name": "result_is_positive",
    "grader_type": 2,
    "config": {
      "code": "def grade(trace, expected):\n    output = trace.get('final_output') or {}\n    result = output.get('result')\n    passed = result is not None and result > 0\n    return {'passed': passed, 'score': 1.0 if passed else 0.0}",
      "function_name": "grade"
    }
  }
]
```

---

### 6.6 How to Choose Which Suite to Run

Ask yourself: what question am I trying to answer?

- **"Is this workflow or agent working at all?"** → Run a basic smoke-test suite with a few representative tasks
- **"Did my change break anything?"** → Run your regression suite
- **"How does this compare to a previous version?"** → Run the same suite against both versions
- **"Is this ready for production?"** → Run both your regression suite and the relevant benchmark suite
- **"Why is my routing workflow sometimes wrong?"** → Run the Routing Benchmark to see detailed routing-specific results
- **"Does my calculator workflow handle all edge cases?"** → Run the Calculator Benchmark

---

## 7. When and Why to Use Evaluation

---

### 7.1 Testing New Workflows and Agents

When you've just built a workflow or agent, run a quick evaluation before deploying it. Even 5–10 test cases will reveal obvious problems that would otherwise reach production. Focus on:
- The most common inputs your workflow or agent will receive
- Edge cases you're uncertain about
- Inputs that previously caused problems

---

### 7.2 Comparing Workflow Versions

If you've updated a workflow — changed its structure, its prompts, its tools, or its routing logic — evaluation lets you compare before and after objectively. Run the same suite against Workflow v1 and Workflow v2, then compare success rates and pattern adherence side by side. Numbers don't lie.

---

### 7.3 Comparing Agent Versions

If you've updated an agent — changed its system prompt, its model, its tool set, or its memory configuration — evaluation lets you compare the versions objectively. Run the same suite against Agent v1 and Agent v2, then compare the success rates. This is the most reliable way to decide whether a change actually improved performance.

---

### 7.4 Detecting Regressions

Every time you make a non-trivial change to a workflow or agent, run the regression suite. This is the single most valuable habit you can develop. Regressions are common in AI systems because small changes to prompts or structure can have unexpected downstream effects. Catching them early, before deployment, saves time and prevents user-facing failures.

---

### 7.5 Validating Routing Logic

Routing workflows and agents are particularly important to test because they determine which path a message takes. A routing error can send a complaint to the sales team instead of the support team. Use the evaluation system to test every routing category with multiple examples. The pattern check verifies that the IF component was actually used, and the output check verifies that the right branch was selected.

---

### 7.6 Ensuring Parallel Branches Behave Correctly

Parallelisation workflows are tricky because errors in one branch might be masked by successful results in other branches. The evaluation system's pattern check for parallelisation verifies that branches actually ran in parallel (not sequentially), and you can add output checks to verify that results from all branches are correctly merged.

---

### 7.7 Checking Orchestrator–Worker Decomposition

When a workflow or agent delegates to sub-workflows or sub-agents, it's important to verify that delegation actually happens and that sub-tasks receive the right inputs. The orchestrator–worker pattern check confirms the sub-workflow or sub-agent invocation, and tool-call checks can verify the inputs passed to each sub-task.

---

### 7.8 Testing Deterministic Functions

For workflows or agents that call deterministic tools (arithmetic, data retrieval, format conversion), the Calculator Benchmark pattern is ideal: define exact input/output pairs and use `state_check` with `condition: "eq"` to verify precise values. This gives you 100% reliable pass/fail results that don't depend on LLM variability.

---

### 7.9 Improving Reliability Over Time

Don't think of evaluation as a one-time check. Build up a regression suite as you work:
- Every time you encounter a bug in production, add a test case for it
- Every time you make a change, run the suite and fix any failures before deploying
- Over time, your suite grows into a comprehensive safety net

This is how professional software teams use testing — the discipline pays off as the system becomes more complex.

---

## 8. Glossary

| Term | Definition |
|---|---|
| **Agent** | An AI-powered entity in OpenJiuwen that can take actions, use tools, and maintain a conversation. Evaluated identically to workflows. |
| **Avg Score** | The mean grader score (0.0–1.0) across all trials. Measures overall quality, not just binary pass/fail. |
| **Benchmark** | A standardised set of test cases designed to measure capability in absolute terms. Compare to regression tests. |
| **Code-Based Grader** | A grader that runs a custom Python function to evaluate trial output. For advanced, custom evaluation logic. |
| **Consistency** | The inverse of score std dev — a "Consistency" card label of "high" means the agent scores similarly every time. |
| **Custom Aggregate Metric** | A user-defined Python function (`def compute(results)`) that runs after all trials complete and returns a suite-level metric. Stored in suite `config.custom_metrics`. |
| **Deterministic Grader** | A grader that applies a fixed rule (contains, equals, state_check, tool_call_check, etc.) with no LLM call. Fast and reproducible. |
| **Difficulty** | An organisational label (Easy / Medium / Hard) on a task. Does not affect execution — used for filtering and reporting only. |
| **Error Rate** | The fraction of trials that raised an execution exception (distinct from a graded failure). |
| **Evaluation Harness** | The internal component that orchestrates trial execution, collects traces, runs graders, and computes metrics. Uses weighted aggregation for multi-grader scores. |
| **Evaluation Run** | One complete execution of an evaluation suite against a specific workflow or agent. |
| **Evaluation Suite** | A collection of related evaluation tasks, organised under a name. May include suite-level custom metric definitions in its `config`. |
| **Execution Trace** | A detailed log of everything that happened during one trial — components, tools, LLM calls, branch decisions. |
| **Flakiness** | Mean standard deviation of pass/fail per unique task across trials. `0` = perfectly consistent, `0.5` = maximally random. Only meaningful for multi-trial tasks. |
| **Grader** | A component that evaluates the output of one trial and returns passed/failed plus a quality score. |
| **Graders Tab** | The results sub-tab showing per-grader pass rate, avg score, and trial count — useful for diagnosing which specific criterion is failing. |
| **Metrics Tab** | The results sub-tab showing pass@k / pass^k sampling tables and custom aggregate metrics. |
| **Model-Based Grader** | A grader that uses an LLM to assess output quality against a rubric. For nuanced, subjective evaluation. |
| **Overview Tab** | The results sub-tab showing high-level stat cards (pass/fail, score quality, latency, tokens). |
| **p95 Latency** | The 95th percentile latency — 95% of trials completed faster than this value. A useful worst-case indicator. |
| **pass@k** | The probability that at least 1 of k independent trial attempts will pass, given the observed pass rate. |
| **pass^k** | The probability that all k independent trial attempts will pass, given the observed pass rate. |
| **Pattern Checks** | Zero or more structural patterns selected as checkboxes on a task. Each ticked pattern (Routing, Chaining, Parallelisation, Orchestrator–Worker, Evaluator–Optimizer, Memory Usage) adds a separate pass/fail result based on execution trace analysis. Multiple patterns can be selected simultaneously; leaving all unchecked skips pattern validation entirely. |
| **Pattern Check** | An evaluation that verifies the execution trace exhibits the expected structural pattern. |
| **Perfect Score Rate** | The fraction of trials that achieved a score of exactly 1.0. Distinct from success rate — a trial can pass without being perfect. |
| **Per-Grader Breakdown** | Aggregate statistics (pass rate, avg score, count) computed separately for each named grader across all trials. |
| **Regression** | When something that was working correctly stops working after a change. |
| **Regression Test Suite** | A collection of test cases built for a specific workflow or agent to detect regressions. |
| **Rubric** | A plain-language description of what a good output looks like, used by model-based graders. |
| **Score** | A number from 0.0 to 1.0 (displayed as 0–100%) representing the quality of a trial according to a grader. |
| **Score Distribution** | A histogram showing what fraction of trials fell into each 20% score bucket. Accessed via the "· details" link on the Avg Score card. |
| **Space** | An organisational unit in OpenJiuwen — suites, workflows, and agents belong to a space. |
| **state_check** | A deterministic grader check type that reads a single field from the output by dot-separated path and compares it to an expected value. |
| **Success Rate** | The fraction of all trials that passed, expressed as a percentage. |
| **Task** | A single test case: an input, expected output, trials count, and graders. The unit of evaluation. |
| **Tokens Per Trial** | The average number of LLM tokens consumed per individual trial. Shown in the token card tooltip. |
| **Traces Tab** | The results sub-tab showing per-trial expandable detail: grader verdicts, actual output, error messages. |
| **Transcript** | See *Execution Trace*. |
| **Trial** | One single independent execution of a task. A task can have multiple trials. |
| **Weighted Aggregation** | The method used to combine scores from multiple graders: `Σ(score_i × weight_i) / Σ(weight_i)`. Graders with higher weight contribute more to the final score. |
| **Workflow** | A structured sequence or graph of components in OpenJiuwen that processes inputs and produces outputs. Evaluated identically to agents. |

---

## 9. FAQ

**Q: Do I need to write code to use the evaluation system?**

No. The core features — creating suites, loading benchmarks, adding tasks, running evaluations, viewing results — are all available through the UI with no coding required. Code-based graders are optional and only needed for very advanced custom evaluation logic.

---

**Q: Can I evaluate a workflow and an agent with the same suite?**

Yes. The same suite of tasks can be run against any workflow or any agent. When you click "Run Evaluation", simply choose "Workflow" or "Agent" and select the target from the dropdown. This makes it easy to compare a workflow implementation to an agent implementation of the same problem.

---

**Q: How many trials should I use?**

For most cases, 3 trials is a good starting point — enough to get meaningful pass@k statistics without being slow. Use 5 for important test cases where you want more confidence. Use 1 for smoke tests where you just want to verify basic functionality. Avoid using 1 for reliability testing, as a single pass or fail is not meaningful for probabilistic AI systems.

---

**Q: My success rate is 70%. Is that good or bad?**

It depends on the workflow or agent. A creative writing assistant at 70% is probably fine. A financial calculation workflow at 70% is not acceptable. Set your own quality bar based on the consequences of failure in your use case.

---

**Q: What's the difference between pass@k and success rate?**

Success rate is the raw fraction of all trials that passed. pass@1 is the same number. pass@k (for k > 1) models the probability that *at least one* of k runs would succeed. It's always higher than success rate for the same workflow or agent, because multiple chances increase the probability of at least one success.

---

**Q: Can I run evaluation in the background while doing other things?**

Yes. When you click Start Run, the evaluation runs completely in the background. You can navigate away, close the tab, or do other work. The results will be waiting for you when you return. Click **Refresh** on the Runs tab to see the latest status. The View Results button (chart icon) is enabled as soon as the run starts — you can watch partial results appear in real time.

---

**Q: What happens if a trial crashes with an error?**

The trial is recorded as failed, and the full error message is captured and displayed in the Trace Viewer as a red error banner when you expand that trial row. The evaluation continues with the remaining trials — one error doesn't stop the whole run. This lets you see how often a workflow or agent encounters errors, which is itself useful information.

---

**Q: How do I know if a pattern check is appropriate for my task?**

Use a pattern check when you care about *how* the workflow or agent achieved its result, not just *what* the result is. For example: if you want to confirm that a routing workflow actually used conditional branching (not just guessing), tick the Routing pattern check. You can tick multiple patterns simultaneously — for example, both Routing and Chaining for a workflow that routes and then chains steps. If you only care about the final output quality, leave all Pattern Checks unchecked — this skips structure validation entirely.

---

**Q: Why does the Trace Viewer say "actual: null" for my grader?**

`actual: null` (or `—`) means the grader couldn't find the expected field or value in the output. Common causes:
- The workflow or agent returned no output (check the Execution Error banner above the grader table)
- The output field has a different name than the grader's `path` setting (e.g., grader checks `result` but workflow returns `sum`)
- The workflow or agent returned the correct data wrapped in an extra object (e.g., grader checks `result` but output is `{"data": {"result": 6.0}}` — you'd need `path: "data.result"`)

---

**Q: What's the difference between `output_check` and `state_check`?**

Both are deterministic grader check types:
- **`output_check`** compares the *entire* `final_output` object against an expected value, or checks a condition on the whole output (e.g., `is_not_empty`)
- **`state_check`** navigates to a *specific field* inside the output using a dot-separated path (e.g., `path: "result"` reads `output["result"]`) and compares just that value

Use `state_check` when you want to check one field precisely (e.g., the `result` field of a calculator response). Use `output_check` when you want to check the whole output or just verify it's not empty.

---

**Q: Can I add the same task multiple times to different suites?**

Tasks belong to one suite, but you can create similar tasks in different suites. For example, you might have a "Quick Smoke Test" suite with 5 critical tasks and a "Full Regression Suite" with 50 tasks. You'd run the smoke test on every change and the full suite before releases.

---

**Q: Where are the pre-built benchmarks?**

17 pre-built benchmark suites are included with OpenJiuwen: 10 domain benchmarks (customer support, RAG, code generation, content moderation, data extraction, research agent, translation, email assistant, SQL agent, conversational agent) and 7 pattern benchmarks (Routing, Chaining, Parallelisation, Orchestrator–Worker, Evaluator–Optimizer, Memory Usage, Calculator). Access them via **Add Suite → Add from Library** on the Evaluation page — select the Domain Benchmarks or Pattern Benchmarks tab. Each suite has all tasks and graders pre-configured — just import and run.

---

**Q: How is latency measured?**

Latency is the wall-clock time from when a trial started executing to when it finished, measured in milliseconds and displayed as seconds if over 1000 ms (e.g., `1.08s`). It includes LLM response time, tool call time, and all internal processing. Grader evaluation time is not counted against the workflow or agent's latency.

---

**Q: Are evaluation results private to my space?**

Yes. Evaluation suites, tasks, runs, and results are all scoped to your space. Other spaces cannot see your evaluation data.

---

**Q: What is the difference between success rate and average score?**

Success rate is binary: each trial either passed or failed, and success rate counts the passing fraction. Average score is continuous: even failing trials have a score (e.g., 0.4 out of 1.0), and the average score includes all of them. A workflow with 50% success rate might have an average score of 0.75 (near-misses) or 0.20 (completely wrong answers half the time). The average score tells you more about the quality of failures.

---

**Q: What does "flakiness" tell me that success rate doesn't?**

Success rate tells you how often the workflow or agent passes across all trials. Flakiness tells you whether those passes and failures are *randomly distributed* or *input-specific*. A workflow with 60% success rate and zero flakiness consistently passes the same inputs and fails the same inputs — the failures are deterministic and fixable. A workflow with 60% success rate and high flakiness fails randomly on the same inputs — the problem is non-determinism in the model or workflow, not a specific fixable bug.

---

**Q: What is the Graders tab for?**

The Graders tab shows aggregate statistics broken down by individual grader name — how often each grader passed, what average score it gave, and how many trials it evaluated. Use it when you have multiple graders on a task and want to know *which specific criterion* is failing. For example, if you have a "structure" grader and a "quality" grader and the overall success rate is low, the Graders tab will tell you whether structure is fine but quality is failing, or vice versa.

---

**Q: What are custom aggregate metrics and when should I use them?**

Custom aggregate metrics are Python functions you write that compute a single number (or dict) from the full list of trial results. Use them when the built-in metrics don't capture what you care about — for example:
- A metric that weights score by task difficulty
- A "consistency per category" metric grouped by task tag
- A domain-specific score combining latency and pass rate

They're defined at the suite level via the **Custom Metrics** tab in the Results & Traces view and persist across runs. They're recomputed every time you view results, so you can add them without re-running evaluations.

---

**Q: Why do I see "· details" links on some stat cards?**

The "· details" links open popup dialogs with more information that would be too detailed to show in the card itself:
- **Avg Score · details** → Score Distribution histogram (five 20% buckets showing where scores cluster)
- **Avg Latency · details** → Latency Breakdown table (median, p95, min, max, total)

These details are hidden by default to keep the Overview tab uncluttered.

---

*This guide covers all major features of the OpenJiuwen Evaluation System. For technical reference documentation (API endpoints, grader schema reference, task schema reference), see the other files in this directory: `EVALUATION_README.md`, `GRADERS.md`, and `TASKS.md`.*

---

## 10. Additional Resources

### Step-by-Step Cookbook
**[`COOKBOOK.md`](./COOKBOOK.md)** — 20+ practical recipes showing exactly how to configure evaluation for specific use cases:
- How to evaluate a customer support routing agent
- How to test RAG pipeline accuracy with citation verification
- How to use model-based grading for open-ended answers
- How to set up regression gates in CI/CD with `agenteval --fail-threshold`
- How to write custom aggregate metrics in Python

### Example Evaluation Suites
**[`EXAMPLE_SUITES/`](./EXAMPLE_SUITES/)** — 10 ready-to-use YAML evaluation suites you can import directly into OpenJiuwen:

| File | Domain | Description |
|------|--------|-------------|
| `01_customer_support.yaml` | Customer Support | Intent routing, escalation detection, tone checking |
| `02_rag_system.yaml` | RAG / Q&A | Retrieval accuracy, citation quality, groundedness |
| `03_code_generation.yaml` | Code | Syntax correctness, test passing, style compliance |
| `04_content_moderation.yaml` | Safety | Harmful content detection, false-positive rate |
| `05_data_extraction.yaml` | Structured Output | JSON schema compliance, field extraction accuracy |
| `06_research_agent.yaml` | Research | Source coverage, claim accuracy, report structure |
| `07_translation_agent.yaml` | Translation | Translation quality, terminology consistency, length ratio |
| `08_email_assistant.yaml` | Productivity | Email tone, action items, brevity, reply relevance |
| `09_sql_agent.yaml` | SQL / Data | Query correctness, safe SQL, performance hints |
| `10_conversational_agent.yaml` | Chat | Coherence, context retention, helpfulness, safety |

To import: open the **Evaluation** page → **Add Suite → Add from Library** → select the Domain Benchmarks tab → click a card → **Add to My Suites**.

> **Tip**: These YAML files can also be imported programmatically via the CLI (`agenteval`) or the Python SDK.

### CLI Tool (`agenteval`)
Run evaluations from the terminal and integrate with CI/CD pipelines:

```bash
# Install
pip install -e backend/

# Configure
agenteval configure --api-url http://localhost:8000 --token <jwt> --space-id <id>

# List suites
agenteval suites

# Run and block until complete; exit code 1 if success rate < 80%
agenteval run --suite-id <id> --workflow-id <id> --wait --fail-threshold 0.8

# Show results with per-task breakdown
agenteval results --run-id <id> -v

# Export as CSV
agenteval export --run-id <id> --format csv -o results.csv
```

### Python SDK
The `openjiuwen-sdk` package provides programmatic access for scripting and automation:

```python
from openjiuwen_studio.evaluation.sdk import EvaluationClient

client = EvaluationClient(api_url="http://localhost:8000", token="<jwt>", space_id="<id>")

# List suites
suites = client.list_suites()

# Start a run and wait for completion
run = client.run(evaluation_id="<id>", workflow_id="<wf_id>", wait=True)
print(f"Success rate: {run.metrics.success_rate:.1%}")

# Export results
results = client.get_results(run.run_id)
```

See [`EVALUATION_README.md`](./EVALUATION_README.md) for the full SDK API reference.

### Video Tutorials
Eight short video tutorials are planned (scripts in [`VIDEO_SCRIPTS.md`](dev/VIDEO_SCRIPTS.md)):

| # | Title | Duration | Topics |
|---|-------|----------|--------|
| 1 | Getting Started in 5 Minutes | 5 min | Create suite, add task, first run |
| 2 | Understanding Evaluation Results | 4 min | Metrics panel, heatmap, traces |
| 3 | Creating Effective Tasks | 5 min | Input design, trials, grader selection |
| 4 | Grader Types Explained | 5 min | Deterministic, model-based, code-based |
| 5 | Custom Metrics | 3 min | Python metric builder, aggregate formulas |
| 6 | Loading and Customising Benchmarks | 3 min | Benchmark browser, YAML editing |
| 7 | Debugging Failures with Traces | 4 min | Trace viewer, tool call inspection |
| 8 | Advanced Patterns | 5 min | pass@k, run comparison, CI/CD gate |

> **Note**: Video recording is pending. Scripts with full narration and screen action notes are available in `VIDEO_SCRIPTS.md`.

### Reference Documentation

| File | Contents |
|------|----------|
| [`EVALUATION_README.md`](./EVALUATION_README.md) | API endpoint reference, schema definitions |
| [`GRADERS.md`](./GRADERS.md) | All grader types with schema and examples |
| [`TASKS.md`](./TASKS.md) | Task schema, input/output format, trials |
| [`GRADER_PRESETS.md`](./GRADER_PRESETS.md) | Pre-built grader configurations |
| [`TROUBLESHOOTING.md`](./TROUBLESHOOTING.md) | Common errors and how to fix them |
| [`ONBOARDING_FLOW.md`](./ONBOARDING_FLOW.md) | New user onboarding sequence |
| [`INDEX.md`](./INDEX.md) | Master index of all evaluation documentation |
