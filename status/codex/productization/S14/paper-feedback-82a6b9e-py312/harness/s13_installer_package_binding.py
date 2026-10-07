"""Bind every actual denial invocation to one verified native distribution."""
from application.platform.distribution import verify_distribution

def require_package_identity(package,expected):
    if verify_distribution(package)!=expected:
        raise ValueError('Native installer denial package identity changed')
