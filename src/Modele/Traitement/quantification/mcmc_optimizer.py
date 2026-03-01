from src.logger import get_logger

logger = get_logger(__name__)

def run_mcmc(*args, **kwargs):
    logger.warning("[MCMC] Not implemented in minimal version")
    raise NotImplementedError("MCMC not enabled in Option A")