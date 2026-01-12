#!/bin/bash
# Enable all PM-focused features for the Unified PM Tool
# 
# Usage:
#   source scripts/enable-pm-features.sh
#   # or
#   . scripts/enable-pm-features.sh

export FEATURE_PRD_CHANGES=true
export FEATURE_PRD_QUALITY_SCORING=true
export FEATURE_EFFORT_ESTIMATION=true
export FEATURE_EXPERT_ASSIST=true
export FEATURE_PM_PATTERN_LEARNING=true

echo "✅ PM features enabled:"
echo "   - PRD Changes (diff-style suggestions)"
echo "   - PRD Quality Scoring"
echo "   - Effort Estimation"
echo "   - Expert Assist"
echo "   - PM Pattern Learning (makes system smarter over time)"
echo ""
echo "📚 Learn more: docs/PATTERN_LEARNING_GUIDE.md"
echo ""
echo "Start the backend server to use these features."
