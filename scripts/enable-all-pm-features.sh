#!/bin/bash
# One-liner to enable all PM features
# Usage: source scripts/enable-all-pm-features.sh

export FEATURE_PRD_CHANGES=true && \
export FEATURE_PRD_QUALITY_SCORING=true && \
export FEATURE_EFFORT_ESTIMATION=true && \
export FEATURE_EXPERT_ASSIST=true && \
export FEATURE_PM_PATTERN_LEARNING=true && \
echo "✅ All PM features enabled!" && \
echo "   Run: python -m context_graph.api.main"
