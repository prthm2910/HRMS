THIRD_PARTY_APPS = [
    'rest_framework',              # The API Toolkit
    'rest_framework_simplejwt',    # For Auth Tokens
    'corsheaders',                 # To allow Frontend access
    'django_filters',              # Advanced filtering
    'drf_spectacular',             # For API Schema and Docs
]

SPECTACULAR_CONFIG = {
    'TITLE': 'HRMS API',
    'DESCRIPTION': 'Human Resource Management System API with V1/V2 versioning',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}