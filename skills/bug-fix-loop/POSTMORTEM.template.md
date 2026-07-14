# POST-MORTEM: <Bug Title>

## Root Cause
<Why the bug existed — what assumption, logic error, or missing guard caused it>

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
