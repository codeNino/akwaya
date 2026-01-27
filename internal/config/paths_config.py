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


DEDUPLICATION_SCHEMA_PATH = APP_BASE_DIR / "internal/domain/pipeline/schema.sql"
DEDUPLICATION_RESULTS_PATH = ARTIFACTS_DIR / "deduplication_results.json"
DB_MODELS_TEMP_DIR = ARTIFACTS_DIR / "db_models_temp"
<<<<<<< HEAD
RAW_PROSPECTIVE_INDIVIDUALS_PATH = APP_BASE_DIR / "artifacts/raw_prospective_individuals.json"
DEDUPLICATION_WHITELABELS_RESULTS_PATH = ARTIFACTS_DIR / "deduplication_whitelabels_results.json"
=======

>>>>>>> b8387380f0dc6cbed3022f135bb8d7fcedba7dd7

FUNNEL_CONFIG_PATH = APP_BASE_DIR / "internal/config/funnel_config.yaml"
LEADS_SOURCED_PATH = ARTIFACTS_DIR / "leads_sourced.json"
LEADS_AUGMENTED_PATH = ARTIFACTS_DIR / "leads_augmented.json"
