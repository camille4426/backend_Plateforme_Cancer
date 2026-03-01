from src.logger import get_logger

logger = get_logger(__name__)

def run_mh(*args, **kwargs):
    logger.warning("[MH] Not implemented in minimal version")
    raise NotImplementedError("Metropolis-Hastings not enabled in Option A")