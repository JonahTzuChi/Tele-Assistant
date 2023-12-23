class ViolateContentModerationError(Exception):
    """
    Raise when content violates the content moderation policy
    """
    pass

class TimeoutError(Exception):
    """
    Raise when timeout
    """
    pass