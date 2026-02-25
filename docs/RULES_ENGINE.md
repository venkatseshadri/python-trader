# Orbiter Rules Engine: Design Specification (v5)

## 1. Overview
This document outlines the design for a new rules-based evaluation and execution engine. The core principle is to create a "pure" orchestrator in `main.py` that is completely decoupled from all session, strategy, and execution logic.

## 2. Core Components & Principles

### A. The `main.py` (The "Orchestrator")
- **Responsibilities:** A simple, "dumb" loop that asks the `SessionManager` for the high-level application state and calls the appropriate `Engine` method. It has zero business logic.

### B. The `SessionManager` (The "Conductor")
- **Responsibilities:** Manages the application's lifecycle by determining the high-level state (`RUN_EVALUATION_CYCLE`, `RUN_EOD_SEQUENCE`, `HIBERNATE`).

### C. The `ComponentFactory` (The "Builder")
- **Responsibilities:** Builds and returns a single, unified `Engine` object, encapsulating all complexity.

### D. The `Engine` (The "Black Box")
- **File:** `orbiter/core/engine/core_engine.py`
- **Responsibilities:**
    - Encapsulates all core trading components (`state`, `evaluator`, `executor`).
    - Exposes simple, high-level methods like `tick()` and `shutdown()`.
    - The `tick()` method contains the logic for running one evaluation cycle (getting facts, evaluating rules, executing actions).

### E. The `RuleEvaluator` (The "Strategist")
- **Responsibilities:** Takes a JSON rule file and market "facts", evaluates them, and returns a list of "actions".

### F. The `ActionExecutor` (The "Operator")
- **Responsibilities:** Receives a list of actions and executes them.

## 3. High-Level Control Flow (v5)
```
[main.py] -> Asks SessionManager: "What to do?" -> Returns "RUN_EVALUATION_CYCLE"
[main.py] -> Calls engine.tick()
  [Engine] -> Gets facts, calls RuleEvaluator
    [RuleEvaluator] -> Evaluates rules.json -> Returns ["PLACE_SPREAD"]
  [Engine] -> Calls ActionExecutor with actions
    [ActionExecutor] -> Executes place_spread()
(Loop)
---
[main.py] -> Asks SessionManager: "What to do?" -> Returns "RUN_EOD_SEQUENCE"
[main.py] -> Calls engine.shutdown()
  [Engine] -> Calls ActionExecutor
    [ActionExecutor] -> Executes square_off_all()
[main.py] -> Loop terminates.
```

## 4. Refactoring Plan
1.  **Create `Engine` Class:** Implement the new `Engine` class in `orbiter/core/engine/main_engine.py`. Move the evaluation cycle logic from `main.py` into its `tick()` method.
2.  **Update `ComponentFactory`:** Refactor the factory to build and return a single, unified `Engine` instance.
3.  **Final `main.py` Refactor:** Gut the `run()` loop in `main.py` and replace it with the new, simple, `engine.tick()`-based loop.
4.  **Install `rule-engine`:** Add the library to `requirements.txt`.
5.  **Refactor `evaluator.py` and `executor.py`** into the new `RuleEvaluator` and `ActionExecutor` components.
