from rest_framework.permissions import BasePermission


class IsStudent(BasePermission):
    """Grants access only to users with role STUDENT.

    Depends on the custom LMSUser model having a `role` field
    with `Role.STUDENT` as a valid choice.
    """

    message = "Access restricted to students."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "STUDENT"
        )


class IsTutor(BasePermission):
    """Grants access only to users with role TUTOR.

    Depends on the custom LMSUser model having a `role` field
    with `Role.TUTOR` as a valid choice.
    """

    message = "Access restricted to tutors."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "TUTOR"
        )
