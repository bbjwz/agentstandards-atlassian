"""Optional two-package integration test; run with the peer's src on PYTHONPATH."""

import pytest

spec_engine = pytest.importorskip("spec_kit_atlassian.engine")

from spec_kit_atlassian.common.http import Cloud as SpecCloud  # noqa: E402

from agentstandards_atlassian.engine import synchronize  # noqa: E402
from tests.test_council import seed_run  # noqa: E402


@pytest.mark.parametrize("council_first", [False, True])
def test_two_packages_share_one_feature_page_and_epic(
    project, cfg, binding, cloud, tenant, monkeypatch, council_first
):
    seed_run(project, binding)
    cfg.fields = {"decision_payload": "customfield_10001", "decision_digest": "customfield_10002"}
    monkeypatch.setattr(spec_engine, "revision", lambda *a, **kw: "a" * 40)
    monkeypatch.setattr("agentstandards_atlassian.engine.revision", lambda *a, **kw: "a" * 40)
    engines = (
        [synchronize, spec_engine.synchronize]
        if council_first
        else [spec_engine.synchronize, synchronize]
    )
    for engine in engines:
        independent_binding = binding.model_copy(deep=True)
        adapter = SpecCloud(cfg, cloud.client) if engine is spec_engine.synchronize else cloud
        engine(project, cfg, independent_binding, adapter, lambda b: None)
    assert len(tenant.pages) == 1
    assert (
        sum(issue["fields"]["issuetype"]["name"] == "Epic" for issue in tenant.issues.values()) == 1
    )
    assert len(tenant.issues) == 5
    body = next(iter(tenant.pages.values()))["body"]["storage"]["value"]
    assert "Implementation plan" in body and "Architecture review" in body and "Human notes" in body

    decision = [
        i for i in tenant.issues.values() if i["fields"]["summary"].startswith("Human architecture")
    ][0]
    assert decision["fields"]["status"]["name"] == cfg.statuses["waiting"]
    before = len(tenant.writes)
    for engine in engines:
        adapter = SpecCloud(cfg, cloud.client) if engine is spec_engine.synchronize else cloud
        engine(project, cfg, binding.model_copy(deep=True), adapter, lambda b: None)
    assert len(tenant.writes) == before
