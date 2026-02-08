import uuid


def generate_form_token(request, token_name='form_token'):
    """Generate a unique token, store it in the session, and return it."""
    token = str(uuid.uuid4())
    request.session[token_name] = token
    return token


def is_duplicate_submission(request, token_name='form_token'):
    """
    Check if this is a duplicate form submission.
    Returns True if duplicate (token missing or doesn't match), False if valid first submission.
    Does NOT consume the token - use consume_form_token() after successful processing.
    """
    submitted_token = request.POST.get(token_name)
    session_token = request.session.get(token_name)
    if not submitted_token or not session_token:
        return True
    return submitted_token != session_token


def consume_form_token(request, token_name='form_token'):
    """
    Consume (remove) the form token from the session.
    Call this only after the form has been successfully processed.
    """
    request.session.pop(token_name, None)

