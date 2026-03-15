# dev-agent-team

Claude Code Agent Teams template for full-stack development. Accepts a text spec and produces working code through 6 specialized agents with explicit handoffs and non-negotiable acceptance criteria.

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

Or clone directly:

```bash
git clone https://github.com/ameba7464/dev-agent-team my-project
cd my-project
```

### 2. Fill in the requirements

Edit `task.md` — describe what you want to build.

### 3. (Optional) Override the tech stack

Edit `stack.md` to use a different stack. Default: Python + FastAPI + PostgreSQL / React 18 + TypeScript + Tailwind CSS.

### 4. Run

```bash
# Inside WSL Ubuntu:
tmux new-session -s main
claude
```

Then tell `lead`:
```
Прочитай ТЗ в файле task.md и запусти команду агентов.
```

### Reset between runs

```bash
./reset.sh
```

---

## Agent pipeline

```
task.md
    ↓
  lead          → agent-runtime/state/plan.md + status.md
    ↓
system-designer → shared/architecture.md + api-contracts.md + db-schema.md + component-tree.md
    ↓                       ↓
backend-dev           frontend-dev        (parallel)
    ↓                       ↓
    └──── qa-engineer + bug-hunter ────┘  (parallel)
                    ↓
         outputs/final-summary.md
```

| Agent | Role | Starts when |
|---|---|---|
| `lead` | Coordinator, creates plan | Immediately after task |
| `system-designer` | Architecture, API contracts, DB schema | After `lead` |
| `backend-dev` | Python / FastAPI code | After `system-designer` |
| `frontend-dev` | React / Tailwind code | After `system-designer`, parallel with `backend-dev` |
| `qa-engineer` | Tests (pytest, Vitest) + code review | After `backend-dev` and `frontend-dev` |
| `bug-hunter` | Security vulnerabilities (OWASP Top 10) | After `backend-dev` and `frontend-dev`, parallel with `qa-engineer` |

---

## Output structure

```
agent-runtime/
├── shared/           ← artifacts shared between agents
│   ├── architecture.md
│   ├── api-contracts.md
│   ├── db-schema.md
│   ├── component-tree.md
│   ├── backend-done.md
│   ├── frontend-done.md
│   ├── review-report.md
│   └── bugs-report.md
├── messages/         ← handoff files (from-<agent>-to-<agent>.md)
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

**One agent = one specialization.** Each agent does exactly one thing. The harness — explicit handoffs, material artifacts, non-negotiable acceptance criteria — is what makes the system work. A well-constrained weaker agent outperforms a capable agent in a weak harness.

**Every handoff is a file.** No implied contracts. Agent B starts only after it reads the artifact produced by Agent A. All intermediate state is visible on disk.

**Non-negotiable criteria.** Each agent has hard-stop rules — it cannot mark its task complete until all criteria are met. No soft "objectives" or "guidelines".
