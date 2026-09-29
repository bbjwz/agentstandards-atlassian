# Jira decision configuration

Use the existing project board. Map `council` and `decision` roles to existing standard work
item types, initially Task. Configure an approval transition (default destination `Approved`)
for decision requests. Limit that transition to the appropriate project role. The integration
also independently checks the actual changelog actor against configured account IDs.

Create two custom text fields on the decision issue screen:

```yaml
fields:
  decision_payload: customfield_10001
  decision_digest: customfield_10002
  # Optional text fields for board cards:
  council_phase: customfield_10003
  architecture_outcome: customfield_10004
approver_account_ids:
  - YOUR_AUTHORIZED_ATLASSIAN_ACCOUNT_ID
decision_status: Approved
```

The digest is generated and managed by the integration. Do not edit it. The payload is human-owned.
Version 0.1 uses a structured JSON text field so native Jira is sufficient; there is no custom
Forge form. The request description contains available conflicts/options and the Confluence link.

Example selection payload (use real IDs from that run):

```json
{
  "selections": [
    {
      "conflict_id": "conflict-1",
      "selected_proposal_ids": ["proposal-a"],
      "rationale": "Meets the operational constraints with the least additional complexity."
    }
  ]
}
```

A run with no conflicts still requires an authorized approval; its payload is `{"selections": []}`.
For an exception, retain selections and add:

```json
{
  "selections": [],
  "exceptions": [
    {
      "validator_artifact_ids": ["EXACT-BLOCKING-VALIDATOR-ARTIFACT-ID"],
      "reason": "Explicit human risk acceptance and remediation rationale."
    }
  ]
}
```

All blocking required-validator IDs must be covered. The user does not supply approver identity
or approval time; those are derived from Jira's authenticated changelog event. There is no
automatic approval by comment text or a status flag without that event.

Synchronization creates a new decision identity when the underlying architecture digest changes.
Older requests cannot authorize the current run. Approval reconciliation rereads the issue and
rejects changes after approval or while the request is being read. An audit JSON file accompanies
the run-scoped and feature-level decision manifests in the draft PR.

Run reconciliation through the serialized worker; it can discover the current approved request
or accept an explicit `--decision-key`. No approval means a no-op, not an error or a paid call.
