# 🧪 Test Suite (`orbiter/tests/`)

## 🎯 Single Responsibility Principle (SRP)
The `tests/` directory serves as the **Quality Assurance & Verification** layer. It ensures all modular components strictly adhere to their contracts and prevents regressions during refactoring.

## 📂 Architecture

### 1. `unit/` (Isolated Verification)
- Contains isolated, tightly-scoped tests mocking external dependencies.
- **`test_system_utils.py`:** Validates CLI argument parsing and fallback logic.
- **`test_broker_client.py`:** Verifies symbol resolution and API payload formatting without hitting the network.
- **`test_profit_guard.py` & `test_smart_atr_sl.py`:** Mathematically verifies trailing stop loss logic and margin buffers.

### 2. `integration/` (System Verification)
- Tests the orchestration between `CoreEngine`, `SessionManager`, and `ActionManager` using simulated states.

### 3. `data/` (Test Fixtures)
- Contains mock JSON responses and historical tick data used to simulate live market feeds during test execution.

## 🛑 Strict Boundaries
- **Test-Driven Development (TDD):** Tests dictate the code. If a test fails, the application is not production-ready.
- Tests do not connect to live broker APIs unless specifically marked as a live regression module.