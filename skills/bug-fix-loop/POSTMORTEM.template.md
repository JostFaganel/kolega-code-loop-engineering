# POST-MORTEM: <Bug Title>

## Root Cause
<Why the bug existed — what assumption, logic error, or missing guard caused it>

## Investigation Findings
- Investigation scope: <NEIGHBORHOOD | SYSTEM>
- System understanding (Pass 1) accuracy: <accurate | partial | missed>
- Hypothesis chosen by Refactoring agent: <which of the 2-3 hypotheses>
- Hypothesis accuracy: <did the chosen hypothesis match the actual fix? yes | partial | no>
- Unexpected root causes explored: <were any alternative causes valid? none | yes: <which>>

## File & Line
- File: <path>
- Line: <number>

## Fix Applied
<What changed, minimally. Keep it surgical.>

## Prevention Rule
<An architectural rule to prevent this class of bug from recurring.>

Examples:
- "Never allow manual updates to the ledger table without routing through DoubleEntryValidator."
- "Set initialization flags synchronously before any await."
- "Validate all arithmetic inputs before performing the operation."
