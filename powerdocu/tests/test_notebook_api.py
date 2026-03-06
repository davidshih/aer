from __future__ import annotations

from pathlib import Path

import pytest

from powerdocu_notebook import (
    NotebookConfig,
    build_app_report,
    build_flow_report,
    detect_package_type,
    parse_msapp,
    parse_flow_zip,
    preview_report,
    render_markdown,
)


def test_detect_package_type_for_supported_inputs(sample_msapp_path: Path, sample_flow_zip_path: Path) -> None:
    assert detect_package_type(sample_msapp_path) == "msapp"
    assert detect_package_type(sample_flow_zip_path) == "flow"


def test_detect_package_type_rejects_solution_packages(sample_solution_zip_path: Path) -> None:
    with pytest.raises(NotImplementedError, match="does not support solution packages"):
        detect_package_type(sample_solution_zip_path)


def test_parse_msapp_extracts_variables_navigation_and_resources(sample_msapp_path: Path) -> None:
    config = NotebookConfig()
    app = parse_msapp(sample_msapp_path, config)

    assert app.name == "Sample App"
    assert app.app_id == "app-001"
    assert app.global_variables == {"globalVar"}
    assert app.context_variables == {"ctxVar", "navCtx"}
    assert app.collections == {"myCollection"}
    assert app.screen_navigations["Home Screen"] == {"DetailsScreen"}
    assert "logo.png" in app.resource_bytes


def test_build_app_report_and_render_markdown(sample_msapp_path: Path, tmp_path: Path) -> None:
    config = NotebookConfig()
    report = build_app_report(parse_msapp(sample_msapp_path, config), config)
    output_dir = render_markdown(report, tmp_path)

    assert output_dir.name == "AppDoc-Sample-App"
    assert (output_dir / "index-Sample-App.md").exists()
    assert (output_dir / "controls-Sample-App.md").exists()
    assert (output_dir / "screen-Home-Screen-Sample-App.md").exists()
    assert (output_dir / "screen-navigation.mmd").read_text(encoding="utf-8").startswith("flowchart TD")

    variables_text = (output_dir / "variables-Sample-App.md").read_text(encoding="utf-8")
    assert "globalVar" in variables_text
    assert "navCtx" in variables_text

    preview = preview_report(report)
    assert "statistics" in preview
    assert not preview["screens"].empty


def test_parse_flow_zip_builds_graph_and_variables(sample_flow_zip_path: Path) -> None:
    config = NotebookConfig()
    flow = parse_flow_zip(sample_flow_zip_path, config)

    assert flow.name == "Sample Flow"
    assert flow.trigger is not None
    assert flow.trigger.connector == "office365"
    assert set(flow.actions.action_nodes) >= {
        "Initialize_variable",
        "Condition",
        "Set_variable",
        "Compose_else",
        "Switch_test",
        "Compose_A",
        "Compose_Default",
        "Final_step",
    }
    assert flow.actions.action_nodes["Initialize_variable"].order == 1


def test_build_flow_report_and_render_markdown(sample_flow_zip_path: Path, tmp_path: Path) -> None:
    config = NotebookConfig()
    report = build_flow_report(parse_flow_zip(sample_flow_zip_path, config), config)
    output_dir = render_markdown(report, tmp_path)

    assert output_dir.name == "FlowDoc-Sample-Flow"
    assert (output_dir / "index-Sample-Flow.md").exists()
    assert (output_dir / "triggersactions-Sample-Flow.md").exists()
    assert (output_dir / "actions" / "trigger-Sample-Flow.md").exists()
    assert (output_dir / "flow-overview.mmd").exists()
    assert (output_dir / "flow-detailed.mmd").exists()

    variables_text = (output_dir / "variables-Sample-Flow.md").read_text(encoding="utf-8")
    assert "counter" in variables_text

    detailed_mermaid = (output_dir / "flow-detailed.mmd").read_text(encoding="utf-8")
    assert "|Yes|" in detailed_mermaid
    assert "|No|" in detailed_mermaid

    preview = preview_report(report)
    assert "actions" in preview
    assert not preview["actions"].empty
