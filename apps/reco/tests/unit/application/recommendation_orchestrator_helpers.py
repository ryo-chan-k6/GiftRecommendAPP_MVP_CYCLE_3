"""Orchestrator 単体テスト向け Port 差し替えヘルパー。

User Meaning 配線後の ``build_default_stub_ports()`` は 004〜010 を本実装とする。
Orchestrator 本体の挙動を検証する既存テストは、当該フェーズのみ Stub に戻して
パイプラインを通す。デフォルト composition の配線検証は別テストで行う。
"""

from __future__ import annotations

from dataclasses import replace

from reco.application.recommendation_orchestrator import OrchestratorPorts
from reco.application.recommendation_orchestrator.stubs import StubPipelineModule

_USER_MEANING_STUB_PORTS: tuple[tuple[str, str, str], ...] = (
    ("user_semantic_extractor", "MOD-RECO-004", "semantic_extracted"),
    ("external_feature_estimator", "MOD-RECO-005", "external_feature_estimated"),
    ("internal_feature_estimator", "MOD-RECO-006", "internal_feature_estimated"),
    ("user_feature_generator", "MOD-RECO-007", "user_feature_generated"),
    ("user_meaning_projector", "MOD-RECO-008", "user_meaning_projected"),
    ("user_context_builder", "MOD-RECO-009", "user_context_built"),
    ("query_embedding_generator", "MOD-RECO-010", "query_embedding_generated"),
)


def ports_with_user_meaning_stubs(ports: OrchestratorPorts) -> OrchestratorPorts:
    """User Meaning フェーズ Port を StubPipelineModule に差し替える。"""
    return replace(
        ports,
        **{
            attr: StubPipelineModule(module_id=module_id, phase_name=phase_name)
            for attr, module_id, phase_name in _USER_MEANING_STUB_PORTS
        },
    )
