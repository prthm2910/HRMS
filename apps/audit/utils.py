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


def log_ai_operation(operation_type, user, input_data, output_data, status, 
                    processing_time_seconds, model_used, error_message=None, 
                    user_agent=None, path=None):
    """
    Log an AI operation to the audit system.
    
    Creates both an AuditLog entry and a linked AIOperationLog entry.
    
    Args:
        operation_type (str): Type of AI operation ('OCR', 'NLP', etc.)
        user: Django User object who initiated the operation
        input_data (dict): Summary of input data
        output_data (dict): Summary of output data
        status (str): Operation status ('SUCCESS', 'FAILED', 'PENDING')
        processing_time_seconds (Decimal): Processing time in seconds
        model_used (str): AI model identifier
        error_message (str, optional): Error message if failed
        user_agent (str, optional): User agent string
        path (str, optional): Request path
        
    Returns:
        AIOperationLog: The created AI operation log instance
    """
    from apps.audit.models import AuditLog, AIOperationLog
    
    # Create parent audit entry
    audit_entry = AuditLog.objects.create(
        actor=user,
        action='AI_SERVICE',
        table_name='AIOperationLog',
        record_id=None,  # Will be set after AI log is created
        changes={'operation_type': operation_type, 'status': status},
        user_agent=user_agent or '',
        path=path or ''
    )
    
    # Create detailed AI operation log
    ai_log = AIOperationLog.objects.create(
        audit_log=audit_entry,
        operation_type=operation_type,
        model_used=model_used,
        input_data=input_data,
        output_data=output_data,
        status=status,
        processing_time_seconds=processing_time_seconds,
        error_message=error_message
    )
    
    # Update audit entry with AI log ID
    audit_entry.record_id = str(ai_log.id)
    audit_entry.save()
    
    return ai_log