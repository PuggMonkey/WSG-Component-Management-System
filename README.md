# WSG Component Tracking & Logging Tool (Prototype)

This is a functional prototype for Wyre Systems Group (WSG) to track components, record status updates, maintain operational logs, monitor stock quantities, and flag replenishment requirements.

## Features
- Create and list components (name, description, status, quantity, replenishment threshold)
- Update component status with an audit log entry
- Adjust stock quantities with an audit log entry
- List low-stock components (quantity <= threshold)
- View recent logs for a specific component or for all components
- Uses SQLite for persistent storage
- Demonstrates an event-driven element (low-stock alerts) via a small event bus

## Run the prototype
From this folder:

```bash
python main.py
```

This creates/uses a local SQLite database file `wsg_components.db`.

## Run tests (evidence of correctness)
From this folder:

```bash
python -m unittest -v
```

## Documentation
See `TECHNICAL_DOCUMENTATION.md` for:
- requirements analysis
- design decisions and paradigms
- schema/architecture notes
- testing and debugging evidence

