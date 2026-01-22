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

RAW_PROSPECTIVE_WHITELABELS_PATH = APP_BASE_DIR / "artifacts/raw_prospective_whitelabels.json"


DEDUPLICATION_SCHEMA_PATH = APP_BASE_DIR / "internal/domain/pipeline/schema.sql"
DEDUPLICATION_RESULTS_PATH = ARTIFACTS_DIR / "deduplication_results.json"
DB_MODELS_TEMP_DIR = ARTIFACTS_DIR / "db_models_temp"
RAW_PROSPECTIVE_INDIVIDUALS_PATH = APP_BASE_DIR / "artifacts/raw_prospective_individuals.json"

FUNNEL_CONFIG_PATH = APP_BASE_DIR / "internal/config/funnel_config.yaml"
