# Pattern Learning Guide

## Overview

Pattern Learning is an optional feature that makes the PM tool **smarter over time** by learning from expert responses. When enabled, the system:

1. **Learns from expert feedback** - When experts respond to predicted questions
2. **Extracts patterns** - Identifies when predictions were wrong or partially right
3. **Applies patterns automatically** - Uses learned patterns to improve future predictions
4. **Tracks accuracy** - Monitors how well patterns work over time

## How It Works

### 1. Expert Responds

When an expert responds to a predicted question:
- **"Correct"** → No learning needed (prediction was right)
- **"Wrong"** → System learns the correct answer
- **"Partially Right"** → System learns refinement

### 2. Pattern Extraction

The system extracts:
- **Conditions** - When this pattern applies (file paths, context, key terms)
- **Correction** - What the correct answer should be
- **Source** - Which questions this was learned from

### 3. Pattern Application

Future predictions automatically check learned patterns:
- If a similar question matches a pattern → Apply the correction
- Track how often patterns are applied
- Update accuracy scores based on results

## Enabling Pattern Learning

### Option 1: Environment Variable

```bash
export FEATURE_PM_PATTERN_LEARNING=true
```

### Option 2: Using Helper Script

The helper script includes pattern learning by default:

```bash
source scripts/enable-pm-features.sh
```

## API Endpoints

### Get Pattern Insights

```bash
GET /api/patterns/insights
```

Returns:
- Total patterns learned
- Patterns by type (correction, refinement)
- Most applied patterns
- Accuracy statistics

**Example Response:**
```json
{
  "total_patterns": 15,
  "by_type": {
    "correction": 10,
    "refinement": 5
  },
  "by_decision": {
    "wrong": 10,
    "partially_right": 5
  },
  "most_applied_patterns": [
    {
      "pattern_signature": "rate_limiting_missing",
      "decision": "wrong",
      "times_applied": 8
    }
  ]
}
```

### Learn from Expert Response

```bash
POST /api/patterns/learn
```

**Request Body:**
```json
{
  "question_id": "question-123",
  "expert_response": {
    "verdict": "wrong",
    "correct_answer": "Rate limiting is already implemented in middleware",
    "note": "The PRD is correct, no change needed",
    "should_learn": true
  }
}
```

**Response:**
```json
{
  "learned": true,
  "pattern_id": "pattern-456",
  "pattern_description": "Correction for: Will engineering ask about rate limiting?",
  "applies_when": "file:api/auth.py AND context:authentication"
}
```

## Use Cases

### Use Case 1: Correcting False Positives

**Scenario:** System predicts "Engineering will ask about rate limiting" but rate limiting already exists.

**Expert Response:**
- Verdict: `"wrong"`
- Correct Answer: `"Rate limiting already implemented"`

**Result:** System learns this pattern and won't predict this question when rate limiting code exists.

### Use Case 2: Refining Predictions

**Scenario:** System predicts "Security will ask about encryption" but encryption is mentioned, just not detailed enough.

**Expert Response:**
- Verdict: `"partially_right"`
- Note: `"Encryption is mentioned but needs key management details"`

**Result:** System learns to suggest adding key management details when encryption is mentioned.

### Use Case 3: Team-Specific Patterns

**Scenario:** Engineering team always asks about error handling, but it's not in the PRD.

**Expert Response:**
- Verdict: `"correct"`
- Note: `"Engineering always asks about error handling"`

**Result:** System learns to always predict this question for engineering team when error handling is missing.

## Pattern Storage

Patterns are currently stored **in-memory** (for this phase). In production, you would:

1. **Store in database** - Persist patterns across restarts
2. **Version patterns** - Track pattern evolution
3. **A/B test patterns** - Compare old vs new patterns
4. **Pattern analytics** - Monitor pattern effectiveness

## Benefits

### For PMs
- ✅ **Fewer false positives** - System learns what NOT to predict
- ✅ **Better suggestions** - Predictions improve over time
- ✅ **Team-specific insights** - Learns each team's concerns

### For Experts
- ✅ **Less repetitive questions** - System learns from your feedback
- ✅ **Faster validation** - Patterns applied automatically
- ✅ **Your expertise scales** - One response helps future predictions

### For the System
- ✅ **Self-improving** - Gets smarter without code changes
- ✅ **Accurate patterns** - Tracks what works
- ✅ **Scalable learning** - Learns from all expert interactions

## Monitoring

### Check Pattern Insights

```bash
curl http://localhost:8000/api/patterns/insights
```

### View Learned Patterns

Patterns are applied automatically, but you can see insights:
- Total patterns learned
- Most applied patterns
- Accuracy scores

## Best Practices

### 1. Enable Early
Enable pattern learning from the start to begin learning immediately.

### 2. Expert Feedback Quality
- Provide clear, specific responses
- Include correct answers when verdict is "wrong"
- Add notes for "partially_right" verdicts

### 3. Review Patterns
Periodically check pattern insights to see what's being learned.

### 4. Pattern Accuracy
Monitor accuracy scores - patterns with low accuracy may need refinement.

## Example Workflow

1. **PM creates review** → System generates predicted questions
2. **PM asks expert** → "Will engineering ask about rate limiting?"
3. **Expert responds** → "Wrong - rate limiting already exists"
4. **System learns** → Creates pattern: "Don't predict rate limiting when code exists"
5. **Future reviews** → Pattern automatically applied, fewer false positives

## Troubleshooting

### Patterns Not Learning?

1. **Check feature flag:**
   ```bash
   echo $FEATURE_PM_PATTERN_LEARNING
   # Should output: true
   ```

2. **Check expert response format:**
   - Must include `verdict` ("wrong" or "partially_right")
   - Must include `should_learn: true`
   - For "wrong": must include `correct_answer`

3. **Check API response:**
   ```bash
   curl -X POST http://localhost:8000/api/patterns/learn \
     -H "Content-Type: application/json" \
     -d '{"question_id": "...", "expert_response": {...}}'
   ```

### Patterns Not Applying?

- Patterns are applied automatically during PRD change generation
- Check pattern insights to see if patterns exist
- Verify pattern conditions match current context

## Integration with Other Features

Pattern Learning works with:
- ✅ **PRD Changes** - Patterns improve change suggestions
- ✅ **Expert Assist** - Learns from expert responses
- ✅ **Quality Scoring** - Better predictions = better scores

## Future Enhancements

Potential improvements:
- [ ] Pattern versioning
- [ ] Pattern A/B testing
- [ ] Pattern analytics dashboard
- [ ] Pattern sharing across teams
- [ ] ML-based pattern matching

## Summary

Pattern Learning makes your PM tool **smarter over time** by:
- Learning from expert feedback
- Extracting correction and refinement patterns
- Applying patterns automatically to future predictions
- Tracking accuracy and effectiveness

**Enable it to start learning from day one!**

```bash
export FEATURE_PM_PATTERN_LEARNING=true
```
