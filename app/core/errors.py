"""Exception hierarchy for PulseForge.

Everything this project raises inherits from `PulseForgeError`. Nothing raises a
bare `Exception`. Callers wanting "anything PulseForge did" catch one class;
callers wanting precision get it.
"""


class PulseForgeError(Exception):
    """Base class for every error this project raises."""


class ConfigurationError(PulseForgeError):
    """Invalid or missing configuration. Raised at startup, never mid-run."""


class CaptureError(PulseForgeError):
    """Traffic capture failed."""


class SanitizationError(CaptureError):
    """A request could not be sanitized, so it must not be stored.

    Fail-closed by design: if we cannot prove a record is safe to write, we drop
    it rather than write it. See SECURITY.md.
    """


class StorageError(PulseForgeError):
    """An artifact could not be read or written."""


class ArtifactNotFoundError(StorageError):
    """A content-addressed artifact was requested but does not exist."""


class SchemaVersionError(StorageError):
    """An artifact carries a schema_version this build cannot read."""


class ReplayError(PulseForgeError):
    """The replay engine could not execute a plan."""


class WorkloadPlanError(PulseForgeError):
    """A workload plan is missing, malformed, or unusable."""


class PlanIntegrityError(WorkloadPlanError):
    """A plan's content hash does not match its declared plan_id.

    Highest-severity error in the system: it means baseline and candidate may not
    have received identical workloads (R7), which makes any verdict derived from
    them meaningless.
    """


class ComparisonError(PulseForgeError):
    """Two result sets could not be compared."""


class GateError(PulseForgeError):
    """A verdict could not be produced."""


class PlannerError(PulseForgeError):
    """The workload planner failed."""


class PlannerUnavailableError(PlannerError):
    """The LLM planner was unreachable or returned unusable output.

    Never fatal. The caller falls back to full-corpus replay and logs that it did
    (R6). A third-party outage must not fail the pipeline.
    """
