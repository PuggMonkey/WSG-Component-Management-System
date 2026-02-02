# Technical Documentation — WSG Component Tracking & Logging Prototype

## 1. Requirements (from brief)
WSG requires a prototype tool that enables engineers to:
- record **component status updates**
- maintain **operational logs**
- monitor **quantities** (stock levels)
- flag **replenishment requirements**

Non-functional expectations:
- **Reliable** (data integrity, predictable behaviour)
- **Easy to maintain** (clean structure, separation of concerns)
- **Modular** (reusable components, clear decomposition)
- Demonstrate **more than one paradigm** (structured + modular + event-driven)
- Include **input validation**, basic error handling, internal comments
- Provide **technical documentation** and **testing evidence**

## 2. Solution overview
The prototype is a Python CLI application with a SQLite database.

### Key idea
Separate the system into layers:
- **Domain models** (`component.py`, `user.py`): data + validation rules
- **Database/schema** (`db.py`): connection settings + table creation
- **Repository** (`repositories.py`): SQL queries isolated in one place
- **Service/business logic** (`services.py`): “what the system does” + transactions + events
- **Interface** (`cli.py`, `main.py`): structured CLI flow + user input validation
- **Tests** (`tests/`): verification against an in-memory SQLite database

This modular decomposition makes the code easier to maintain and test.

## 3. Programming paradigms demonstrated
### 3.1 Structured programming (required)
- The CLI uses **sequence**, **selection**, and **iteration**:
  - `while True` menu loop
  - `if/elif/else` decision structure for commands
  - repeated input validation loops (`_prompt_int`, `_prompt_non_empty`)

### 3.2 Modular / procedural decomposition (required)
- Logic is broken into reusable functions and modules:
  - input functions (`cli.py`)
  - repository functions for SQL (`repositories.py`)
  - service methods for business behaviour (`services.py`)

### 3.3 Event-driven programming (additional paradigm)
- `events.py` implements a small **publish/subscribe** event bus.
- The service publishes `LOW_STOCK` events when a component reaches the replenishment threshold.
- The CLI subscribes and prints an alert without tightly coupling the business logic to UI output.

## 4. Data model & schema (SQLite)
The database schema is created by `init_db()` in `db.py`.

### 4.1 `components` table
Stores current state of each tracked component:
- `name`, `description`, `status`
- `quantity` (current stock)
- `min_quantity` (threshold: replenish when quantity <= min_quantity)
- timestamps (`created_at`, `updated_at`)

### 4.2 `logs` table
Stores audit/operational log entries:
- component reference (`component_id`)
- timestamp, user name, action, message
- optional before/after fields for status and quantity changes

Reliability features:
- SQLite **foreign keys** enabled (`PRAGMA foreign_keys = ON`)
- `logs.component_id` enforces referential integrity (`ON DELETE CASCADE`)

## 5. Validation and error handling
### 5.1 Input validation (UI layer)
`cli.py` ensures:
- non-empty strings for required fields
- integers for numeric fields, with minimum constraints where needed

### 5.2 Domain validation (model layer)
`Component` validates:
- allowed statuses: `active`, `idle`, `defected`, `retired`
- `quantity >= 0`, `min_quantity >= 0`

### 5.3 Error handling (service layer)
`services.py` uses:
- `try/except sqlite3.Error` to catch database errors
- `commit()`/`rollback()` transactions for reliability
- `ValueError` for invalid business actions (e.g., negative stock)

## 6. How to run
### 6.1 Run the application

```bash
python main.py
```

This creates/uses `wsg_components.db` in the current directory.

### 6.2 Run automated tests

```bash
python -m unittest -v
```

## 7. Testing & debugging evidence
### 7.1 Automated tests included
`tests/test_prototype.py` verifies:
- component creation and retrieval
- duplicate name detection
- invalid status rejection
- low-stock event publication
- log entries are written for key actions

### 7.2 Debugging approach used
During development, correctness was validated by:
- using an in-memory SQLite database in tests (`:memory:`) to isolate behaviour
- checking boundary cases (invalid status, duplicate names, negative quantity results)
- verifying side effects (log rows + low-stock events)

## 8. Maintainability notes / future improvements
If expanded beyond prototype, recommended next steps:
- implement proper user authentication and hashed passwords
- add richer log formatting (include min_quantity changes as dedicated fields)
- provide filtered log searches (by date range, action type)
- add export/reporting (CSV/JSON)
- build a small GUI/web UI while keeping the same service/repository layers

