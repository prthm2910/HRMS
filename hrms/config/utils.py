from datetime import timedelta

def get_db_config(env):
    """
    Constructs the Database dictionary.
    
    Args:
        env: The environ object (e.g., django-environ) that allows reading .env values.
    """
    return {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME'),
            'USER': env('DB_USER'),
            'PASSWORD': env('DB_PASSWORD'),
            'HOST': env('DB_HOST'),
            'PORT': env('DB_PORT'),
        }
    }

def get_simple_jwt_config(env):
    """
    Constructs the Simple JWT configuration dictionary.
    Crucially, this handles the Type Conversion (int -> timedelta) 
    so your main settings file stays clean.
    """
    
    # We fetch the integer value (e.g., 30) or default to 30
    # Note: If using django-environ, env.int() handles casting automatically.
    # If using standard os.getenv, use: int(env('VAR', 30))
    access_token_hours = env.int('ACCESS_TOKEN_LIFETIME_HOURS', default=10)
    refresh_token_days = env.int('REFRESH_TOKEN_LIFETIME_DAYS', default=1)

    return {
        'ACCESS_TOKEN_LIFETIME': timedelta(hours=access_token_hours),
        'REFRESH_TOKEN_LIFETIME': timedelta(days=refresh_token_days),
        'ROTATE_REFRESH_TOKENS': True,
        'BLACKLIST_AFTER_ROTATION': True,
        'AUTH_HEADER_TYPES': ('Bearer',),
    }