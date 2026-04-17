"""Callable upload_to helpers for S3-backed FileFields in the learning app."""


def resource_upload_path(instance, filename):
    """Return the S3 object key for a lesson resource file, partitioned by course.

    Args:
        instance (Resource): The Resource model instance being saved.
        filename (str): The original filename of the uploaded file.

    Returns:
        str: The S3 object key path.
    """
    return f"resources/{instance.lesson.module.course_id}/{filename}"
