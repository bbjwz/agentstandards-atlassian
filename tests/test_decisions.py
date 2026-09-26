import json

import pytest

from agentstandards_atlassian.common.jira import Jira
from agentstandards_atlassian.common.models import Conflict
from agentstandards_atlassian.council import snapshot
from agentstandards_atlassian.decisions import approved_manifest, changes_for_decision
from tests.test_council import seed_run


@pytest.fixture
def approved(project, cfg, binding, cloud, tenant):
    seed_run(project, binding)
    snap = snapshot(project, binding, "a" * 40)
    cfg.fields = {"decision_payload": "customfield_10001", "decision_digest": "customfield_10002"}
    cfg.approver_account_ids = ["human-1"]
    jira = Jira(cloud, cfg)
    key, _ = jira.upsert(
        "decision-test",
        "agentstandards-atlassian",
        "decision",
        "Approve",
        "Review",
        binding.identity,
        metadata={"run_id": snap.run_id, "decision_digest": snap.decision_digest},
    )
    tenant.issues[key]["fields"].update(
        {
            "status": {"name": "Approved"},
            "customfield_10001": json.dumps({"selections": []}),
            "customfield_10002": snap.decision_digest,
        }
    )
    tenant.histories[key] = [
        {
            "id": "10",
            "created": "2026-09-26T10:00:00+00:00",
            "author": {"accountId": "human-1"},
            "items": [{"field": "status", "fieldId": "status", "toString": "Approved"}],
        }
    ]
    return snap, jira, key


def test_even_no_conflicts_requires_real_approval(approved, cfg, binding):
    snap, jira, key = approved
    result = approved_manifest(snap, cfg, jira, key)
    assert result["manifest"]["decided_by"] == "human-1"
    changes = changes_for_decision(binding.feature_path, result)
    assert any("runs/" in path and path.endswith("decision-manifest.yaml") for path in changes)
    assert len(changes) == 3


def test_unauthorized_approver_rejected(approved, cfg, tenant):
    snap, jira, key = approved
    tenant.histories[key][0]["author"]["accountId"] = "intruder"
    with pytest.raises(Conflict, match="not authorized"):
        approved_manifest(snap, cfg, jira, key)


def test_edit_after_approval_requires_reapproval(approved, cfg, tenant):
    snap, jira, key = approved
    tenant.histories[key].append(
        {
            "id": "11",
            "created": "2026-09-26T10:01:00+00:00",
            "author": {"accountId": "human-1"},
            "items": [{"fieldId": "customfield_10001"}],
        }
    )
    with pytest.raises(Conflict, match="changed after approval"):
        approved_manifest(snap, cfg, jira, key)


def test_superseded_digest_rejected(approved, cfg):
    snap, jira, key = approved
    snap.decision_digest = "different"
    with pytest.raises(Conflict, match="stale"):
        approved_manifest(snap, cfg, jira, key)


def test_exception_requires_all_blockers(approved, cfg, tenant):
    snap, jira, key = approved
    snap.phase, snap.blockers = "blocked", ["validator-a", "validator-b"]
    tenant.issues[key]["fields"]["customfield_10001"] = json.dumps(
        {
            "selections": [],
            "exceptions": [{"validator_artifact_ids": ["validator-a"], "reason": "accepted"}],
        }
    )
    with pytest.raises(Conflict, match="every blocking"):
        approved_manifest(snap, cfg, jira, key)


def test_exception_keeps_blocking_verdicts(approved, cfg, tenant):
    snap, jira, key = approved
    snap.phase, snap.blockers = "blocked", ["validator-a", "validator-b"]
    tenant.issues[key]["fields"]["customfield_10001"] = json.dumps(
        {
            "selections": [],
            "exceptions": [
                {"validator_artifact_ids": snap.blockers, "reason": "Risk explicitly accepted"}
            ],
        }
    )
    result = approved_manifest(snap, cfg, jira, key)
    assert result["manifest"]["status"] == "exception"
    assert result["manifest"]["exceptions"][0]["approved_by"] == "human-1"
    assert snap.blockers == ["validator-a", "validator-b"]
