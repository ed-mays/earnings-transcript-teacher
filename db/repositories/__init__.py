"""Repository package — re-exports all classes for backwards-compatible imports.

Existing code using ``from db.repositories import CallRepository`` continues to
work without any changes after the monolith was split into per-class modules.
"""

from db.repositories.analytics import AnalyticsRepository
from db.repositories.analysis import AnalysisRepository
from db.repositories.calls import CallRepository
from db.repositories.competitors import CompetitorRepository
from db.repositories.embeddings import EmbeddingRepository
from db.repositories.flags import FlagRepository
from db.repositories.learning import LearningRepository, SYSTEM_USER_ID
from db.repositories.progress import ProgressRepository
from db.repositories.schema import (
    SchemaRepository,
    OutdatedSchemaError,
    RepositoryError,
    reset_all_data,
)

__all__ = [
    "AnalyticsRepository",
    "AnalysisRepository",
    "CallRepository",
    "CompetitorRepository",
    "EmbeddingRepository",
    "FlagRepository",
    "LearningRepository",
    "SYSTEM_USER_ID",
    "ProgressRepository",
    "SchemaRepository",
    "OutdatedSchemaError",
    "RepositoryError",
    "reset_all_data",
]
