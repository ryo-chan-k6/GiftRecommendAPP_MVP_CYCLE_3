"""BATCH-015 Item Embedding生成 application package.

MOD-BATCH-036 / MOD-BATCH-037。MOD-BATCH-015（Recheck）と混同しない。
"""

from batch.application.item_embedding.adapter import (
    ScaffoldItemEmbeddingAdapter,
    build_deterministic_stub_vector,
    build_scaffold_adapter,
    is_valid_embedding_input_hash,
    serialize_embedding_input,
)
from batch.application.item_embedding.job import (
    BATCH_ID,
    DEFAULT_MAX_ITEMS,
    DEFAULT_QUEUE_BATCH_SIZE,
    DEFAULT_SOURCE,
    ITEM_EMBEDDING_PHASES,
    ItemEmbeddingError,
    ItemEmbeddingJob,
    build_default_scaffold_job,
    resolve_config_version,
)
from batch.application.item_embedding.models import (
    DEFAULT_EMBEDDING_SOURCE_TYPE,
    EMBEDDING_DIMENSION,
    MVP_EMBEDDING_MODEL_NAME,
    ConfigResolveHint,
    DigestionPlan,
    EmbeddingGenerationContext,
    EmbeddingGenerationResult,
    EmbeddingHashHandoff,
    ItemEmbeddingJobResult,
    ItemEmbeddingUpsertRow,
    ItemRow,
    QueueRow,
)
from batch.application.item_embedding.repositories import (
    DEFAULT_EMBEDDING_MODEL_VERSION,
    ExistingEmbedding,
    ItemEmbeddingRepositories,
)

__all__ = [
    "BATCH_ID",
    "DEFAULT_EMBEDDING_MODEL_VERSION",
    "DEFAULT_EMBEDDING_SOURCE_TYPE",
    "DEFAULT_MAX_ITEMS",
    "DEFAULT_QUEUE_BATCH_SIZE",
    "DEFAULT_SOURCE",
    "EMBEDDING_DIMENSION",
    "ITEM_EMBEDDING_PHASES",
    "MVP_EMBEDDING_MODEL_NAME",
    "ConfigResolveHint",
    "DigestionPlan",
    "EmbeddingGenerationContext",
    "EmbeddingGenerationResult",
    "EmbeddingHashHandoff",
    "ExistingEmbedding",
    "ItemEmbeddingError",
    "ItemEmbeddingJob",
    "ItemEmbeddingJobResult",
    "ItemEmbeddingRepositories",
    "ItemEmbeddingUpsertRow",
    "ItemRow",
    "QueueRow",
    "ScaffoldItemEmbeddingAdapter",
    "build_default_scaffold_job",
    "build_deterministic_stub_vector",
    "build_scaffold_adapter",
    "is_valid_embedding_input_hash",
    "resolve_config_version",
    "serialize_embedding_input",
]
