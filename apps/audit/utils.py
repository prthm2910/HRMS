import threading

_thread_locals = threading.local()


def set_audit_data(user, user_agent, path):
    """Store user, user_agent, and path in the current thread."""
    _thread_locals.current_user = user
    _thread_locals.current_user_agent = user_agent
    _thread_locals.current_path = path  # <--- Store the path

def get_audit_data():
    """Retrieve data as a dictionary."""
    return {
        'user': getattr(_thread_locals, 'current_user', None),
        'user_agent': getattr(_thread_locals, 'current_user_agent', ''),
        'path': getattr(_thread_locals, 'current_path', '') # <--- Retrieve the path
    }

def clear_audit_data():
    """Clean up."""
    if hasattr(_thread_locals, 'current_user'):
        del _thread_locals.current_user
    if hasattr(_thread_locals, 'current_user_agent'):
        del _thread_locals.current_user_agent
    if hasattr(_thread_locals, 'current_path'):
        del _thread_locals.current_path