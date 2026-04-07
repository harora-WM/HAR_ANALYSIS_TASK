"""
Passes the raw loaded file data directly to Claude without any stripping
or transformation. The full JSON is sent as-is so no signal is lost.
"""


def build_context(loaded: dict) -> dict:
    """
    Returns the raw data from the loaded file unchanged, with filename
    and classification added so the prompt has full context.
    """
    return {
        "filename": loaded["filename"],
        "classification": loaded["classification"],
        "data": loaded["data"],
    }
