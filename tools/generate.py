"""Turn a focus library into one Hearts of Iron IV notification mod."""

from __future__ import annotations

from tools.focuses import FocusDef, Library
from tools.pdx import tokenize
from tools.targets import Target

CHECKS_PER_EFFECT = 200
EVENTS_PER_FILE = 200
EVENT_PICTURE = "GFX_report_event_generic_read_write"


def _indent(text: str, tabs: int) -> str:
    prefix = "\t" * tabs
    return "\n".join(prefix + line if line.strip() else "" for line in text.split("\n"))


def _brace_delta(text: str) -> int:
    delta = 0
    for kind, _value, _start, _end in tokenize(text):
        if kind == "lbrace":
            delta += 1
        elif kind == "rbrace":
            delta -= 1
    return delta


def _emit_check(prefix: str, focus: FocusDef, event_id: str) -> str:
    lines = [
        "\tif = {",
        "\t\tlimit = {",
        f"\t\t\tNOT = {{ has_country_flag = {prefix}_seen_{focus.focus_id} }}",
        f"\t\t\tNOT = {{ has_completed_focus = {focus.focus_id} }}",
        "\t\t\tNOT = {",
        "\t\t\t\tfocus_progress = {",
        f"\t\t\t\t\tfocus = {focus.focus_id}",
        "\t\t\t\t\tprogress > 0",
        "\t\t\t\t}",
        "\t\t\t}",
    ]
    for group in focus.prerequisite_groups:
        if len(group) == 1:
            lines.append(f"\t\t\thas_completed_focus = {group[0]}")
        else:
            lines.append("\t\t\tOR = {")
            for item in group:
                lines.append(f"\t\t\t\thas_completed_focus = {item}")
            lines.append("\t\t\t}")
    for raw in focus.raw_prerequisites:
        lines.append(_indent(raw, 3))
    if focus.exclusive or focus.raw_exclusive:
        lines.append("\t\t\tNOT = {")
        lines.append("\t\t\t\tOR = {")
        for item in focus.exclusive:
            lines.extend(
                [
                    f"\t\t\t\t\thas_completed_focus = {item}",
                    "\t\t\t\t\tfocus_progress = {",
                    f"\t\t\t\t\t\tfocus = {item}",
                    "\t\t\t\t\t\tprogress > 0",
                    "\t\t\t\t\t}",
                ]
            )
        for raw in focus.raw_exclusive:
            lines.append(_indent(raw, 5))
        lines.append("\t\t\t\t}")
        lines.append("\t\t\t}")
    if not focus.available_if_capitulated:
        lines.append("\t\t\tNOT = { has_capitulated = yes }")
    if focus.allow_branch:
        lines.append(_indent(focus.allow_branch, 3))
    if focus.available:
        lines.append(_indent(focus.available, 3))
    if focus.bypass:
        lines.append("\t\t\tNOT = {")
        lines.append(_indent(focus.bypass, 4))
        lines.append("\t\t\t}")
    lines.extend(
        [
            "\t\t}",
            f"\t\tset_country_flag = {prefix}_seen_{focus.focus_id}",
            f"\t\tcountry_event = {{ id = {event_id} }}",
            "\t}",
        ]
    )
    return "\n".join(lines)


def _chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)] or [[]]


def _descriptor(target: Target, supported_version: str) -> str:
    lines = ['version="0.1"', "tags={", '\t"Gameplay"', '\t"Utilities"', "}"]
    if target.dependencies:
        lines.append("dependencies={")
        for dependency in target.dependencies:
            lines.append(f'\t"{dependency}"')
        lines.append("}")
    lines.extend(
        [
            f'name="{target.name}"',
            'picture="thumbnail.png"',
            f'supported_version="{supported_version}"',
            "",
        ]
    )
    return "\n".join(lines)


def _decisions(prefix: str) -> str:
    return f"""{prefix}_notifications = {{
	{prefix}_enable = {{
		icon = generic_political_actions
		fire_only_once = no
		cost = 0
		days_re_enable = 0
		available = {{
			is_ai = no
			NOT = {{ has_country_flag = {prefix}_enabled }}
		}}
		visible = {{
			is_ai = no
			NOT = {{ has_country_flag = {prefix}_enabled }}
		}}
		complete_effect = {{
			hidden_effect = {{
				set_country_flag = {prefix}_enabled
				{prefix}_scan_focuses = yes
			}}
			custom_effect_tooltip = {prefix}_enable_tt
		}}
		ai_will_do = {{
			factor = 0
		}}
	}}

	{prefix}_disable = {{
		icon = generic_political_actions
		fire_only_once = no
		cost = 0
		days_re_enable = 0
		available = {{
			is_ai = no
			has_country_flag = {prefix}_enabled
		}}
		visible = {{
			is_ai = no
			has_country_flag = {prefix}_enabled
		}}
		complete_effect = {{
			hidden_effect = {{
				clr_country_flag = {prefix}_enabled
			}}
			custom_effect_tooltip = {prefix}_disable_tt
		}}
		ai_will_do = {{
			factor = 0
		}}
	}}
}}
"""


def _category(prefix: str) -> str:
    return f"""{prefix}_notifications = {{
	icon = generic_political_actions
	priority = 200

	allowed = {{
		always = yes
	}}

	visible = {{
		is_ai = no
	}}
}}
"""


def _on_actions(prefix: str) -> str:
    return f"""on_actions = {{
	on_daily = {{
		effect = {{
			{prefix}_scan_focuses = yes
		}}
	}}
}}
"""


def _core_loc(prefix: str) -> str:
    return (
        "l_english:\n"
        f' {prefix}_notifications:0 "Focus Notifications"\n'
        f' {prefix}_notifications_desc:0 "Events when a national focus becomes available."\n'
        f' {prefix}_enable:0 "Enable Focus Available Notifications"\n'
        f' {prefix}_enable_desc:0 "While this is on, an event opens when a national focus becomes available. Focuses you have already been told about are remembered, including if you turn notifications off and on again. Taking this also reports every focus that is available right now."\n'
        f' {prefix}_enable_tt:0 "Report every national focus that is available now, and each one that becomes available later."\n'
        f' {prefix}_disable:0 "Disable Focus Available Notifications"\n'
        f' {prefix}_disable_desc:0 "Stop those events. Focuses you have already been told about stay remembered."\n'
        f' {prefix}_disable_tt:0 "Stop focus available events."\n'
        f' {prefix}_event_title:0 "New Focus Available"\n'
        f' {prefix}_event_ok:0 "Understood."\n'
    )


def _event_block(prefix: str, event_id: str) -> str:
    return f"""country_event = {{
	id = {event_id}
	title = {prefix}_event_title
	desc = {event_id}.d
	picture = {EVENT_PICTURE}
	is_triggered_only = yes
	fire_only_once = yes

	option = {{
		name = {prefix}_event_ok
	}}
}}
"""


def _header(target: Target, note: str) -> str:
    return (
        f"# Generated for {target.keyword} ({target.name}). Do not edit.\n"
        f"# {note}\n"
    )


def render_mod(library: Library, target: Target, supported_version: str) -> dict[str, str]:
    prefix = target.id_prefix
    files: dict[str, str] = {
        "descriptor.mod": _descriptor(target, supported_version),
        f"common/decisions/{prefix}_decisions.txt": _decisions(prefix),
        f"common/decisions/categories/{prefix}_decision_categories.txt": _category(prefix),
        f"common/on_actions/{prefix}_on_actions.txt": _on_actions(prefix),
        f"localisation/english/{prefix}_l_english.yml": _core_loc(prefix),
    }

    event_for: dict[str, str] = {}
    ordered_ids: list[str] = []
    for tree_id in sorted(library.trees):
        for focus_id in library.active_ids_for_tree(tree_id):
            if focus_id not in event_for:
                event_for[focus_id] = ""
                ordered_ids.append(focus_id)

    event_files: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    for focus_id in ordered_ids:
        if len(current) >= EVENTS_PER_FILE:
            event_files.append(current)
            current = []
        namespace = f"{prefix}_e{len(event_files) + 1}"
        event_id = f"{namespace}.{len(current) + 1}"
        event_for[focus_id] = event_id
        current.append((focus_id, event_id))
    if current:
        event_files.append(current)

    loc_lines = ["l_english:"]
    for index, pairs in enumerate(event_files, start=1):
        namespace = f"{prefix}_e{index}"
        blocks = [f"add_namespace = {namespace}"]
        for focus_id, event_id in pairs:
            blocks.append(_event_block(prefix, event_id).rstrip("\n"))
            loc_lines.append(
                f' {event_id}.d:0 "The focus ${focus_id}$ is now available."'
            )
        files[f"events/{prefix}_events_{index:03}.txt"] = (
            _header(target, f"events {index}") + "\n" + "\n".join(blocks) + "\n"
        )
    if len(loc_lines) > 1:
        files[f"localisation/english/{prefix}_events_l_english.yml"] = "\n".join(loc_lines) + "\n"

    dispatch = [_header(target, "daily and on-enable scan").rstrip("\n"), f"{prefix}_scan_focuses = {{"]
    dispatch.append("\tif = {")
    dispatch.append("\t\tlimit = {")
    dispatch.append("\t\t\tis_ai = no")
    dispatch.append(f"\t\t\thas_country_flag = {prefix}_enabled")
    dispatch.append("\t\t}")
    effect_files: list[str] = []
    for tree_id in sorted(library.trees):
        active = library.active_ids_for_tree(tree_id)
        if not active:
            continue
        parts = _chunks(active, CHECKS_PER_EFFECT)
        effect_names = [f"{prefix}_tree_{tree_id}"]
        effect_names.extend(f"{prefix}_tree_{tree_id}_p{part}" for part in range(2, len(parts) + 1))
        for part_index, (effect_name, focus_ids) in enumerate(zip(effect_names, parts)):
            body = [
                _header(target, f"tree {tree_id}, part {part_index + 1}").rstrip("\n"),
                f"{effect_name} = {{",
            ]
            for focus_id in focus_ids:
                body.append(_emit_check(prefix, library.focuses[focus_id], event_for[focus_id]))
            if part_index + 1 < len(effect_names):
                body.append(f"\t{effect_names[part_index + 1]} = yes")
            body.append("}")
            effect_text = "\n".join(body) + "\n"
            if _brace_delta(effect_text) != 0:
                raise RuntimeError(f"Unbalanced braces in {effect_name}")
            effect_files.append(effect_text)
        dispatch.append("\t\tif = {")
        dispatch.append(f"\t\t\tlimit = {{ has_focus_tree = {tree_id} }}")
        dispatch.append(f"\t\t\t{effect_names[0]} = yes")
        dispatch.append("\t\t}")
    dispatch.append("\t}")
    dispatch.append("}")
    dispatch_text = "\n".join(dispatch) + "\n"
    if _brace_delta(dispatch_text) != 0:
        raise RuntimeError("Unbalanced braces in the scan dispatch")
    files[f"common/scripted_effects/{prefix}_scan_dispatch.txt"] = dispatch_text

    scan_chunks: list[list[str]] = []
    bucket: list[str] = []
    for effect_text in effect_files:
        bucket.append(effect_text)
        if len(bucket) >= 40:
            scan_chunks.append(bucket)
            bucket = []
    if bucket:
        scan_chunks.append(bucket)
    for index, bucket in enumerate(scan_chunks, start=1):
        files[f"common/scripted_effects/{prefix}_scan_{index:03}.txt"] = "\n".join(bucket)
    return files
