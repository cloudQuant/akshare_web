# Quality and development commands
# Usage: make lint | make format | make security | make quality | make test
# Backend: make lint format security typecheck test test-cov
# Frontend: make frontend-lint frontend-format frontend-test frontend-test-cov
# All: make quality pre-commit

.PHONY: lint format security quality test test-cov typecheck deps-audit pre-commit
.PHONY: frontend-lint frontend-format frontend-test frontend-test-cov frontend-typecheck

# Backend (Python)
lint:
	ruff check app/ tests/
	ruff format --check app/ tests/

format:
	ruff check app/ tests/ --fix
	ruff format app/ tests/

security:
	bandit -r app/ -c bandit.yaml -ll

deps-audit:
	@command -v pip-audit >/dev/null 2>&1 && pip-audit -r requirements.txt || echo "pip-audit not installed (pip install pip-audit)"

typecheck:
	mypy app/

quality: lint security deps-audit
	@echo "All backend quality checks passed"

test:
	pytest tests/ -x -q --tb=short

test-cov:
	pytest tests/ -v --cov=app --cov-report=term-missing --cov-fail-under=70

# Frontend (Node)
frontend-lint:
	cd frontend && npm run lint

frontend-format:
	cd frontend && npm run format

frontend-test:
	cd frontend && npx vitest run --testTimeout=15000

frontend-test-cov:
	cd frontend && npm run test:coverage

frontend-typecheck:
	cd frontend && npx vue-tsc --noEmit

# Full quality (backend + frontend)
quality-full: lint security deps-audit typecheck test frontend-lint frontend-typecheck frontend-test
	@echo "All quality checks passed (backend + frontend)"

pre-commit:
	@command -v pre-commit >/dev/null 2>&1 && pre-commit run --all-files || echo "pre-commit not installed (pip install pre-commit)"
