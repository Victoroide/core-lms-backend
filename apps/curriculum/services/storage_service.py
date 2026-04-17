"""Callable upload_to helpers for S3-backed FileFields in the curriculum app."""


def submission_upload_path(instance, filename):
    """Return the S3 object key for a student submission file, partitioned by student.

    Args:
        instance (Submission): The Submission model instance being saved.
        filename (str): The original filename of the uploaded file.

    Returns:
        str: The S3 object key path.
    """
    return f"submissions/{instance.student_id}/{filename}"
