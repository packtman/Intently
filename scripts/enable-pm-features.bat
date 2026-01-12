@echo off
REM Enable all PM-focused features for the Unified PM Tool
REM 
REM Usage:
REM   scripts\enable-pm-features.bat

set FEATURE_PRD_CHANGES=true
set FEATURE_PRD_QUALITY_SCORING=true
set FEATURE_EFFORT_ESTIMATION=true
set FEATURE_EXPERT_ASSIST=true
set FEATURE_PM_PATTERN_LEARNING=true

echo ✅ PM features enabled:
echo    - PRD Changes (diff-style suggestions)
echo    - PRD Quality Scoring
echo    - Effort Estimation
echo    - Expert Assist
echo    - PM Pattern Learning (makes system smarter over time)
echo.
echo 📚 Learn more: docs\PATTERN_LEARNING_GUIDE.md
echo.
echo Start the backend server to use these features.
