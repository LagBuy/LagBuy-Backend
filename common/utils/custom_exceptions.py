from rest_framework.exceptions import APIException
from rest_framework import status


class UserAlreadyExist(APIException):
    """Exception to be raised when a user tries creating
    an account with an email that already exist in db.
    As a convention, for security reasons, the response is
    structured in such a way that the user cannot know if the
    email already exist. This prevent bad actors from knowing
    our existing users email.

    The server returns the same response as when an account is
    created successfully, telling the user to check their email
    for a verification link or code. Then a mail informing the user
    that their account already exist is sent instead.
    """
    status = status.HTTP_201_CREATED
    default_detail = "Verification e-mail sent."
    default_code = "Created"
