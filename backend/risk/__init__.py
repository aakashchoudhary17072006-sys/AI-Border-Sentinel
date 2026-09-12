"""
AI Border Sentinel - Step 5: Explainable Rule-Based Risk Engine Module
Computes transparent prototype suspicion scores (0-100) with detailed reasons.
"""

from risk.risk_engine import (
    LEVEL_CRITICAL,
    LEVEL_MONITOR,
    LEVEL_NORMAL,
    LEVEL_SUSPICIOUS,
    RiskConfig,
    RiskEngine,
)

__all__ = [
    "RiskEngine",
    "RiskConfig",
    "LEVEL_NORMAL",
    "LEVEL_MONITOR",
    "LEVEL_SUSPICIOUS",
    "LEVEL_CRITICAL",
]
