import json

import yaml
from agentstandards.config import CouncilConfig
from agentstandards.context import build_context
from agentstandards.models import DecisionManifest, RunState

from agentstandards_atlassian.common.confluence import document
from agentstandards_atlassian.council import sections, snapshot
from agentstandards_atlassian.engine import synchronize


def seed_run(project, binding, run_id="20260926-test"):
    config = CouncilConfig.model_validate(
        {
            "schema_version": "1.0",
            "configured": True,
            "participants": [
                {
                    "id": "codex",
                    "required": True,
                    "transport": "codex-cli",
                    "underlying_vendor": "openai",
                    "model": "test-codex",
                },
                {
                    "id": "anthropic",
                    "required": True,
                    "transport": "anthropic",
                    "underlying_vendor": "anthropic",
                    "model": "test-anthropic",
                    "api_key_env": "ANTHROPIC_API_KEY",
                },
            ],
        }
    )
    config_path = project / ".specify/extensions/agentstandards/agentstandards-config.yml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(config.model_dump(mode="json")))
    context = build_context(project, project / binding.feature_path)
    architecture = project / binding.feature_path / "architecture"
    run = architecture / "runs" / run_id
    run.mkdir(parents=True)
    (run / "artifacts").mkdir()
    (architecture / "current-run.json").write_text(json.dumps({"run_id": run_id}))
    state = RunState(
        run_id=run_id,
        feature="001-feature",
        phase="awaiting_human",
        context_hash=context.content_hash,
        config_hash=config.stable_hash(),
    )
    (run / "state.json").write_text(state.model_dump_json())
    (run / "config-snapshot.yaml").write_text(yaml.safe_dump(config.model_dump(mode="json")))
    manifest = DecisionManifest(run_id=run_id)
    (run / "decision-manifest.yaml").write_text(yaml.safe_dump(manifest.model_dump(mode="json")))
    return run


def test_matrix_reads_registry_and_does_not_claim_live_calls(project, binding):
    seed_run(project, binding)
    snap = snapshot(project, binding, "a" * 40)
    assert len(snap.reviewers) == 13 and len(snap.cells) == 52
    assert all(cell.state == "not_observed" for cell in snap.cells)
    assert snap.context_current and not snap.verified_ready


def test_changed_inputs_are_stale(project, binding):
    seed_run(project, binding)
    (project / binding.feature_path / "plan.md").write_text("changed plan")
    snap = snapshot(project, binding, "a" * 40)
    assert snap.outcome == "STALE" and not snap.verified_ready


def test_forged_ready_report_fails_core_verification(project, binding):
    run = seed_run(project, binding)
    report = {
        "schema_version": "1.0",
        "run_id": run.name,
        "feature": "001-feature",
        "status": "READY",
        "required_participants": ["codex", "anthropic"],
        "decision_manifest_path": "missing.yaml",
    }
    (run / "gate-report.yaml").write_text(yaml.safe_dump(report))
    snap = snapshot(project, binding, "a" * 40)
    assert snap.outcome == "UNVERIFIED" and not snap.verified_ready


def test_sections_escape_evidence_and_are_valid_storage(project, cfg, binding):
    seed_run(project, binding)
    snap = snapshot(project, binding, "a" * 40)
    snap.errors.append("<script>bad</script>")
    for section in sections(snap, cfg, "TEST-9"):
        document(section.body)
        assert "<script>" not in section.body


def test_no_paid_calls_and_run_sync_idempotence(project, cfg, binding, cloud, tenant, monkeypatch):
    seed_run(project, binding)
    cfg.fields = {"decision_payload": "customfield_10001", "decision_digest": "customfield_10002"}
    monkeypatch.setattr("agentstandards_atlassian.engine.revision", lambda *a, **kw: "a" * 40)
    result = synchronize(project, cfg, binding, cloud, lambda b: None)
    assert len(tenant.issues) == 3 and len(tenant.pages) == 1
    assert tenant.issues[result["run_key"]]["fields"]["status"]["name"] == "Waiting for input"
    before = len(tenant.writes)
    synchronize(project, cfg, binding, cloud, lambda b: None)
    assert len(tenant.writes) == before


def test_previous_run_is_kept_on_same_page(project, cfg, binding, cloud, tenant, monkeypatch):
    seed_run(project, binding, "first-run")
    cfg.fields = {"decision_payload": "customfield_10001", "decision_digest": "customfield_10002"}
    monkeypatch.setattr("agentstandards_atlassian.engine.revision", lambda *a, **kw: "a" * 40)
    synchronize(project, cfg, binding, cloud, lambda b: None)
    seed_run(project, binding, "second-run")
    synchronize(project, cfg, binding, cloud, lambda b: None)
    assert len(tenant.pages) == 1
    body = tenant.pages[binding.page_id]["body"]["storage"]["value"]
    assert "Previous council run: first-run" in body and "second-run" in body
