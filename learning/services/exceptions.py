class AxiomEngineError(Exception):
    """Raised when the AxiomEngine Go microservice returns a non-2xx response
    or an unexpected payload structure."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"AxiomEngine HTTP {status_code}: {detail}")


class AxiomEngineTimeout(Exception):
    """Raised when the HTTP request to AxiomEngine exceeds the configured
    connect or read timeout."""

    def __init__(self, url: str, timeout: tuple):
        self.url = url
        self.timeout = timeout
        super().__init__(
            f"AxiomEngine request to {url} timed out (connect={timeout[0]}s, read={timeout[1]}s)"
        )


class CertificateEligibilityError(Exception):
    """Raised when a student has not met the passing requirements to receive
    a course-completion certificate."""

    def __init__(self, student_id: int, course_id: int, reason: str):
        self.student_id = student_id
        self.course_id = course_id
        self.reason = reason
        super().__init__(
            f"Ineligible for certificate: student={student_id} course={course_id} -- {reason}"
        )
