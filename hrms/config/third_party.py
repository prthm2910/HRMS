THIRD_PARTY_APPS = [
    'rest_framework',              # The API Toolkit
    'rest_framework_simplejwt',    # For Auth Tokens
    'corsheaders',                 # To allow Frontend access
    'django_filters',              # Advanced filtering
    'drf_spectacular',             # For API Schema and Docs
    'phonenumber_field',           # Standardized phone numbers
    'rest_framework_simplejwt.token_blacklist', # For blacklisting tokens (Logout)
]

SPECTACULAR_CONFIG = {
    'TITLE': 'HRMS API',
    'DESCRIPTION': 'Human Resource Management System API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'ENUM_NAME_OVERRIDES': {
        'PayrollStatus': 'apps.payroll.models.PayrollStatus',
        'LeaveRequestStatus': 'apps.leaves.models.LeaveRequestStatus',
    },
}