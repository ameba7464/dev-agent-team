# Роли Claude Agent Team

В этой папке лежат инструкции ролей для мультиагентного процесса разработки в Claude Agent Teams.

## Состав команды

- `lead.md`: координатор — читает brief, составляет план, запускает агентов в правильном порядке
- `system-designer.md`: архитектор — проектирует API-контракты, схему БД и компонентное дерево
- `backend-dev.md`: Python/FastAPI-разработчик — реализует серверную часть по артефактам system-designer
- `frontend-dev.md`: React-разработчик — реализует клиентскую часть по артефактам system-designer
- `qa-engineer.md`: инженер по качеству — пишет тесты и проводит ревью кода
- `bug-hunter.md`: специалист по безопасности — анализирует код по чеклисту OWASP Top 10

## Порядок запуска

```
lead → system-designer → backend-dev + frontend-dev (параллельно) → qa-engineer + bug-hunter (параллельно) → lead (финализация)
```

## Контракт коммуникации

Все агенты взаимодействуют через общие артефакты и явные handoff-сообщения.

- Общие входные данные и рабочие файлы: `agent-runtime/shared/`
- Статус и план: `agent-runtime/state/`
- Сообщения между агентами: `agent-runtime/messages/`
- Финальные результаты: `agent-runtime/outputs/`

Формат каждого handoff-сообщения — из `agent-runtime/messages/message-template.md`.
