# Схемы HabitFlow

Эти исходники Mermaid можно открыть в редакторе с поддержкой Mermaid и экспортировать в рисунки для пояснительной записки.

## Архитектура

```mermaid
flowchart LR
    U[Пользователь] --> B[Браузер: HTML, CSS, JavaScript]
    B -->|HTTP и формы| F[Flask: маршруты и бизнес-логика]
    F -->|Jinja HTML и JSON API| B
    F -->|SQLAlchemy| P[(PostgreSQL)]
```

## Основные действия

```mermaid
flowchart LR
    U[Пользователь] --> A[Регистрация и вход]
    U --> H[Управление привычками]
    U --> T[Отметка выполнения]
    U --> G[Управление целями]
    U --> S[Статистика и отчёты]
    U --> D[Достижения и шаблоны]
    M[Администратор] --> U
    M --> X[Управление пользователями]
```

## Основные сущности

```mermaid
erDiagram
    USERS ||--o{ CATEGORIES : owns
    USERS ||--o{ HABITS : owns
    USERS ||--o{ GOALS : owns
    CATEGORIES o|--o{ HABITS : groups
    HABITS ||--o{ HABIT_LOGS : records
    HABITS ||--o{ HABIT_SCHEDULES : changes
    GOALS ||--o{ GOAL_HABITS : includes
    HABITS ||--o{ GOAL_HABITS : linked
    USERS ||--o{ USER_ACHIEVEMENTS : earns
    ACHIEVEMENTS ||--o{ USER_ACHIEVEMENTS : awarded
    USERS {
        int id PK
        string email
        string username
        string password_hash
        string role
    }
    CATEGORIES {
        int id PK
        int user_id FK
        string name
    }
    HABITS {
        int id PK
        int user_id FK
        int category_id FK
        string name
        string frequency
        json target_days
    }
    HABIT_LOGS {
        int id PK
        int habit_id FK
        date date
        boolean completed
    }
    HABIT_SCHEDULES {
        int id PK
        int habit_id FK
        date effective_date
        string frequency
        json target_days
    }
    GOALS {
        int id PK
        int user_id FK
        string title
        date deadline
        string status
    }
    GOAL_HABITS {
        int goal_id PK,FK
        int habit_id PK,FK
    }
    ACHIEVEMENTS {
        int id PK
        string code
        string name
    }
    USER_ACHIEVEMENTS {
        int id PK
        int user_id FK
        int achievement_id FK
    }
```
