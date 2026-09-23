class EngineUnavailableError(Exception):
    """The engine cannot answer right now (provider down, spend unknown). The route returns 503."""
