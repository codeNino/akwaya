from pathlib import Path

def get_project_root() -> Path:
    """Find the project root by looking for pyproject.toml or .git"""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return parent
    # fallback: assume 3 levels up from this file
    return current.parents[3]

APP_BASE_DIR = get_project_root()


ARTIFACTS_DIR = APP_BASE_DIR / "artifacts"

RAW_NORMALIZED_PROSPECT_PATH = APP_BASE_DIR / "artifacts/raw_prospect_normalized.json"

SEARCH_CONFIG_PATH = APP_BASE_DIR / "internal/config/search_config.yaml"

DEDUPLICATION_SCHEMA_PATH = APP_BASE_DIR / "internal/domain/pipeline/schema.sql"
DEDUPLICATION_RESULTS_PATH = ARTIFACTS_DIR / "deduplication_results.json"
DB_MODELS_TEMP_DIR = ARTIFACTS_DIR / "db_models_temp"