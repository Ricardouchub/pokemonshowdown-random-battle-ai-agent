from __future__ import annotations

from typing import Dict, List

from ps_agent.state.feature_extractor import FeatureVector


def to_dense_array(feature_vector: FeatureVector, feature_order: List[str]) -> List[float]:
    """Encode features into a dense list following feature_order."""
    return [float(feature_vector.features_dense.get(name, 0.0)) for name in feature_order]
