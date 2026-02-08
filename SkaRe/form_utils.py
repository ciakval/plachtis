import uuid


def generate_form_token(request, token_name='form_token'):
    """Generate a unique token, store it in the session, and return it."""
    token = str(uuid.uuid4())
    request.session[token_name] = token
    return token


def is_duplicate_submission(request, token_name='form_token'):
    """
    Check if this is a duplicate form submission.
    Returns True if duplicate (token missing or already consumed), False if first submission.
    Consumes the token on first call so subsequent calls return True.
    """
    submitted_token = request.POST.get(token_name)
    session_token = request.session.pop(token_name, None)
    if not submitted_token or not session_token:
        return True
    return submitted_token != session_token

