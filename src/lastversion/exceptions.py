"""Custom exceptions for lastversion."""


class TarPathTraversalException(Exception):
    """Custom exception for path traversal attempts during tar extraction."""


class ApiCredentialsError(Exception):
    """Raised when there's an API error related to credentials"""


class BadProjectError(Exception):
    """Raised when no such project exists"""
