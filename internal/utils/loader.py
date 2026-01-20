import yaml
from .logger import AppLogger

logger = AppLogger("utils.Loader")()

def load_yaml(path: str) -> dict:
    """Load parameters from a YAML file."""
    try:
        with open(path, 'r') as file:
            params = yaml.safe_load(file)
        logger.debug('Parameters retrieved from %s', path)
        return params
    except FileNotFoundError:
        logger.error('File not found: %s', path)
        raise
    except yaml.YAMLError as e:
        logger.error('YAML error: %s', e)
        raise
    except Exception as e:
        logger.error('Unexpected error: %s', e)
        raise
