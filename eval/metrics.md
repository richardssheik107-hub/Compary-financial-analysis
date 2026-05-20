# Eval Metrics (Day 1 Baseline)

## Scope

This baseline evaluates the current agent behavior on three buckets:
- single_company
- compare
- general

## Metrics

1. intent_accuracy
- Definition: predicted intent equals expected intent.
- Formula: correct_intent / total_cases

2. route_success_rate
- Definition: request returns usable output without hard failure.
- Single/general: `snapshot.found == True` and `analysis is not None`
- Compare: `comparison is not None`

3. compare_success_rate
- Definition: compare queries that produced a valid comparison object.
- Formula: compare_success / total_compare_cases

4. text_quality_pass_rate
- Definition: output text passes basic quality checks.
- Checks:
  - summary length >= 60
  - outlook length >= 70
  - summary contains all: 收入 / 利润 / 现金流
  - risk note contains: 不构成投资建议

5. empty_or_error_rate
- Definition: cases with no usable output.
- Formula: failed_cases / total_cases

## Output

`scripts/eval_runner.py` prints:
- total and bucket-level counts
- all metrics above
- top failed examples (query + reason)
