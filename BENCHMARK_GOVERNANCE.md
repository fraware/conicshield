# Benchmark Governance

This document defines how ConicShield benchmark results become trusted, published, replaced, deprecated, or rejected.

Moreau install/runtime policy is defined in `docs/MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md`. This governance document assumes vendor-native claims are produced only in qualified vendor environments.

## 1. Governing principle

A benchmark result is not just a score. It is a governed claim about a stable task.

Three things must be kept separate:

1. the task contract
2. the reference fixture
3. the implementation under test

If those drift together, comparisons lose meaning.

## 2. Benchmark family

A benchmark family is the unit of longitudinal comparison.

Example:
`conicshield-transition-bank-v1`

A family version changes only when the semantic task contract changes materially.

Examples of semantic task changes:
- action semantics change
- reward semantics change
- transition-bank construction semantics change
- observation/state contract changes
- reference arm definition changes

If any of the above change materially, do not overwrite scores under the old family. Publish a new family version.

## 3. Task contract

The task contract includes:
- environment name
- action space
- observation/state contract
- reward semantics
- transition-bank semantics
- arm definitions required for publication

A run may only replace the current published run if it preserves the same task contract version within the same benchmark family.

## 4. Reference fixture

The reference fixture is the frozen gold bundle used for native parity checks.

The fixture is versioned separately from the benchmark family.

A fixture may be regenerated only under the fixture regeneration policy. Regeneration does not by itself authorize score replacement.

## 5. Result states

### Experimental
A run that executed successfully but has no governance standing.

### Candidate
A run whose artifact bundle validates and is reviewable.

### Review-locked
A candidate that is comparable to the current published run because it matches:
- benchmark family
- task contract version
- required arm coverage
- declared run-spec coverage

### Published
A review-locked run that has passed all required gates and has been explicitly promoted.

### Deprecated
A formerly published run retained for historical inspection but no longer current.

## 6. Gates

### Artifact gate
Green only if:
- run bundle validates
- all schemas validate
- all invariants pass
- required artifacts are present

### Parity gate
Required for native compiled publication.
Green only if the native compiled implementation matches the frozen reference fixture within the approved tolerances.

### Promotion gate
Green only if the run meets the benchmark-family promotion thresholds.

## 7. Promotion policy

A run may become the current published result only if:

1. artifact gate is green
2. run is review-locked
3. promotion gate is green
4. if the run includes `shielded-native-moreau` as a publishable arm, parity gate is green

A native compiled arm may appear on the endorsed benchmark card only when all of the above hold.

## 8. Replacement policy

### Same-family replacement
A run may replace the current published run if:
- benchmark family is unchanged
- task contract version is unchanged
- required gates are green

### New-family publication
If the task contract changes materially, the result must be published as a new benchmark family version.
It must not overwrite the current family score.

## 9. Regression policy

### Critical regression
Examples:
- invalid artifact bundle
- failed parity
- missing required arm
- fixture provenance violation
- family/task mismatch in a claimed replacement

Action:
block publication immediately

### Major regression
Examples:
- rule-violation rate worsens materially
- matched-action rate worsens materially
- solve-failure rate becomes nonzero
- reward retention falls below threshold

Action:
do not promote; retain as candidate only

### Minor regression
Examples:
- modest latency drift without behavioral regression
- modest intervention-norm drift

Action:
record and review; promotion depends on policy thresholds

### Informational drift
Examples:
- metadata-only changes
- documentation-only changes

Action:
record only

## 10. Publication rule

The benchmark card must identify:
- benchmark family
- task contract version
- fixture version
- current published run id
- whether the native compiled arm is endorsed

Recommended footer:

“This result is the current published run for the declared benchmark family. Publication required a valid artifact bundle, green parity status where applicable, green promotion status, and family-level compatibility with the existing task contract.”

## 11. Required repository files

- `benchmarks/registry.json`
- `benchmarks/releases/<family_id>/CURRENT.json`
- `benchmarks/releases/<family_id>/HISTORY.json`
- immutable run bundles under `benchmarks/runs/<run_id>/`

## 12. Human review requirement

No run becomes published automatically just because CI is green.

Promotion requires a short release decision record that states:
- what changed
- why the run is comparable to the current published run
- which gates passed
- whether anything regressed

## 13. Family-version bump rule

A new benchmark family version is mandatory when the semantic task contract changes.

Examples:
- action space changes
- state contract changes
- reward semantics change
- transition-bank construction semantics change
- reference arm definition changes
- required benchmark-arm set changes

In these cases:
- do not overwrite the current family result
- initialize a new family version
- publish under the new family only
- retain the old family history intact
