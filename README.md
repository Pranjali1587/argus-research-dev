# ARGUS — Research, Benchmarking & UI Work

ARGUS is a project exploring how an AI agent can turn natural-language requests into Linux shell commands while checking command risk before execution. The project includes a governance layer intended to block or request confirmation for potentially destructive actions.

This repository brings together selected project material: research notes, benchmark and evaluation artefacts, a UI mockup, and a snapshot of the early Demo 1 codebase.

## Work documented here

### Research and literature review

- Read and summarised 18 papers and resources relevant to LLM agents, tool use, and AI safety.
- Prepared research summaries and a project progress report.
- Worked on a related-work review around **CARE: Pre-Execution Command Verification for Shell-Executing LLM Agents**.
- Mapped nine related papers/resources, including ClawGuard, MAGE, SafeHarness, AgentDojo, Agent-SafetyBench, ASB, AgentSecBench, and ShellCore.
- Prepared a literature matrix comparing threat models, methods, trajectory awareness, datasets, and evaluation metrics.
- Reviewed CARE's citation genealogy: the references CARE builds on were mapped; the cited-by check was recorded as empty at the time of the report.

### Benchmarking and evaluation

- Contributed to developing and expanding a benchmark to 120 prompts across safe, reversible, destructive, ambiguous, and adversarial cases, including social-engineering-style prompts.
- Organised benchmark prompts and supporting evaluation artefacts.
- The project report records a **64.4% accuracy result on the first baseline test run**.
- The reported analysis highlighted failures on ambiguous prompts and two adversarial prompts that caused destructive commands to be classified as safe.

### UI prototyping

- Created a standalone HTML, CSS, and JavaScript UI mockup.
- The prototype presents Home, Governance & Approval, and Action History screens.
- This is a visual prototype, not a production application or the implemented Electron interface.

## My contribution and project scope

The reports and artefacts in this repository document my work on research review, CARE-related-work mapping, benchmark preparation and analysis, project documentation, and UI prototyping.

The `demo-1/` directory contains an early project code snapshot from the phase in which I participated. It is included as project context; it should not be read as a claim that I independently developed or completed the entire application. The implementation is a team-project artefact.

## Repository guide

| Folder | Contents |
|---|---|
| `research/` | Project progress report, Week 4 report, and CARE related-work mapping |
| `benchmark/` | Benchmark workbook and aggregate baseline logging data |
| `ui-prototype/` | Standalone UI mockup and notes |
| `demo-1/` | Early Demo 1 code snapshot, baseline results, test prompts, and demo instructions |
| `project-documentation/` | Notes describing the scope of the material in this repository |

## Important notes

- Benchmark figures are reported from the project documents and refer to the first recorded baseline run; they are not a claim of final system performance.
- The UI in `ui-prototype/` is a mockup. The Demo 1 code and UI mockup are separate artefacts.
- Research mapping is a literature review, not a claim that the project created or implemented CARE.
- This repository is a selected record of project work and supporting artefacts, not a claim of sole ownership of the complete ARGUS project.
