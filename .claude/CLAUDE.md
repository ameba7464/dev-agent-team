# Dev Agent Team

Этот проект — персональная утилита мультиагентной разработки на базе Claude Code Agent Teams. Команда принимает ТЗ текстом и производит готовый код через специализированных агентов.

## Обязательный режим запуска

Запуск только через `tmux` внутри WSL Ubuntu.

```bash
# 1. Открой WSL-терминал и перейди в проект
cd /mnt/c/Users/miros/OneDrive/Документы/Работа/tablichka

# 2. Запусти tmux-сессию
tmux new-session -s main

# 3. Внутри tmux запусти claude
claude
```

## Обязательные настройки

- `.claude/settings.json` — `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
- `.claude/settings.json` — `teammateMode: "tmux"`

## Команда агентов

| Агент | Роль | Стартует когда |
|---|---|---|
| `lead` | Координатор, составляет план | Сразу после получения ТЗ |
| `system-designer` | Архитектура, API-контракты, схема БД | После `lead` |
| `backend-dev` | Python / FastAPI код | После `system-designer` |
| `frontend-dev` | React / Tailwind код | После `system-designer`, параллельно с `backend-dev` |
| `qa-engineer` | Тесты (pytest, Vitest) + ревью кода | После `backend-dev` и `frontend-dev` |
| `bug-hunter` | Поиск багов и уязвимостей | После `backend-dev` и `frontend-dev`, параллельно с `qa-engineer` |

## Workflow

```
agent-runtime/shared/brief.md   ← оператор заполняет перед запуском
           ↓
         lead → state/plan.md + state/status.md
           ↓
   system-designer → shared/architecture.md, api-contracts.md, db-schema.md, component-tree.md
        ↓                        ↓
  backend-dev              frontend-dev   (параллельно)
        ↓                        ↓
        └──── qa-engineer + bug-hunter (параллельно) ────┘
                         ↓
              outputs/final-summary.md
```

## Структура артефактов

```
agent-runtime/
├── shared/                 ← артефакты между агентами
│   ├── brief.md            ← ВХОД: оператор заполняет (gitignored)
│   ├── brief.template.md   ← шаблон brief (committed)
│   ├── architecture.md
│   ├── api-contracts.md
│   ├── db-schema.md
│   ├── component-tree.md
│   ├── backend-done.md
│   ├── frontend-done.md
│   ├── review-report.md
│   └── bugs-report.md
├── messages/               ← handoff-сообщения между агентами
│   └── message-template.md ← формат сообщений (committed)
├── state/                  ← plan.md и status.md от lead
└── outputs/                ← финальный код
    ├── backend/
    ├── frontend/
    └── tests/
```

## Правила для всех агентов

- Входная точка — `agent-runtime/shared/brief.md`. Не начинать без него.
- Каждый handoff — явный файл в `agent-runtime/messages/` в формате из `message-template.md`.
- Типы сообщений: `assignment`, `handoff`, `revision_request`, `approval`, `rejection`, `blocker`.
- Код только в `agent-runtime/outputs/`. Shared-артефакты только в `agent-runtime/shared/`.
- Не помечать задачу завершённой с незакрытыми critical-проблемами.

## Как использовать в новом проекте

```bash
# Клонировать шаблон
gh repo create my-project --template ameba7464/dev-agent-team --clone
cd my-project

# Заполнить brief
cp agent-runtime/shared/brief.template.md agent-runtime/shared/brief.md
# отредактировать brief.md

# Запустить
tmux new-session -s main
claude
```

Затем дать lead-инструкцию:
```
Прочитай brief в файле agent-runtime/shared/brief.md и запусти команду агентов.
```

---

# Правила написания агентов

## Основной принцип

Таски атомарные, гранулярные, специфичные. Каждый агент делает ОДНУ вещь. Сумма всех решает задачу целиком.

Агент внутри сильного harness-а превосходит более способного агента внутри слабого. Это не промптинг — это системное проектирование.

## Структура агента

### 1. Название и миссия

Одно предложение. Что агент делает и зачем. Никаких абстракций — конкретная функция.

### 2. Обязанности

Список конкретных действий. Каждый пункт — одно действие. Если агенту нужно больше трёх шагов — разбить на несколько агентов.

### 3. Инструкции

Если агент выполняет скрипт — указать точный путь:
```
Execute: agent-runtime/outputs/generate.py
```

Если читает файл — указать точный путь. Никаких "посмотри в папке".

### 4. Non-Negotiable Acceptance Criteria

**Самая важная секция.** Определяет что НЕ является предметом торга. Агент не завершает работу пока не выполнены все критерии.

Использовать именно "Non-Negotiable", а не "Rules" или "Objectives":
- "Rules" смягчает — агент решает что соблюдать
- "Non-Negotiable" создаёт обязательство

Формат каждого критерия:
```
- [Артефакт/условие] должен содержать [конкретное требование].
```

### 5. Обязательные выходы

Точные пути к файлам. Форматы. Никакой свободы интерпретации. Без определённых выходов нельзя строить цепочки агентов.

## Правила harness-оптимизации

- Один агент = одна специализация
- Явные зависимости: агент B стартует только после артефакта от агента A
- Каждый handoff — материальный файл, не подразумеваемая договорённость
- Если агенту нужно больше 3 шагов — это два агента

## Правила взаимодействия агентов

- Handoff-сообщения пишутся в `agent-runtime/messages/`, имя: `from-<агент>-to-<агент>.md`
- Формат каждого сообщения — из `agent-runtime/messages/message-template.md` (поля: id, from, to, type, topic, artifacts, needs, deadline, notes)
- Типы: `assignment` | `handoff` | `revision_request` | `approval` | `rejection` | `blocker`
- Shared-артефакты: `agent-runtime/shared/`
- Финальные результаты: `agent-runtime/outputs/`

## Чего не делать

- Не писать агента который "делает всё"
- Не оставлять выходы без точных путей
- Не использовать размытые критерии ("хорошее качество", "полный анализ")
- Не дублировать ответственность между агентами
