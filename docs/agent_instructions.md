# AI Agent Instructions

When contributing to this repository (`Pfirsichfest`), AI Assistants must adhere to the following architectural and stylistic constraints:

## 1. Package Management
*   **Use Conda:** We exclusively use `Conda` via `environment.yml` to handle both Python packages and non-Python system dependencies (like `aria2`). 
*   **Do not use `requirements.txt` or `uv`**.
*   **Pip Fallback:** If Conda-Forge fails to resolve specific Python SDKs (like `google-cloud-compute`), place them explicitly under the `- pip:` array within the `environment.yml`.

## 2. Code Quality
*   **Pre-commit:** All code must pass local `.pre-commit-config.yaml` checks before pushing.
*   **Linter (`ruff`):** Use the latest version of Ruff. Enable all rules (`lint.select = ["ALL"]`) inside `.pyproject.toml`, mitigating only strict formatting conflicts (`COM812`, `ISC001`).
*   **Type Checker (`pyright`):** Use the latest version of Pyright. Enforce `typeCheckingMode = "strict"`.

## 3. Git Workflow
*   **Single Branching:** Maintain a single active production branch: `main`. Do not use `master`.
*   **Conventional Commits:** All Git commits must be thoroughly isolated and prefixed according to the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) standard (e.g., `feat:`, `fix:`, `build:`, `docs:`).
*   **Clean Workspaces:** Actively maintain `.gitignore` to prevent tracking of `.venv`, `__pycache__`, or local `.env` secrets. Ensure no un-tracked legacy files (`requirements.txt`) are left behind.

## 4. Documentation & Monorepo
*   **Module-Level Docs:** Since this is a monorepo, each discrete service (`/bot`, `/downloader`) must maintain its own internal `README.md` explaining its localized purpose, dependencies, and environment triggers.

## 5. Continuous Integration (CI)
*   **Automated Verification:** Every codebase alteration should have an accompanying placeholder `pytest` in `module/tests/`.
*   **GitHub Actions:** Ensure the `.github/workflows/ci.yml` runs successfully against `pre-commit` and `conda run pytest` on the `main` branch.
