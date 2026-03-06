# ---
# jupyter:
#   jupytext:
#     formats: py:percent,ipynb
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # PowerDocu Notebook
#
# This notebook provides a pure Python implementation of the PowerDocu v1 plan:
# standalone `.msapp` files and standalone flow export `.zip` files can be parsed,
# transformed into report models, and rendered into multi-file Markdown bundles with
# Mermaid diagrams.

# %%
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
import json
import re
import shutil
import textwrap
import zipfile
from typing import Any, Iterable
import xml.etree.ElementTree as ET

import pandas as pd


try:
    ROOT_DIR = Path(__file__).resolve().parent
except NameError:
    ROOT_DIR = Path.cwd().resolve()
DEFAULTS_DIR = ROOT_DIR / "resources" / "defaults"
SUPPORTED_DIAGRAM_FORMAT = "mermaid"
DEFAULT_FLOW_ACTION_ORDER = "appearance"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".gif", ".png", ".bmp", ".tif", ".tiff", ".svg"}


# %% [markdown]
# ## Public configuration and data models

# %%
@dataclass(slots=True)
class NotebookConfig:
    changes_only: bool = True
    show_default_values: bool = False
    include_sample_data: bool = False
    flow_action_order: str = DEFAULT_FLOW_ACTION_ORDER
    diagram_format: str = SUPPORTED_DIAGRAM_FORMAT


@dataclass(slots=True)
class Expression:
    operator: str
    operands: list[Any] = field(default_factory=list)


@dataclass(slots=True)
class Rule:
    property: str = ""
    category: str = ""
    invariant_script: str = ""
    rule_provider_type: str = ""
    name_map: str = ""


@dataclass(slots=True)
class ControlPropertyReference:
    control_name: str
    screen_name: str | None
    rule_property: str


@dataclass(slots=True)
class DataSourceInfo:
    name: str
    source_type: str
    properties: list[Expression] = field(default_factory=list)

    @property
    def is_sample_data(self) -> bool:
        return expression_value_as_bool(find_expression(self.properties, "IsSampleData"))


@dataclass(slots=True)
class ResourceInfo:
    name: str
    content: str = ""
    resource_kind: str = ""
    original_path: str = ""
    properties: list[Expression] = field(default_factory=list)

    @property
    def is_sample_data(self) -> bool:
        return expression_value_as_bool(find_expression(self.properties, "IsSampleData"))


@dataclass
class ControlNode:
    name: str = ""
    control_type: str = ""
    control_id: str = ""
    properties: list[Expression] = field(default_factory=list)
    children: list["ControlNode"] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)
    parent: "ControlNode | None" = None

    def screen(self) -> "ControlNode | None":
        if self.control_type == "screen":
            return self
        if self.parent is not None:
            return self.parent.screen()
        return None

    @property
    def screen_name(self) -> str | None:
        screen = self.screen()
        return screen.name if screen else None


@dataclass(slots=True)
class AppEntity:
    app_id: str = ""
    name: str = ""
    properties: list[Expression] = field(default_factory=list)
    controls: list[ControlNode] = field(default_factory=list)
    data_sources: list[DataSourceInfo] = field(default_factory=list)
    resources: list[ResourceInfo] = field(default_factory=list)
    global_variables: set[str] = field(default_factory=set)
    context_variables: set[str] = field(default_factory=set)
    collections: set[str] = field(default_factory=set)
    variable_references: dict[str, list[ControlPropertyReference]] = field(default_factory=dict)
    screen_navigations: dict[str, set[str]] = field(default_factory=dict)
    resource_bytes: dict[str, bytes] = field(default_factory=dict)


@dataclass(slots=True)
class TriggerInfo:
    name: str
    trigger_type: str = ""
    connector: str = ""
    description: str = ""
    inputs: list[Expression] = field(default_factory=list)
    recurrence: dict[str, str] = field(default_factory=dict)
    trigger_properties: list[Expression] = field(default_factory=list)


@dataclass
class ConnectionReference:
    name: str
    source: str = ""
    connection_id: str = ""
    logical_name: str = ""
    reference_type: str = ""


@dataclass
class ActionNode:
    name: str
    description: str = ""
    expression: str = ""
    action_expression: Expression | None = None
    action_inputs: list[Expression] = field(default_factory=list)
    action_type: str = ""
    raw_inputs: str = ""
    connection: str = ""
    neighbours: list["ActionNode"] = field(default_factory=list)
    subactions: list["ActionNode"] = field(default_factory=list)
    elseactions: list["ActionNode"] = field(default_factory=list)
    node_run_after_conditions: dict[str, list[str]] = field(default_factory=dict)
    switch_relationship: dict[str, str] = field(default_factory=dict)
    order: int = 0
    parent: "ActionNode | None" = None

    def add_neighbour(self, neighbour: "ActionNode", run_after_conditions: Iterable[str]) -> None:
        if all(existing.name != neighbour.name for existing in self.neighbours):
            self.neighbours.append(neighbour)
        self.node_run_after_conditions[neighbour.name] = list(run_after_conditions)

    def add_subaction(self, subaction: "ActionNode") -> None:
        if all(existing.name != subaction.name for existing in self.subactions):
            self.subactions.append(subaction)
            subaction.parent = self

    def add_elseaction(self, elseaction: "ActionNode") -> None:
        if all(existing.name != elseaction.name for existing in self.elseactions):
            self.elseactions.append(elseaction)
            elseaction.parent = self


@dataclass(slots=True)
class ActionGraph:
    action_nodes: dict[str, ActionNode] = field(default_factory=dict)
    root_nodes: list[ActionNode] = field(default_factory=list)

    def find_or_create(self, name: str) -> ActionNode:
        if name not in self.action_nodes:
            self.action_nodes[name] = ActionNode(name=name)
        return self.action_nodes[name]

    def add_root_node(self, node: ActionNode) -> None:
        if all(existing.name != node.name for existing in self.root_nodes):
            self.root_nodes.append(node)


@dataclass(slots=True)
class FlowEntity:
    flow_id: str = ""
    name: str = ""
    description: str = ""
    flow_type: str = "Unknown"
    trigger: TriggerInfo | None = None
    actions: ActionGraph = field(default_factory=ActionGraph)
    connection_references: list[ConnectionReference] = field(default_factory=list)


@dataclass(slots=True)
class ControlRuleRow:
    category: str
    property_name: str
    value: str
    default_value: str | None = None


@dataclass(slots=True)
class ControlSection:
    title: str
    control_type: str
    rows: list[ControlRuleRow] = field(default_factory=list)


@dataclass(slots=True)
class ScreenSection:
    screen: ControlSection
    controls: list[ControlSection] = field(default_factory=list)


@dataclass(slots=True)
class AppReport:
    app_id: str
    name: str
    safe_name: str
    header: str
    metadata_rows: list[tuple[str, str]]
    statistics_rows: list[tuple[str, str]]
    app_property_rows: list[tuple[str, str]]
    preview_flag_rows: list[tuple[str, str]]
    app_info_section: ControlSection | None
    global_variables: list[str]
    context_variables: list[str]
    collections: list[str]
    variable_references: dict[str, list[ControlPropertyReference]]
    data_sources: list[DataSourceInfo]
    resources: list[ResourceInfo]
    screen_sections: list[ScreenSection]
    screen_navigation_mermaid: str
    output_folder_name: str
    include_sample_data: bool
    logo_resource_name: str | None = None
    logo_bytes: bytes | None = None
    colour_properties: tuple[str, ...] = (
        "BorderColor",
        "Color",
        "DisabledBorderColor",
        "DisabledColor",
        "DisabledFill",
        "DisabledSectionColor",
        "DisabledSelectionFill",
        "Fill",
        "FocusedBorderColor",
        "HoverBorderColor",
        "HoverColor",
        "HoverFill",
        "PressedBorderColor",
        "PressedColor",
        "PressedFill",
        "SelectionColor",
        "SelectionFill",
    )


@dataclass(slots=True)
class FlowVariableInfo:
    name: str
    variable_type: str
    initial_values: list[tuple[str, str]]
    references: list[str]


@dataclass(slots=True)
class FlowActionReport:
    action: ActionNode
    input_blocks: list[str]
    relation_rows: list[tuple[str, str]]


@dataclass(slots=True)
class FlowReport:
    flow_id: str
    name: str
    safe_name: str
    header: str
    metadata_rows: list[tuple[str, str]]
    connections: list[ConnectionReference]
    trigger: TriggerInfo
    variables: list[FlowVariableInfo]
    actions: list[FlowActionReport]
    overview_mermaid: str
    detailed_mermaid: str
    output_folder_name: str


# %% [markdown]
# ## Shared helpers

# %%
def utc_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^\w\-]+", "-", value.strip(), flags=re.ASCII)
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    return cleaned.strip("-") or "untitled"


def normalize_zip_name(name: str) -> str:
    return name.replace("\\", "/").lstrip("/").lower()


def zip_name_map(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    return {normalize_zip_name(info.filename): info for info in archive.infolist()}


def read_zip_bytes(archive: zipfile.ZipFile, names: dict[str, zipfile.ZipInfo], name: str) -> bytes | None:
    info = names.get(normalize_zip_name(name))
    if info is None:
        return None
    return archive.read(info)


def read_zip_json(archive: zipfile.ZipFile, names: dict[str, zipfile.ZipInfo], name: str) -> dict[str, Any] | None:
    payload = read_zip_bytes(archive, names, name)
    if payload is None:
        return None
    return json.loads(payload.decode("utf-8"))


def iter_zip_infos(
    archive: zipfile.ZipFile,
    prefix: str = "",
    suffix: str = "",
) -> list[zipfile.ZipInfo]:
    normalized_prefix = normalize_zip_name(prefix)
    suffix = suffix.lower()
    matched: list[zipfile.ZipInfo] = []
    for info in archive.infolist():
        normalized = normalize_zip_name(info.filename)
        if normalized.startswith(normalized_prefix) and normalized.endswith(suffix):
            matched.append(info)
    return sorted(matched, key=lambda item: normalize_zip_name(item.filename))


def stringify_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "True" if value else "False"
    if value is None:
        return ""
    return str(value)


def parse_expression(operator: str, value: Any) -> Expression:
    expression = Expression(operator=operator)
    if isinstance(value, list):
        list_operands: list[Any] = []
        for operand in value:
            if isinstance(operand, dict):
                parsed_operands = [parse_expression(child_key, child_value) for child_key, child_value in operand.items()]
                list_operands.append(parsed_operands)
            else:
                list_operands.append(stringify_scalar(operand))
        expression.operands.append(list_operands)
    elif isinstance(value, dict):
        for child_key, child_value in value.items():
            expression.operands.append(parse_expression(child_key, child_value))
    else:
        expression.operands.append(stringify_scalar(value))
    return expression


def expression_to_jsonable(expression: Expression) -> dict[str, Any]:
    def convert(value: Any) -> Any:
        if isinstance(value, Expression):
            return expression_to_jsonable(value)
        if isinstance(value, list):
            converted_items = []
            for item in value:
                if isinstance(item, list):
                    converted_items.append([convert(inner) for inner in item])
                else:
                    converted_items.append(convert(item))
            return converted_items
        return value

    if not expression.operands:
        payload: Any = ""
    elif len(expression.operands) == 1:
        payload = convert(expression.operands[0])
    else:
        payload = [convert(item) for item in expression.operands]
    return {expression.operator: payload}


def expression_to_markdown(expression: Expression) -> str:
    return "```json\n" + json.dumps(expression_to_jsonable(expression), indent=2, ensure_ascii=False) + "\n```"


def expression_value(expression: Expression | None) -> str:
    if expression is None or not expression.operands:
        return ""
    first = expression.operands[0]
    if isinstance(first, Expression):
        return json.dumps(expression_to_jsonable(first), ensure_ascii=False)
    if isinstance(first, list):
        return json.dumps(
            [
                expression_to_jsonable(item) if isinstance(item, Expression) else item
                for item in first
            ],
            ensure_ascii=False,
        )
    return stringify_scalar(first)


def expression_value_as_bool(expression: Expression | None) -> bool:
    return expression_value(expression).strip().lower() == "true"


def find_expression(expressions: Iterable[Expression], operator: str) -> Expression | None:
    for expression in expressions:
        if expression.operator == operator:
            return expression
    return None


def flatten_controls(control: ControlNode) -> list[ControlNode]:
    nodes: list[ControlNode] = []
    for child in control.children:
        nodes.append(child)
        nodes.extend(flatten_controls(child))
    return nodes


def markdown_table(headers: list[str], rows: Iterable[Iterable[str]]) -> str:
    header_row = "| " + " | ".join(headers) + " |"
    separator_row = "| " + " | ".join("---" for _ in headers) + " |"
    body_rows = []
    for row in rows:
        body_rows.append("| " + " | ".join(markdown_cell(value) for value in row) + " |")
    return "\n".join([header_row, separator_row, *body_rows])


def markdown_cell(value: Any) -> str:
    text = stringify_scalar(value)
    text = text.replace("\n", "<br>")
    return text.replace("|", "\\|")


def markdown_nav(links: list[tuple[str, str]]) -> str:
    return "\n".join(f"- [{label}]({target})" for label, target in links)


def mermaid_block(source: str) -> str:
    return f"```mermaid\n{source}\n```"


def write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    return path


def load_default_rules() -> dict[str, dict[str, str]]:
    defaults: dict[str, dict[str, str]] = {}
    control_payload = load_json_file(DEFAULTS_DIR / "ControlDefaultSetting.json")
    for entity in control_payload:
        register_default_entity(defaults, entity)
    for file_name in ("AppDefaultSetting.json", "ScreenDefaultSetting.json"):
        entity = load_json_file(DEFAULTS_DIR / file_name)
        register_default_entity(defaults, entity)
    return defaults


def register_default_entity(defaults: dict[str, dict[str, str]], entity: dict[str, Any]) -> None:
    template_name = entity.get("Template", {}).get("Name")
    if not template_name:
        return
    rules = entity.get("Rules") or []
    defaults[template_name] = {
        rule.get("Property", ""): stringify_scalar(rule.get("InvariantScript", ""))
        for rule in rules
        if rule.get("Property")
    }


def load_json_file(path: Path) -> Any:
    payload = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le"):
        try:
            return json.loads(payload.decode(encoding))
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("utf-8", payload, 0, 1, f"Could not decode JSON file: {path}")


DEFAULT_RULES = load_default_rules()


# %% [markdown]
# ## App parsing

# %%
VALID_AFTER_CHARS = {" ", ",", ")", ".", "+", "-", "/", "*", "=", ":", "}", "\n", "\r", "&"}
VALID_PRE_CHARS = {" ", "(", "+", "-", "/", "*", "=", ",", "{", "\n", "\r", "&"}


def detect_package_type(path: str | Path) -> str:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".msapp":
        return "msapp"
    if suffix != ".zip":
        raise ValueError(f"Unsupported file type: {file_path.suffix}")

    with zipfile.ZipFile(file_path) as archive:
        names = {normalize_zip_name(info.filename) for info in archive.infolist()}
    if "solution.xml" in names or any(name.startswith("workflows/") for name in names) or any(
        name.endswith(".msapp") for name in names
    ):
        raise NotImplementedError("V1 does not support solution packages.")
    if any(Path(name).name.lower() == "definition.json" for name in names):
        return "flow"
    raise ValueError("Unsupported zip package: expected a standalone flow export.")


def parse_msapp(path: str | Path, config: NotebookConfig) -> AppEntity:
    app = AppEntity()
    file_path = Path(path)
    with zipfile.ZipFile(file_path) as archive:
        names = zip_name_map(archive)
        parse_app_properties(archive, names, app)
        parse_app_controls(archive, names, app)
        parse_app_data_sources(archive, names, app)
        parse_app_resources(archive, names, app)
    return app


def parse_app_properties(archive: zipfile.ZipFile, names: dict[str, zipfile.ZipInfo], app: AppEntity) -> None:
    for file_name in ("Resources/PublishInfo.json", "Header.json", "Properties.json"):
        payload = read_zip_json(archive, names, file_name)
        if payload is None:
            continue
        for key, value in payload.items():
            expression = parse_expression(key, value)
            app.properties.append(expression)
            if key in {"AppName", "Name"} and not app.name:
                app.name = stringify_scalar(value)
            if key in {"ID", "Id"} and not app.app_id:
                app.app_id = stringify_scalar(value)
            if key == "LogoFileName" and value:
                resource_name = f"Resources/{value}"
                resource_bytes = read_zip_bytes(archive, names, resource_name)
                if resource_bytes is not None:
                    app.resource_bytes[stringify_scalar(value)] = resource_bytes
    if not app.name:
        name_expression = find_expression(app.properties, "AppName") or find_expression(app.properties, "Name")
        app.name = expression_value(name_expression) or "Unnamed App"


def parse_app_controls(archive: zipfile.ZipFile, names: dict[str, zipfile.ZipInfo], app: AppEntity) -> None:
    for info in iter_zip_infos(archive, prefix="Controls/", suffix=".json"):
        payload = json.loads(archive.read(info).decode("utf-8"))
        top_parent = payload.get("TopParent")
        if top_parent is None and payload:
            top_parent = next(iter(payload.values()))
        if not isinstance(top_parent, dict):
            continue
        app.controls.append(parse_control(top_parent, app))
    for control in app.controls:
        check_variable_usage(control, app)


def parse_control(payload: dict[str, Any], app: AppEntity, parent: ControlNode | None = None) -> ControlNode:
    control = ControlNode(parent=parent)
    template_name = ""
    template_id = ""
    variant_name = ""
    child_payloads: list[dict[str, Any]] = []
    rule_payloads: list[dict[str, Any]] = []
    for key, value in payload.items():
        if key == "Children" and isinstance(value, list):
            child_payloads = [child_payload for child_payload in value if isinstance(child_payload, dict)]
        elif key == "Rules" and isinstance(value, list):
            rule_payloads = [rule_payload for rule_payload in value if isinstance(rule_payload, dict)]
        else:
            control.properties.append(parse_expression(key, value))
            if key == "Name":
                control.name = stringify_scalar(value)
            elif key == "ID":
                control.control_id = stringify_scalar(value)
            elif key == "Template" and isinstance(value, dict):
                template_name = stringify_scalar(value.get("Name", ""))
                template_id = stringify_scalar(value.get("Id", ""))
            elif key == "VariantName":
                variant_name = stringify_scalar(value)
    control.control_type = template_name
    if control.control_type == "groupContainer" and variant_name:
        control.control_type = variant_name
    if template_id == "http://microsoft.com/appmagic/Component":
        control.control_type = "component"
    for rule_payload in rule_payloads:
        rule = Rule(
            property=stringify_scalar(rule_payload.get("Property", "")),
            category=stringify_scalar(rule_payload.get("Category", "")),
            rule_provider_type=stringify_scalar(rule_payload.get("RuleProviderType", "")),
            invariant_script=stringify_scalar(rule_payload.get("InvariantScript", "")),
            name_map=stringify_scalar(rule_payload.get("NameMap", "")),
        )
        control.rules.append(rule)
        if rule.invariant_script:
            check_for_variables(control, app, rule.invariant_script)
    for child_payload in child_payloads:
        control.children.append(parse_control(child_payload, app, parent=control))
    return control


def add_variable_reference(app: AppEntity, variable_name: str, control: ControlNode, property_name: str) -> None:
    app.variable_references.setdefault(variable_name, []).append(
        ControlPropertyReference(
            control_name=control.name or control.control_type,
            screen_name=control.screen_name,
            rule_property=property_name,
        )
    )


def contains_variable(script: str, variable_name: str) -> bool:
    index = script.find(variable_name)
    if index == -1:
        return False
    before_valid = index == 0 or script[index - 1] in VALID_PRE_CHARS
    after_index = index + len(variable_name)
    after_valid = after_index == len(script) or script[after_index] in VALID_AFTER_CHARS
    return before_valid and after_valid


def check_variable_usage(control: ControlNode, app: AppEntity) -> None:
    for rule in control.rules:
        for variable_name in app.global_variables:
            if contains_variable(rule.invariant_script, variable_name):
                add_variable_reference(app, variable_name, control, rule.property)
        for variable_name in app.context_variables:
            if contains_variable(rule.invariant_script, variable_name):
                add_variable_reference(app, variable_name, control, rule.property)
        for variable_name in app.collections:
            if contains_variable(rule.invariant_script, variable_name):
                add_variable_reference(app, variable_name, control, rule.property)
    for child in control.children:
        check_variable_usage(child, app)


def add_screen_navigation(app: AppEntity, control: ControlNode, destination_screen: str) -> None:
    screen_name = control.screen_name
    if not screen_name:
        return
    app.screen_navigations.setdefault(screen_name, set()).add(destination_screen)


def check_for_variables(control: ControlNode, app: AppEntity, input_text: str) -> None:
    stripped = strip_code_comments(input_text)
    single_line = stripped.replace("\n", "").replace("\r", "")
    for match in re.finditer(r"\s*Set\(\s*(?P<ident>\w+)\s*,", single_line):
        app.global_variables.add(match.group("ident"))

    compact = single_line.replace(" ", "")
    if "UpdateContext(" in compact:
        for index in find_all_indexes(compact, "UpdateContext("):
            if not is_within_code_comment(compact[:index]):
                for variable_name in extract_context_variable_names(compact[index:]):
                    app.context_variables.add(variable_name)

    if "Navigate(" in compact:
        for index in find_all_indexes(compact, "Navigate("):
            if is_within_code_comment(compact[:index]):
                continue
            navigate_string = compact[index:]
            closing_index = find_closing_character(navigate_string, "(", ")")
            if closing_index >= 0:
                navigate_string = navigate_string[:closing_index]
            navigate_string = navigate_string.replace("Navigate(", "", 1)
            first_param = extract_navigate_param(navigate_string)
            second_param = ""
            third_param = ""
            if first_param != navigate_string:
                remaining = navigate_string[len(first_param) + 1 :]
                second_param = extract_navigate_param(remaining)
                if second_param != remaining:
                    third_param = remaining[len(second_param) + 1 :]
                    for variable_name in extract_context_variable_names(third_param):
                        app.context_variables.add(variable_name)
            if first_param:
                add_screen_navigation(app, control, first_param)

    for match in re.finditer(r"\s*Collect\(\s*(?P<ident>\w+)\s*,\s*", single_line):
        app.collections.add(match.group("ident"))
    for match in re.finditer(r"\s*ClearCollect\(\s*(?P<ident>\w+)\s*,\s*", single_line):
        app.collections.add(match.group("ident"))


def find_all_indexes(value: str, needle: str) -> list[int]:
    indexes: list[int] = []
    start = 0
    while True:
        index = value.find(needle, start)
        if index == -1:
            return indexes
        indexes.append(index)
        start = index + len(needle)


def find_closing_character(content: str, opening: str, closing: str) -> int:
    depth = 0
    for index, char in enumerate(content):
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return index
    return -1


def is_within_code_comment(code: str) -> bool:
    last_open = code.rfind("/*")
    last_close = code.rfind("*/")
    return not (last_open == -1 or last_open < last_close)


def strip_code_comments(code: str) -> str:
    block_comments = r"/\*(.*?)\*/"
    line_comments = r"//(.*?)(\r?\n|$)"
    strings = r"\"((\\[^\n]|[^\"\n])*)\""
    verbatim_strings = r'@(\"[^\"]*\")+'
    pattern = re.compile(block_comments + "|" + line_comments + "|" + strings + "|" + verbatim_strings, re.S)

    def replace(match: re.Match[str]) -> str:
        value = match.group(0)
        if value.startswith("/*"):
            return ""
        if value.startswith("//"):
            return match.group(3) or ""
        return value

    return pattern.sub(replace, code)


def extract_navigate_param(navigate_string: str) -> str:
    if not navigate_string:
        return ""
    index_parenthesis = navigate_string.find("(")
    index_brace = navigate_string.find("{")
    opening_character = None
    if index_parenthesis == -1:
        if index_brace > -1:
            opening_character = "{"
    else:
        if index_brace > -1:
            opening_character = "(" if index_parenthesis < index_brace else "{"
        else:
            opening_character = "("

    comma_index = navigate_string.find(",")
    if opening_character is None or (comma_index > -1 and comma_index < navigate_string.find(opening_character)):
        return navigate_string[:comma_index] if comma_index > -1 else navigate_string

    closing_character = ")" if opening_character == "(" else "}"
    closing_index = find_closing_character(navigate_string, opening_character, closing_character)
    if closing_index == -1:
        return navigate_string
    comma_index = navigate_string.find(",", closing_index)
    return navigate_string[:comma_index] if comma_index > -1 else navigate_string


def extract_context_variable_names(code: str) -> list[str]:
    extracted: list[str] = []
    candidate = code
    if code.startswith("UpdateContext"):
        variable_start = code[code.find("{") :]
        closing_index = find_closing_character(variable_start, "{", "}")
        candidate = variable_start[: closing_index + 1] if closing_index >= 0 else variable_start

    if candidate.startswith("{") and candidate.endswith("}"):
        candidate = candidate[1:-1]

    while ":" in candidate:
        first_curly = candidate.find("{")
        first_round = candidate.find("(")
        first_comma = candidate.find(",")
        if first_curly > -1 or first_round > -1:
            if first_curly > -1 and (first_round == -1 or first_curly < first_round):
                if first_comma == -1 or first_curly < first_comma:
                    closing_index = find_closing_character(candidate, "{", "}")
                else:
                    closing_index = first_comma
            else:
                if first_comma == -1 or first_round < first_comma:
                    closing_index = find_closing_character(candidate, "(", ")")
                else:
                    closing_index = first_comma
            extracted.append(candidate[:closing_index].split(":", 1)[0].strip().replace("{", ""))
            skip_length = 1 if closing_index >= first_comma and first_comma != -1 else 2
            candidate = candidate[closing_index + skip_length :]
            if candidate.startswith(","):
                candidate = candidate[1:]
        else:
            for section in candidate.split(","):
                extracted.append(section.split(":", 1)[0].strip().replace("{", ""))
            candidate = ""
    return [item for item in extracted if item]


def parse_app_data_sources(archive: zipfile.ZipFile, names: dict[str, zipfile.ZipInfo], app: AppEntity) -> None:
    payload = read_zip_json(archive, names, "References/DataSources.json")
    if payload is None:
        return
    for item in payload.get("DataSources", []):
        data_source = DataSourceInfo(
            name=stringify_scalar(item.get("Name", "")),
            source_type=stringify_scalar(item.get("Type", "")),
            properties=[
                parse_expression(key, value)
                for key, value in item.items()
                if key not in {"Name", "Type"}
            ],
        )
        app.data_sources.append(data_source)


def parse_app_resources(archive: zipfile.ZipFile, names: dict[str, zipfile.ZipInfo], app: AppEntity) -> None:
    payload = read_zip_json(archive, names, "References/Resources.json")
    if payload is None:
        return
    for item in payload.get("Resources", []):
        resource = ResourceInfo(
            name=stringify_scalar(item.get("Name", "")),
            content=stringify_scalar(item.get("Content", "")),
            resource_kind=stringify_scalar(item.get("ResourceKind", "")),
            original_path=stringify_scalar(item.get("Path", "")),
            properties=[
                parse_expression(key, value)
                for key, value in item.items()
                if key not in {"Name", "Content", "ResourceKind", "Path"}
            ],
        )
        app.resources.append(resource)
        if resource.resource_kind == "LocalFile":
            extension = Path(resource.original_path).suffix.lower()
            if extension in IMAGE_EXTENSIONS:
                payload_bytes = read_zip_bytes(archive, names, resource.original_path)
                if payload_bytes is not None:
                    app.resource_bytes[resource.name] = payload_bytes


# %% [markdown]
# ## Flow parsing

# %%
def parse_flow_zip(path: str | Path, config: NotebookConfig) -> FlowEntity:
    file_path = Path(path)
    package_type = detect_package_type(file_path)
    if package_type != "flow":
        raise ValueError(f"Expected a flow package, got: {package_type}")

    with zipfile.ZipFile(file_path) as archive:
        names = zip_name_map(archive)
        flow_definition_name = next(
            (
                info.filename
                for info in archive.infolist()
                if Path(info.filename).name.lower() == "definition.json"
            ),
            None,
        )
        if flow_definition_name is None:
            raise ValueError("Could not locate definition.json in the flow package.")
        payload = json.loads(archive.read(names[normalize_zip_name(flow_definition_name)]).decode("utf-8"))
    return parse_flow_definition(payload)


def parse_flow_definition(payload: dict[str, Any]) -> FlowEntity:
    flow = FlowEntity()
    flow.flow_type = determine_flow_type(payload)
    flow.flow_id = stringify_scalar(payload.get("name", ""))
    properties = payload.get("properties", {})
    flow.name = stringify_scalar(properties.get("displayName", "")) or "Unnamed Flow"
    flow.description = stringify_scalar(properties.get("definition", {}).get("description", ""))
    if flow.flow_type in {"CloudFlow", "Unknown"}:
        parse_trigger(flow, properties.get("definition", {}).get("triggers", {}))
        parse_actions(flow, properties.get("definition", {}).get("actions", {}), parent_action=None)
        if not flow.actions.root_nodes and flow.actions.action_nodes:
            first_action = next(iter(flow.actions.action_nodes.values()))
            flow.actions.add_root_node(first_action)
        update_order_numbers(flow.actions.root_nodes)
        parse_connection_references(flow, properties.get("connectionReferences", {}))
    return flow


def determine_flow_type(payload: dict[str, Any]) -> str:
    if payload.get("schemaVersion") == "1.0.0.0" or payload.get("type") == "Microsoft.Flow/flows":
        return "CloudFlow"
    schema_version = stringify_scalar(payload.get("schemaversion", ""))
    if "ROBIN" in schema_version:
        return "DesktopFlow"
    return "Unknown"


def parse_trigger(flow: FlowEntity, triggers_payload: dict[str, Any]) -> None:
    if not triggers_payload:
        flow.trigger = TriggerInfo(name="Unknown Trigger")
        return
    trigger_name, trigger_payload = next(iter(triggers_payload.items()))
    trigger = TriggerInfo(name=trigger_name)
    for key, value in trigger_payload.items():
        if key == "description":
            trigger.description = stringify_scalar(value)
        elif key == "type":
            trigger.trigger_type = stringify_scalar(value)
        elif key == "recurrence" and isinstance(value, dict):
            trigger.recurrence = {child_key: stringify_scalar(child_value) for child_key, child_value in value.items()}
        elif key == "inputs" and isinstance(value, dict):
            parse_input_object(value, trigger.inputs, trigger, None)
        else:
            trigger.trigger_properties.append(parse_expression(key, value))
    flow.trigger = trigger


def extract_connector_name(connection_string: str) -> str:
    if connection_string.startswith("@"):
        return (
            connection_string.replace("@parameters('$connections')['shared_", "")
            .replace("']['connectionId']", "")
            .replace("']['id']", "")
        )
    return connection_string.replace("/providers/Microsoft.PowerApps/apis/shared_", "").split("_")[0]


def parse_connection_references(flow: FlowEntity, references_payload: dict[str, Any]) -> None:
    for key, value in references_payload.items():
        if not isinstance(value, dict):
            continue
        if value.get("api") is not None:
            flow.connection_references.append(
                ConnectionReference(
                    name=extract_connector_name(stringify_scalar(value["api"].get("name", ""))),
                    source=stringify_scalar(value.get("runtimeSource", "")),
                    logical_name=stringify_scalar(value.get("connection", {}).get("connectionReferenceLogicalName", "")),
                    reference_type="ConnectorReference",
                )
            )
        if value.get("connectionName") is not None:
            flow.connection_references.append(
                ConnectionReference(
                    name=extract_connector_name(stringify_scalar(value.get("id", ""))),
                    source=stringify_scalar(value.get("source", "")),
                    connection_id=key,
                    reference_type="Connector",
                )
            )


def parse_actions(
    flow: FlowEntity,
    actions_payload: dict[str, Any],
    parent_action: ActionNode | None,
    is_else_actions: bool = False,
    switch_value: str | None = None,
) -> None:
    for action_name, action_payload in actions_payload.items():
        if not isinstance(action_payload, dict):
            continue
        action = flow.actions.find_or_create(action_name)
        for key, value in action_payload.items():
            if key == "expression":
                if isinstance(value, dict):
                    action.expression = json.dumps(value, ensure_ascii=False)
                    for child_key, child_value in value.items():
                        action.action_expression = parse_expression(child_key, child_value)
                else:
                    action.expression = stringify_scalar(value)
            elif key == "inputs":
                if isinstance(value, dict):
                    parse_input_object(value, action.action_inputs, None, action)
                else:
                    action.raw_inputs = stringify_scalar(value)
            elif key == "actions" and isinstance(value, dict):
                parse_actions(flow, value, action)
            elif key == "cases" and isinstance(value, dict):
                for switch_case in value.values():
                    if isinstance(switch_case, dict):
                        parse_actions(
                            flow,
                            switch_case.get("actions", {}),
                            action,
                            False,
                            stringify_scalar(switch_case.get("case", "")),
                        )
            elif key == "default" and isinstance(value, dict):
                parse_actions(flow, value.get("actions", {}), action, False, "default")
            elif key == "runAfter" and isinstance(value, dict):
                if not value and parent_action is None:
                    flow.actions.add_root_node(action)
                else:
                    for previous_name, conditions in value.items():
                        previous_action = flow.actions.find_or_create(previous_name)
                        previous_action.add_neighbour(
                            action,
                            conditions if isinstance(conditions, list) else [stringify_scalar(conditions)],
                        )
            elif key == "else" and isinstance(value, dict):
                parse_actions(flow, value.get("actions", {}), action, True)
            elif key == "type":
                action.action_type = stringify_scalar(value)
            elif key == "description":
                action.description = stringify_scalar(value)
            elif key in {"foreach", "runtimeConfiguration", "kind", "metadata", "limit", "operationOptions", "trackedProperties"}:
                action.action_inputs.append(parse_expression(key, value))
            else:
                action.action_inputs.append(parse_expression(key, value))

        if parent_action is not None:
            if is_else_actions:
                parent_action.add_elseaction(action)
            else:
                parent_action.add_subaction(action)
            if switch_value is not None:
                parent_action.switch_relationship[action.name] = switch_value


def parse_input_object(
    input_payload: dict[str, Any],
    output_list: list[Expression],
    trigger: TriggerInfo | None,
    action: ActionNode | None,
) -> None:
    action_type = action.action_type if action is not None else ""
    for key, value in input_payload.items():
        if action_type == "ParseJson" and key == "schema":
            output_list.append(Expression(operator="schema", operands=[json.dumps(value, indent=2, ensure_ascii=False)]))
            continue
        expression = parse_expression(key, value)
        output_list.append(expression)
        if key == "host" and isinstance(value, dict):
            connection_token = value.get("connection", {}).get("name")
            if connection_token is None:
                connection_token = value.get("apiId")
            if connection_token is not None:
                connector_name = extract_connector_name(stringify_scalar(connection_token))
                if trigger is not None:
                    trigger.connector = connector_name
                if action is not None:
                    action.connection = connector_name


def update_order_numbers(root_nodes: Iterable[ActionNode]) -> None:
    counter = {"value": 1}
    visited: set[str] = set()

    def walk(node: ActionNode) -> None:
        if node.name in visited:
            return
        visited.add(node.name)
        node.order = counter["value"]
        counter["value"] += 1
        for child in node.subactions:
            walk(child)
        for child in node.elseactions:
            walk(child)
        for neighbour in node.neighbours:
            walk(neighbour)

    for node in root_nodes:
        walk(node)


# %% [markdown]
# ## Report builders

# %%
def build_app_report(app_entity: AppEntity, config: NotebookConfig) -> AppReport:
    safe = safe_name(app_entity.name)
    all_controls: list[ControlNode] = []
    for control in app_entity.controls:
        all_controls.append(control)
        all_controls.extend(flatten_controls(control))

    statistics_rows = [
        ("Screens", str(sum(1 for control in app_entity.controls if control.control_type == "screen"))),
        ("Controls (excluding Screens)", str(sum(1 for control in all_controls if control.control_type != "screen"))),
        ("Variables", str(len(app_entity.global_variables) + len(app_entity.context_variables))),
        ("Collections", str(len(app_entity.collections))),
        ("Data Sources", str(len(app_entity.data_sources))),
        ("Resources", str(len(app_entity.resources))),
    ]

    app_properties = sorted(
        [
            (expression.operator, expression_value(expression))
            for expression in app_entity.properties
            if expression.operator not in {"AppPreviewFlagsMap", "ControlCount"}
        ],
        key=lambda item: item[0],
    )
    preview_flags_expression = find_expression(app_entity.properties, "AppPreviewFlagsMap")
    preview_flag_rows = extract_named_rows(preview_flags_expression)

    app_info_control = next((control for control in app_entity.controls if control.control_type == "appinfo"), None)
    app_info_section = build_control_section(app_info_control, config) if app_info_control else None

    screen_sections: list[ScreenSection] = []
    for screen in sorted([control for control in app_entity.controls if control.control_type == "screen"], key=lambda item: item.name):
        screen_section = ScreenSection(screen=build_control_section(screen, config))
        descendants = sorted(
            [control for control in flatten_controls(screen) if control.control_type not in {"screen", "appinfo"}],
            key=lambda item: item.name,
        )
        for control in descendants:
            screen_section.controls.append(build_control_section(control, config))
        screen_sections.append(screen_section)

    logo_name = expression_value(find_expression(app_entity.properties, "LogoFileName")) or None
    logo_bytes = app_entity.resource_bytes.get(logo_name) if logo_name else None

    return AppReport(
        app_id=app_entity.app_id,
        name=app_entity.name,
        safe_name=safe,
        header=f"Power App Documentation - {app_entity.name}",
        metadata_rows=[
            ("App Name", app_entity.name),
            ("App ID", app_entity.app_id),
            ("Documentation generated at", utc_timestamp()),
        ],
        statistics_rows=statistics_rows,
        app_property_rows=app_properties,
        preview_flag_rows=preview_flag_rows,
        app_info_section=app_info_section,
        global_variables=sorted(app_entity.global_variables),
        context_variables=sorted(app_entity.context_variables),
        collections=sorted(app_entity.collections),
        variable_references={
            key: sorted(value, key=lambda item: ((item.screen_name or ""), item.control_name, item.rule_property))
            for key, value in app_entity.variable_references.items()
        },
        data_sources=sorted(app_entity.data_sources, key=lambda item: item.name),
        resources=sorted(app_entity.resources, key=lambda item: item.name),
        screen_sections=screen_sections,
        screen_navigation_mermaid=build_screen_navigation_mermaid(app_entity),
        output_folder_name=f"AppDoc-{safe}",
        include_sample_data=config.include_sample_data,
        logo_resource_name=logo_name,
        logo_bytes=logo_bytes,
    )


def build_control_section(control: ControlNode, config: NotebookConfig) -> ControlSection:
    default_rules = DEFAULT_RULES.get(control.control_type, {})
    rows: list[ControlRuleRow] = []
    for rule in sorted(control.rules, key=lambda item: (item.category, item.property)):
        default_value = default_rules.get(rule.property, "")
        if config.changes_only and default_value == rule.invariant_script:
            continue
        rows.append(
            ControlRuleRow(
                category=rule.category,
                property_name=rule.property,
                value=rule.invariant_script,
                default_value=default_value if config.show_default_values and default_value != rule.invariant_script else None,
            )
        )
    return ControlSection(title=control.name or control.control_type, control_type=control.control_type, rows=rows)


def extract_named_rows(expression: Expression | None) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    if expression is None:
        return rows
    for operand in expression.operands:
        if isinstance(operand, Expression):
            rows.append((operand.operator, expression_value(operand)))
    return rows


def build_screen_navigation_mermaid(app_entity: AppEntity) -> str:
    lines = ["flowchart TD"]
    if not app_entity.screen_navigations:
        lines.append('    app["App"]')
        return "\n".join(lines)
    for source_screen, destinations in sorted(app_entity.screen_navigations.items()):
        source_id = f"screen_{safe_name(source_screen)}"
        lines.append(f'    {source_id}["{escape_mermaid_text(source_screen)}"]')
        for destination in sorted(destinations):
            destination_id = f"screen_{safe_name(destination)}"
            lines.append(f'    {destination_id}["{escape_mermaid_text(destination)}"]')
            lines.append(f"    {source_id} --> {destination_id}")
    return "\n".join(deduplicate_preserve_order(lines))


def build_flow_report(flow_entity: FlowEntity, config: NotebookConfig) -> FlowReport:
    if flow_entity.trigger is None:
        raise ValueError("A flow report requires a trigger.")
    safe = safe_name(flow_entity.name)
    action_nodes = list(flow_entity.actions.action_nodes.values())
    if config.flow_action_order == "name":
        ordered_actions = sorted(action_nodes, key=lambda item: item.name.lower())
    else:
        ordered_actions = sorted(action_nodes, key=lambda item: item.order or 10_000)

    variables = build_flow_variables(flow_entity)
    action_reports = [build_flow_action_report(action) for action in ordered_actions]

    return FlowReport(
        flow_id=flow_entity.flow_id,
        name=flow_entity.name,
        safe_name=safe,
        header=f"Flow Documentation - {flow_entity.name}",
        metadata_rows=[
            ("Flow Name", flow_entity.name),
            ("Flow ID", flow_entity.flow_id),
            ("Description", flow_entity.description),
            ("Documentation generated at", utc_timestamp()),
            ("Number of Variables", str(len(variables))),
            ("Number of Actions", str(len(action_nodes))),
        ],
        connections=sorted(flow_entity.connection_references, key=lambda item: (item.name, item.reference_type)),
        trigger=flow_entity.trigger,
        variables=variables,
        actions=action_reports,
        overview_mermaid=build_flow_mermaid(flow_entity, detailed=False),
        detailed_mermaid=build_flow_mermaid(flow_entity, detailed=True),
        output_folder_name=f"FlowDoc-{safe}",
    )


def build_flow_variables(flow_entity: FlowEntity) -> list[FlowVariableInfo]:
    variables: list[FlowVariableInfo] = []
    action_nodes = list(flow_entity.actions.action_nodes.values())
    variable_nodes = [node for node in action_nodes if node.action_type == "InitializeVariable"]
    modify_variable_nodes = [node for node in action_nodes if node.action_type in {"SetVariable", "IncrementVariable"}]

    for node in sorted(variable_nodes, key=lambda item: item.name.lower()):
        for expression in node.action_inputs:
            if expression.operator != "variables":
                continue
            name, variable_type, initial_values = extract_flow_variable_details(expression.operands)
            references = {node.name}
            for action in modify_variable_nodes:
                if any(match_expression_name(input_expression, name) for input_expression in action.action_inputs):
                    references.add(action.name)
            for action in action_nodes:
                if variable_reference_in_action(action, name):
                    references.add(action.name)
            variables.append(
                FlowVariableInfo(
                    name=name,
                    variable_type=variable_type,
                    initial_values=sorted(initial_values.items()),
                    references=sorted(references),
                )
            )
    return variables


def extract_flow_variable_details(operands: list[Any]) -> tuple[str, str, dict[str, str]]:
    variable_name = ""
    variable_type = ""
    initial_values: dict[str, str] = {}
    for operand in operands:
        if isinstance(operand, Expression):
            if operand.operator == "name":
                variable_name = expression_value(operand)
            elif operand.operator == "type":
                variable_type = expression_value(operand)
            elif operand.operator == "value":
                if len(operand.operands) == 1 and not isinstance(operand.operands[0], list):
                    initial_values[expression_value(operand)] = ""
                else:
                    for nested in operand.operands:
                        if isinstance(nested, list):
                            for item in nested:
                                if isinstance(item, Expression):
                                    initial_values[item.operator] = expression_value(item)
                                else:
                                    initial_values[stringify_scalar(item)] = ""
                        elif isinstance(nested, Expression):
                            initial_values[nested.operator] = expression_value(nested)
                        else:
                            initial_values[stringify_scalar(nested)] = ""
        elif isinstance(operand, list) and operand and isinstance(operand[0], list):
            nested_name, nested_type, nested_values = extract_flow_variable_details(operand[0])
            variable_name = nested_name or variable_name
            variable_type = nested_type or variable_type
            initial_values.update(nested_values)
    return variable_name, variable_type, initial_values


def match_expression_name(expression: Expression, variable_name: str) -> bool:
    if expression.operator == "name" and expression_value(expression) == variable_name:
        return True
    for operand in expression.operands:
        if isinstance(operand, Expression) and match_expression_name(operand, variable_name):
            return True
        if isinstance(operand, list):
            for item in operand:
                if isinstance(item, Expression) and match_expression_name(item, variable_name):
                    return True
    return False


def variable_reference_in_action(action: ActionNode, variable_name: str) -> bool:
    reference = f"@variables('{variable_name}')"
    if reference in action.expression:
        return True
    if action.action_expression and reference in json.dumps(expression_to_jsonable(action.action_expression), ensure_ascii=False):
        return True
    if reference in action.raw_inputs:
        return True
    return any(reference in json.dumps(expression_to_jsonable(expression), ensure_ascii=False) for expression in action.action_inputs)


def build_flow_action_report(action: ActionNode) -> FlowActionReport:
    input_blocks = [expression_to_markdown(expression) for expression in action.action_inputs]
    relation_rows: list[tuple[str, str]] = []
    if action.neighbours:
        relation_rows.append(("Next Actions", ", ".join(sorted(child.name for child in action.neighbours))))
    if action.subactions:
        relation_rows.append(("Subactions", ", ".join(sorted(child.name for child in action.subactions))))
    if action.elseactions:
        relation_rows.append(("Else Actions", ", ".join(sorted(child.name for child in action.elseactions))))
    if action.switch_relationship:
        relation_rows.append(
            (
                "Switch Relationships",
                ", ".join(f"{name}: {value}" for name, value in sorted(action.switch_relationship.items())),
            )
        )
    return FlowActionReport(action=action, input_blocks=input_blocks, relation_rows=relation_rows)


def build_flow_mermaid(flow_entity: FlowEntity, detailed: bool) -> str:
    lines = ["flowchart TD"]
    if flow_entity.trigger is None:
        return "\n".join(lines)
    trigger_id = f"trigger_{safe_name(flow_entity.trigger.name)}"
    lines.append(f'    {trigger_id}["{escape_mermaid_text(flow_entity.trigger.name)}"]')
    visited: set[str] = set()

    def walk(node: ActionNode) -> None:
        if node.name in visited:
            return
        visited.add(node.name)
        node_id = f"action_{safe_name(node.name)}"
        node_label = escape_mermaid_text(f"{node.name}\\n({node.action_type or 'Action'})")
        lines.append(f'    {node_id}["{node_label}"]')
        for neighbour in node.neighbours:
            neighbour_id = f"action_{safe_name(neighbour.name)}"
            condition_label = "/".join(node.node_run_after_conditions.get(neighbour.name, []))
            if condition_label:
                lines.append(f"    {node_id} -->|{escape_mermaid_text(condition_label)}| {neighbour_id}")
            else:
                lines.append(f"    {node_id} --> {neighbour_id}")
            walk(neighbour)
        if detailed:
            for child in node.subactions:
                child_id = f"action_{safe_name(child.name)}"
                label = node.switch_relationship.get(child.name)
                if node.elseactions:
                    label = label or "Yes"
                if label:
                    lines.append(f"    {node_id} -->|{escape_mermaid_text(label)}| {child_id}")
                else:
                    lines.append(f"    {node_id} --> {child_id}")
                walk(child)
            for child in node.elseactions:
                child_id = f"action_{safe_name(child.name)}"
                label = node.switch_relationship.get(child.name) or "No"
                lines.append(f"    {node_id} -->|{escape_mermaid_text(label)}| {child_id}")
                walk(child)

    for root in flow_entity.actions.root_nodes:
        root_id = f"action_{safe_name(root.name)}"
        lines.append(f"    {trigger_id} --> {root_id}")
        walk(root)
    return "\n".join(deduplicate_preserve_order(lines))


def deduplicate_preserve_order(lines: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique.append(line)
    return unique


def escape_mermaid_text(value: str) -> str:
    return value.replace('"', "'")


# %% [markdown]
# ## Markdown rendering

# %%
def render_markdown(report: AppReport | FlowReport, output_dir: str | Path) -> Path:
    destination = Path(output_dir).resolve()
    if isinstance(report, AppReport):
        return render_app_markdown(report, destination)
    return render_flow_markdown(report, destination)


def render_app_markdown(report: AppReport, output_dir: Path) -> Path:
    folder = output_dir / report.output_folder_name
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True, exist_ok=True)
    resources_dir = folder / "resources"
    resources_dir.mkdir(exist_ok=True)

    logo_relative_path = None
    if report.logo_resource_name and report.logo_bytes:
        suffix = Path(report.logo_resource_name).suffix or ".bin"
        logo_relative_path = Path("resources") / f"applogo{suffix.lower()}"
        (folder / logo_relative_path).write_bytes(report.logo_bytes)

    safe = report.safe_name
    links = [
        ("Overview", f"index-{safe}.md"),
        ("App Details", f"appdetails-{safe}.md"),
        ("Variables", f"variables-{safe}.md"),
        ("DataSources", f"datasources-{safe}.md"),
        ("Resources", f"resources-{safe}.md"),
        ("Controls", f"controls-{safe}.md"),
    ]
    metadata_block = markdown_table(["Property", "Value"], report.metadata_rows)
    common_intro = f"# {report.header}\n\n{metadata_block}\n\n{markdown_nav(links)}\n"

    index_sections = [common_intro, "## App Statistics", markdown_table(["Component Type", "Count"], report.statistics_rows)]
    if logo_relative_path is not None:
        index_sections.append("## App Logo")
        index_sections.append(f"![App Logo]({logo_relative_path.as_posix()})")
    write_text(folder / f"index-{safe}.md", "\n\n".join(index_sections))

    details_sections = [common_intro, "## App Properties", markdown_table(["App Property", "Value"], report.app_property_rows)]
    if report.preview_flag_rows:
        details_sections.extend(["## App Preview Flags", markdown_table(["Preview Flag", "Value"], report.preview_flag_rows)])
    if report.app_info_section is not None:
        details_sections.append(render_control_section_markdown("## App Info", report.app_info_section))
    write_text(folder / f"appdetails-{safe}.md", "\n\n".join(details_sections))

    variable_sections = [common_intro, "## Variables & Collections"]
    variable_sections.append(render_variable_section("Global Variables", report.global_variables, report.variable_references))
    variable_sections.append(render_variable_section("Context Variables", report.context_variables, report.variable_references))
    variable_sections.append(render_variable_section("Collections", report.collections, report.variable_references))
    write_text(folder / f"variables-{safe}.md", "\n\n".join(variable_sections))

    datasource_sections = [common_intro, "## DataSources"]
    for datasource in report.data_sources:
        if datasource.is_sample_data and not report.include_sample_data:
            continue
        rows = [("Type", datasource.source_type)] + [
            (expression.operator, expression_value(expression)) for expression in datasource.properties
        ]
        datasource_sections.extend([f"### {datasource.name}", markdown_table(["Property", "Value"], rows)])
    write_text(folder / f"datasources-{safe}.md", "\n\n".join(datasource_sections))

    resource_sections = [common_intro, "## Resources"]
    for resource in report.resources:
        if resource.is_sample_data and not report.include_sample_data:
            continue
        rows = [
            ("ResourceKind", resource.resource_kind),
            ("Content", resource.content),
            ("Path", resource.original_path),
        ] + [(expression.operator, expression_value(expression)) for expression in resource.properties]
        resource_sections.extend([f"### {resource.name}", markdown_table(["Property", "Value"], rows)])
    write_text(folder / f"resources-{safe}.md", "\n\n".join(resource_sections))

    controls_sections = [common_intro, "## Controls Overview"]
    for screen in report.screen_sections:
        controls_sections.append(f"### [Screen: {screen.screen.title}](screen-{safe_name(screen.screen.title)}-{safe}.md)")
        controls_sections.append(render_control_outline(screen))
    controls_sections.extend(["## Screen Navigation", mermaid_block(report.screen_navigation_mermaid)])
    write_text(folder / f"controls-{safe}.md", "\n\n".join(controls_sections))
    write_text(folder / "screen-navigation.mmd", report.screen_navigation_mermaid)

    for screen in report.screen_sections:
        screen_sections = [common_intro, render_control_section_markdown(f"## {screen.screen.title}", screen.screen)]
        for control in screen.controls:
            screen_sections.append(render_control_section_markdown(f"## {control.title}", control))
        write_text(folder / f"screen-{safe_name(screen.screen.title)}-{safe}.md", "\n\n".join(screen_sections))

    return folder


def render_variable_section(
    title: str,
    variables: list[str],
    references: dict[str, list[ControlPropertyReference]],
) -> str:
    sections = [f"### {title}"]
    if not variables:
        sections.append("_None_")
        return "\n\n".join(sections)
    for variable in variables:
        sections.append(f"#### {variable}")
        refs = references.get(variable, [])
        if not refs:
            sections.append("_No references found._")
            continue
        rows = [
            (
                ref.control_name,
                ref.screen_name or "App",
                ref.rule_property,
            )
            for ref in refs
        ]
        sections.append(markdown_table(["Control", "Screen", "Property"], rows))
    return "\n\n".join(sections)


def render_control_outline(screen: ScreenSection) -> str:
    lines = [f"- {screen.screen.title} ({screen.screen.control_type})"]
    for control in screen.controls:
        lines.append(f"  - {control.title} ({control.control_type})")
    return "\n".join(lines)


def render_control_section_markdown(heading: str, section: ControlSection) -> str:
    body = [heading, f"Type: `{section.control_type}`"]
    if section.rows:
        headers = ["Category", "Property", "Value"]
        if any(row.default_value is not None for row in section.rows):
            headers.append("Default Value")
        rows: list[list[str]] = []
        for row in section.rows:
            row_values = [row.category, row.property_name, row.value]
            if len(headers) == 4:
                row_values.append(row.default_value or "")
            rows.append(row_values)
        body.append(markdown_table(headers, rows))
    else:
        body.append("_No rules captured for this control._")
    return "\n\n".join(body)


def render_flow_markdown(report: FlowReport, output_dir: Path) -> Path:
    folder = output_dir / report.output_folder_name
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True, exist_ok=True)
    actions_dir = folder / "actions"
    actions_dir.mkdir(exist_ok=True)

    safe = report.safe_name
    links = [
        ("Overview", f"index-{safe}.md"),
        ("Connections", f"connections-{safe}.md"),
        ("Variables", f"variables-{safe}.md"),
        ("Triggers & Actions", f"triggersactions-{safe}.md"),
    ]
    metadata_block = markdown_table(["Property", "Value"], report.metadata_rows)
    common_intro = f"# {report.header}\n\n{metadata_block}\n\n{markdown_nav(links)}\n"
    action_links = [(label, f"../{target}") for label, target in links]
    action_intro = f"# {report.header}\n\n{metadata_block}\n\n{markdown_nav(action_links)}\n"

    write_text(
        folder / f"index-{safe}.md",
        "\n\n".join([common_intro, "## Flow Overview", mermaid_block(report.overview_mermaid)]),
    )
    write_text(folder / "flow-overview.mmd", report.overview_mermaid)
    write_text(folder / "flow-detailed.mmd", report.detailed_mermaid)

    connection_sections = [common_intro, "## Connections"]
    for connection in report.connections:
        rows = [
            ("Connection Type", connection.reference_type),
            ("Source", connection.source),
            ("ID", connection.connection_id),
            ("Connection Reference Name", connection.logical_name),
        ]
        filtered_rows = [(key, value) for key, value in rows if value]
        connection_sections.extend([f"### {connection.name}", markdown_table(["Property", "Value"], filtered_rows)])
    write_text(folder / f"connections-{safe}.md", "\n\n".join(connection_sections))

    variable_sections = [common_intro, "## Variables"]
    for variable in report.variables:
        variable_sections.append(f"### {variable.name}")
        variable_sections.append(
            markdown_table(
                ["Property", "Value"],
                [("Name", variable.name), ("Type", variable.variable_type)],
            )
        )
        if variable.initial_values:
            variable_sections.append("#### Initial Values")
            variable_sections.append(markdown_table(["Key", "Value"], variable.initial_values))
        if variable.references:
            variable_sections.append("#### References")
            variable_sections.append(markdown_table(["Action"], [(reference,) for reference in variable.references]))
    write_text(folder / f"variables-{safe}.md", "\n\n".join(variable_sections))

    trigger_file = actions_dir / f"trigger-{safe}.md"
    trigger_sections = [
        action_intro,
        f"## {report.trigger.name}",
        markdown_table(
            ["Property", "Value"],
            [
                ("Name", report.trigger.name),
                ("Type", report.trigger.trigger_type),
                ("Connector", report.trigger.connector),
                ("Description", report.trigger.description),
            ],
        ),
    ]
    if report.trigger.recurrence:
        trigger_sections.extend(["### Recurrence", markdown_table(["Property", "Value"], report.trigger.recurrence.items())])
    if report.trigger.inputs:
        trigger_sections.append("### Inputs")
        trigger_sections.extend(expression_to_markdown(expression) for expression in report.trigger.inputs)
    if report.trigger.trigger_properties:
        trigger_sections.append("### Other Trigger Properties")
        trigger_sections.extend(expression_to_markdown(expression) for expression in report.trigger.trigger_properties)
    write_text(trigger_file, "\n\n".join(trigger_sections))

    trigger_actions_sections = [
        common_intro,
        "## Trigger",
        f"- [Trigger Details](actions/{trigger_file.name})",
        "## Actions",
        markdown_table(["Action", "Type"], [(f"[{action.action.name}](actions/{action_page_name(action.action, safe)})", action.action.action_type) for action in report.actions]),
        "## Detailed Flow Diagram",
        mermaid_block(report.detailed_mermaid),
    ]
    write_text(folder / f"triggersactions-{safe}.md", "\n\n".join(trigger_actions_sections))

    for action_report in report.actions:
        action = action_report.action
        sections = [
            action_intro,
            f"## {action.name}",
            markdown_table(
                ["Property", "Value"],
                [
                    ("Name", action.name),
                    ("Type", action.action_type),
                    ("Description", action.description),
                    ("Connection", action.connection),
                    ("Order", str(action.order)),
                ],
            ),
        ]
        if action.action_expression is not None or action.expression:
            sections.append("### Expression")
            if action.action_expression is not None:
                sections.append(expression_to_markdown(action.action_expression))
            elif action.expression:
                sections.append(f"```text\n{action.expression}\n```")
        if action_report.input_blocks:
            sections.append("### Inputs")
            sections.extend(action_report.input_blocks)
        elif action.raw_inputs:
            sections.extend(["### Inputs", f"```text\n{action.raw_inputs}\n```"])
        if action_report.relation_rows:
            sections.extend(["### Relationships", markdown_table(["Property", "Value"], action_report.relation_rows)])
        write_text(actions_dir / action_page_name(action, safe), "\n\n".join(sections))

    return folder


def action_page_name(action: ActionNode, flow_safe_name: str) -> str:
    return f"{safe_name(action.name)}-{flow_safe_name}.md"


# %% [markdown]
# ## Preview helpers

# %%
def preview_report(report: AppReport | FlowReport) -> dict[str, pd.DataFrame]:
    preview_frames: dict[str, pd.DataFrame] = {}
    if isinstance(report, AppReport):
        preview_frames["metadata"] = pd.DataFrame(report.metadata_rows, columns=["Property", "Value"])
        preview_frames["statistics"] = pd.DataFrame(report.statistics_rows, columns=["Metric", "Count"])
        preview_frames["screens"] = pd.DataFrame(
            [(section.screen.title, len(section.controls)) for section in report.screen_sections],
            columns=["Screen", "Control Count"],
        )
    else:
        preview_frames["metadata"] = pd.DataFrame(report.metadata_rows, columns=["Property", "Value"])
        preview_frames["connections"] = pd.DataFrame(
            [(item.name, item.reference_type, item.source) for item in report.connections],
            columns=["Connector", "Type", "Source"],
        )
        preview_frames["actions"] = pd.DataFrame(
            [(item.action.name, item.action.action_type, item.action.order) for item in report.actions],
            columns=["Action", "Type", "Order"],
        )

    try:
        from IPython.display import Markdown, display

        display(Markdown(f"### Preview: {report.name}"))
        for label, frame in preview_frames.items():
            display(Markdown(f"#### {label.title()}"))
            display(frame)
    except Exception:
        pass
    return preview_frames


def build_report(path: str | Path, config: NotebookConfig | None = None) -> AppReport | FlowReport:
    config = config or NotebookConfig()
    package_type = detect_package_type(path)
    if package_type == "msapp":
        return build_app_report(parse_msapp(path, config), config)
    if package_type == "flow":
        return build_flow_report(parse_flow_zip(path, config), config)
    raise ValueError(f"Unsupported package type: {package_type}")


__all__ = [
    "ActionNode",
    "ActionGraph",
    "AppEntity",
    "AppReport",
    "ConnectionReference",
    "ControlNode",
    "ControlPropertyReference",
    "DataSourceInfo",
    "Expression",
    "FlowEntity",
    "FlowReport",
    "NotebookConfig",
    "ResourceInfo",
    "TriggerInfo",
    "build_app_report",
    "build_flow_report",
    "build_report",
    "detect_package_type",
    "parse_msapp",
    "parse_flow_zip",
    "preview_report",
    "render_markdown",
]


# %% [markdown]
# ## Optional notebook run cell
#
# The cell below only executes when environment variables are provided. This keeps
# the notebook safe to run in headless tests and interactive sessions without sample
# inputs.

# %%
import os

env_input_raw = os.environ.get("POWERDOCU_NOTEBOOK_SAMPLE_INPUT", "").strip()
env_output_raw = os.environ.get("POWERDOCU_NOTEBOOK_OUTPUT_DIR", "").strip()
env_input = Path(env_input_raw) if env_input_raw else None
env_output = Path(env_output_raw) if env_output_raw else None

if env_input is not None and env_output is not None:
    config = NotebookConfig()
    notebook_report = build_report(env_input, config)
    rendered_folder = render_markdown(notebook_report, env_output)
    preview_frames = preview_report(notebook_report)
    print(f"Rendered documentation into: {rendered_folder}")
    print(f"Preview frames: {', '.join(preview_frames.keys())}")
