# dev-agent-team

Claude Code Agent Teams template for full-stack development. Accepts a brief and produces working code through 6 specialized agents with explicit handoffs, structured messages, and revision loops.

## Prerequisites

- Claude Code CLI installed
- WSL Ubuntu with `tmux`
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (already set in `.claude/settings.json`)

## Quick start

### 1. Create a new project from this template

```bash
gh repo create my-project --template ameba7464/dev-agent-team --clone
cd my-project
```

### 2. Write the brief

```bash
cp agent-runtime/shared/brief.template.md agent-runtime/shared/brief.md
# Fill in brief.md — describe what you want to build
```

### 3. (Optional) Override the tech stack

Edit `stack.md`. Default: Python + FastAPI + PostgreSQL / React 18 + TypeScript + Tailwind CSS.

### 4. Run

```bash
# Inside WSL Ubuntu:
tmux new-session -s main
claude
```

Then tell `lead`:
```
Прочитай brief в файле agent-runtime/shared/brief.md и запусти команду агентов.
```

### Reset between runs

```bash
./reset.sh
```

---

## Agent pipeline

```
agent-runtime/shared/brief.md
           ↓
         lead          → state/plan.md + state/status.md
           ↓
   system-designer     → shared/architecture.md
                          shared/api-contracts.md
                          shared/db-schema.md
                          shared/component-tree.md
        ↓                        ↓
  backend-dev              frontend-dev        (parallel)
        ↓                        ↓
        └──── qa-engineer + bug-hunter ────┘   (parallel)
                         ↓
              outputs/final-summary.md
```

| Agent | Role | Starts when |
|---|---|---|
| `lead` | Coordinator — reads brief, creates plan, orchestrates | Immediately |
| `system-designer` | Architecture, API contracts, DB schema, component tree | After `lead` assignment |
| `backend-dev` | Python / FastAPI code | After `system-designer` handoff |
| `frontend-dev` | React / TypeScript / Tailwind code | After `system-designer` handoff, parallel with `backend-dev` |
| `qa-engineer` | Tests (pytest + Vitest) + code review | After both devs complete |
| `bug-hunter` | Security analysis — OWASP Top 10 | After both devs complete, parallel with `qa-engineer` |

---

## Infrastructure

### Entry point

Operator writes `agent-runtime/shared/brief.md` before each run. Template: `agent-runtime/shared/brief.template.md`.

### Messages

All inter-agent communication uses structured handoff files in `agent-runtime/messages/`:

```
from-lead-to-system-designer.md         type: assignment
from-system-designer-to-backend-dev.md  type: handoff
from-system-designer-to-frontend-dev.md type: handoff
from-backend-dev-to-qa-engineer.md      type: handoff
from-qa-engineer-to-backend-dev.md      type: revision_request  (if issues found)
from-bug-hunter-to-lead.md              type: approval | rejection
...
```

Format: see `agent-runtime/messages/message-template.md`

### Artifact structure

```
agent-runtime/
├── shared/           ← intermediate artifacts between agents
│   ├── brief.md            ← operator fills this (gitignored)
│   ├── brief.template.md   ← committed template
│   ├── architecture.md
│   ├── api-contracts.md
│   ├── db-schema.md
│   ├── component-tree.md
│   ├── backend-done.md
│   ├── frontend-done.md
│   ├── review-report.md
│   └── bugs-report.md
├── messages/         ← handoff files (from-<agent>-to-<agent>.md)
│   └── message-template.md ← committed format reference
├── state/            ← plan.md and status.md from lead
└── outputs/
    ├── backend/      ← FastAPI application code
    ├── frontend/     ← React application code
    └── tests/
        ├── backend/  ← pytest tests
        └── frontend/ ← Vitest tests
```

---

## Design principles

**Artifact-driven communication.** Actual work travels via files in `shared/` and `outputs/`. Intent and coordination travel via structured messages in `messages/`. This separation makes the system inspectable — any state is visible on disk.

**Explicit revision loops.** `qa-engineer` and `bug-hunter` send `revision_request` messages directly to the responsible developer. `lead` tracks status in a table (agent / phase / status / blockers) and re-triggers work when needed.

**Non-negotiable acceptance criteria.** Each agent has hard-stop rules — it cannot mark its task complete until all criteria are met. No soft objectives.

**One agent = one specialization.** The harness — explicit handoffs, material artifacts, structured messages — is what makes the system reliable. A well-constrained agent outperforms a more capable agent in a weak harness.
