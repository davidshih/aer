from __future__ import annotations

import base64
import json
from pathlib import Path
import zipfile

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def tiny_png_bytes() -> bytes:
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9s2R8b4AAAAASUVORK5CYII="
    )


def write_zip(path: Path, entries: dict[str, bytes | str]) -> Path:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload if isinstance(payload, bytes) else payload.encode("utf-8"))
    return path


@pytest.fixture()
def sample_msapp_path(tmp_path: Path) -> Path:
    home_screen = {
        "TopParent": {
            "Name": "Home Screen",
            "Template": {"Name": "screen", "Id": "screen-template"},
            "Rules": [],
            "Children": [
                {
                    "Name": "Navigate Button",
                    "Template": {"Name": "button", "Id": "button-template"},
                    "Rules": [
                        {
                            "Property": "OnSelect",
                            "Category": "Behavior",
                            "RuleProviderType": "InvariantScript",
                            "InvariantScript": (
                                "Set(globalVar, 1); "
                                "UpdateContext({ctxVar: 2}); "
                                "Navigate(DetailsScreen, ScreenTransition.None, {navCtx: 3}); "
                                "Collect(myCollection, {Value: 1})"
                            ),
                        },
                        {
                            "Property": "Text",
                            "Category": "Appearance",
                            "RuleProviderType": "InvariantScript",
                            "InvariantScript": '"Go"',
                        },
                    ],
                }
            ],
        }
    }
    details_screen = {
        "TopParent": {
            "Name": "DetailsScreen",
            "Template": {"Name": "screen", "Id": "screen-template"},
            "Rules": [],
            "Children": [],
        }
    }
    entries = {
        "Header.json": json.dumps({"AppName": "Sample App", "ID": "app-001", "LogoFileName": "logo.png"}),
        "Properties.json": json.dumps(
            {
                "AppName": "Sample App",
                "BackgroundColor": "#ffffff",
                "AppPreviewFlagsMap": {"EnableFeatureX": True},
            }
        ),
        "Resources/PublishInfo.json": json.dumps({"Name": "Sample App"}),
        "Controls/Home Screen.json": json.dumps(home_screen),
        "Controls/DetailsScreen.json": json.dumps(details_screen),
        "References/DataSources.json": json.dumps(
            {
                "DataSources": [
                    {"Name": "Accounts", "Type": "ConnectedDataSource", "IsSampleData": False},
                    {"Name": "SampleData", "Type": "ConnectedDataSource", "IsSampleData": True},
                ]
            }
        ),
        "References/Resources.json": json.dumps(
            {
                "Resources": [
                    {
                        "Name": "logo.png",
                        "Content": "logo",
                        "ResourceKind": "LocalFile",
                        "Path": "Resources/logo.png",
                        "IsSampleData": False,
                    },
                    {
                        "Name": "SampleResource",
                        "Content": "sample",
                        "ResourceKind": "Embedded",
                        "Path": "Resources/sample.txt",
                        "IsSampleData": True,
                    },
                ]
            }
        ),
        "Resources/logo.png": tiny_png_bytes(),
    }
    return write_zip(tmp_path / "sample.msapp", entries)


@pytest.fixture()
def sample_flow_zip_path(tmp_path: Path) -> Path:
    flow_payload = {
        "name": "flow-001",
        "type": "Microsoft.Flow/flows",
        "properties": {
            "displayName": "Sample Flow",
            "connectionReferences": {
                "shared_office365": {
                    "connectionName": "abc123",
                    "source": "Embedded",
                    "id": "/providers/Microsoft.PowerApps/apis/shared_office365",
                    "tier": "NotSpecified",
                }
            },
            "definition": {
                "description": "Flow description",
                "triggers": {
                    "When_an_item_is_created": {
                        "type": "OpenApiConnectionWebhook",
                        "description": "Starts the flow",
                        "inputs": {
                            "host": {
                                "connection": {"name": "@parameters('$connections')['shared_office365']['connectionId']"}
                            },
                            "path": "/items",
                        },
                    }
                },
                "actions": {
                    "Initialize_variable": {
                        "type": "InitializeVariable",
                        "inputs": {
                            "variables": [{"name": "counter", "type": "integer", "value": 0}],
                        },
                        "runAfter": {},
                    },
                    "Condition": {
                        "type": "If",
                        "expression": {"equals": [1, 1]},
                        "actions": {
                            "Set_variable": {
                                "type": "SetVariable",
                                "inputs": {"name": "counter", "value": "@variables('counter')"},
                                "runAfter": {},
                            }
                        },
                        "else": {
                            "actions": {
                                "Compose_else": {
                                    "type": "Compose",
                                    "inputs": "No branch",
                                    "runAfter": {},
                                }
                            }
                        },
                        "runAfter": {"Initialize_variable": ["Succeeded"]},
                    },
                    "Switch_test": {
                        "type": "Switch",
                        "expression": "@variables('counter')",
                        "cases": {
                            "Case_A": {
                                "case": "A",
                                "actions": {
                                    "Compose_A": {"type": "Compose", "inputs": "A branch", "runAfter": {}}
                                },
                            }
                        },
                        "default": {
                            "actions": {
                                "Compose_Default": {
                                    "type": "Compose",
                                    "inputs": "Default branch",
                                    "runAfter": {},
                                }
                            }
                        },
                        "runAfter": {"Condition": ["Succeeded"]},
                    },
                    "Final_step": {
                        "type": "Compose",
                        "inputs": "Done @variables('counter')",
                        "runAfter": {"Switch_test": ["Succeeded"]},
                    },
                },
            },
        },
    }
    return write_zip(tmp_path / "sample-flow.zip", {"definition.json": json.dumps(flow_payload)})


@pytest.fixture()
def sample_solution_zip_path(tmp_path: Path) -> Path:
    return write_zip(
        tmp_path / "sample-solution.zip",
        {
            "solution.xml": "<ImportExportXml><SolutionManifest /></ImportExportXml>",
            "Workflows/sample.json": "{}",
        },
    )
