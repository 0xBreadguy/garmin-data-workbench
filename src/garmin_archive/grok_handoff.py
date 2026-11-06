"""Local, bounded instructions for handing an exported Page to native Grok tools.

This module never calls Grok. Hashes describe locally reconstructed source, not a
remote receipt. The 12,000-byte argument budget is a project guardrail, not a
vendor limit. Native EditCanvas rejects no-op edits, so verification uses atomic
round trips with a changing temporary comment. Exact full ReadCanvas comparison
is the final source-identity gate.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

MAX_ARGUMENT_BYTES = 12_000
MAX_CANVAS_ID_JSON_BYTES = 512
MAX_SOURCE_BYTES = 1_048_576
CANVAS_ID = "__CANVAS_ID_FROM_WRITE_RESULT__"
ANCHOR = "// __GARMIN_RECOVERY_HANDOFF_INSERT_V1__\n"
VERIFY_MARKER_PREFIX = "// __GARMIN_RECOVERY_VERIFY_V1_"
VERIFY_SLOT = "\n// __GARMIN_RECOVERY_VERIFY_V1_SLOT__\n"
PLACEHOLDER = (
    'export default function App() {\n'
    '  return <Page title="Sleep & recovery" width="column"><Section>'
    '<p>Preparing the saved recovery snapshot.</p></Section></Page>;\n'
    '}\n'
)
_INITIALIZER = "const snapshot = decodeTransport(/*__RECOVERY_SNAPSHOT__*/);"
_PART = re.compile(r'const transportPart([0-9]+) = ("(?:[^"\\\n]|\\.)*");\n')


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


def _sha(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _unique(source: str, fragment: str) -> bool:
    at = source.find(fragment)
    return bool(fragment) and at >= 0 and source.find(fragment, at + 1) < 0


def _argument_size(arguments: dict, *, reserve_id: bool = False) -> int:
    size = len(_json(arguments).encode("ascii"))
    if reserve_id and "canvas_id" in arguments:
        size += MAX_CANVAS_ID_JSON_BYTES - len(_json(arguments["canvas_id"]))
    return size


def _source_sections(source: str) -> tuple[str, list[tuple[str, str]], str]:
    """Accept only the current packaged renderer and its bounded data literals."""
    if not isinstance(source, str) or not source or len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise ValueError("Handoff requires a nonempty exported source within the 1 MiB project bound.")
    if ANCHOR in source or VERIFY_MARKER_PREFIX in source or "\r" in source or "\x00" in source:
        raise ValueError("Handoff source contains an unexpected anchor or line encoding.")
    template = (Path(__file__).with_name("ui") / "recovery.canvas.tsx").read_text(encoding="utf-8")
    if template.count(_INITIALIZER) != 1:
        raise ValueError("Packaged Grok renderer has an unsupported snapshot initializer.")
    before, after = template.split(_INITIALIZER)
    if not source.startswith(before) or not source.endswith(after):
        raise ValueError("Handoff source does not match the current packaged Grok renderer.")
    insertion = source[len(before):len(source) - len(after)]
    parts, declarations, offset = [], [], 0
    while match := _PART.match(insertion, offset):
        if int(match[1]) != len(parts) or match[1] != str(len(parts)):
            raise ValueError("Transport declarations must be sequential from transportPart0.")
        part = json.loads(match[2])
        if not part or not part.isascii() or len(part) > 2048:
            raise ValueError("Transport declarations must contain 1–2048 ASCII characters each.")
        parts.append(part)
        declarations.append(match[0])
        offset = match.end()
    names = ",".join(f"transportPart{i}" for i in range(len(parts)))
    expected = 'const snapshot = decodeTransport(JSON.parse([' + names + '].join("")));'
    if not parts or insertion[offset:] != expected:
        raise ValueError("Handoff source has an unsupported transport declaration or snapshot initializer.")
    try:
        packet = json.loads("".join(parts))
    except (ValueError, TypeError) as error:
        raise ValueError("Handoff transport does not contain a complete JSON snapshot.") from error
    if not isinstance(packet, dict) or packet.get("codec_version") != 1 or packet.get("schema_version") != 1:
        raise ValueError("Handoff transport uses an unsupported snapshot version.")

    starts = ["type Metric = ", "const transportPart0 = ", "const snapshot = ",
              "function format(", "function Lane(", "function StageDetail(",
              "function Explorer()", "export default function App()"]
    positions = []
    for start in starts:
        matches = list(re.finditer(r"^" + re.escape(start), source, re.M))
        if len(matches) != 1:
            raise ValueError("Handoff renderer has an unexpected or repeated section anchor.")
        positions.append(matches[0].start())
    if positions != sorted(positions):
        raise ValueError("Handoff renderer section anchors are out of order.")
    prefix = source[:positions[0]]
    sections = [("types-and-decoder", source[positions[0]:positions[1]])]
    sections.extend((f"transport-{i:03d}", declaration) for i, declaration in enumerate(declarations))
    labels = ["snapshot-and-constants", "format-and-helpers", "lane", "stage-and-comparison", "explorer"]
    sections.extend((label, source[positions[i + 2]:positions[i + 3]]) for i, label in enumerate(labels))
    final = source[positions[-1]:]
    if prefix + "".join(section for _, section in sections) + final != source:
        raise ValueError("Handoff section reconstruction did not preserve the source exactly.")
    return prefix, sections, final


def _step(number: int, label: str, tool: str, arguments: dict, before: str | None, after: str) -> dict:
    bound = _argument_size(arguments, reserve_id=True)
    if bound > MAX_ARGUMENT_BYTES:
        raise ValueError(f"Handoff section {label!r} exceeds the {MAX_ARGUMENT_BYTES}-byte project argument bound.")
    return {"number": number, "label": label, "tool": tool, "arguments": arguments,
            "arguments_json_bytes": _argument_size(arguments), "reserved_arguments_json_bytes": bound,
            "before_sha256": None if before is None else _sha(before), "after_sha256": _sha(after)}


def _verification(source: str, final_app: str, first_number: int) -> list[dict]:
    def marker(index: int) -> str:
        return f"\n{VERIFY_MARKER_PREFIX}{index:04d}__\n"

    def edits(fragment: str, index: int) -> dict:
        return {"canvas_id": CANVAS_ID, "edits": [
            {"old_string": fragment, "new_string": VERIFY_SLOT, "replace_all": False},
            {"old_string": VERIFY_SLOT, "new_string": fragment, "replace_all": False},
            {"old_string": marker(index), "new_string": marker(index + 1), "replace_all": False}]}

    if not _unique(source, final_app):
        raise ValueError("Cannot attach the verification comment to a unique final App.")
    current = source + marker(0)
    steps = [_step(first_number, "verification-begin", "EditCanvas", {
        "canvas_id": CANVAS_ID, "old_string": final_app,
        "new_string": final_app + marker(0), "replace_all": False}, source, current)]
    start, index = 0, 0
    while start < len(source):
        low, high, end = start + 1, len(source), start
        while low <= high:
            middle = (low + high) // 2
            if _argument_size(edits(source[start:middle], index), reserve_id=True) <= MAX_ARGUMENT_BYTES:
                end, low = middle, middle + 1
            else:
                high = middle - 1
        fragment = source[start:end]
        if end - start <= 256 or not _unique(source, fragment):
            raise ValueError("Cannot create bounded unique overlapping source verification fragments.")
        following = source + marker(index + 1)
        step = _step(first_number + len(steps), "verify-source-fragment", "EditCanvas",
                     edits(fragment, index), current, following)
        step.update({"start_character": start, "end_character": end,
                     "start_byte": len(source[:start].encode("utf-8")),
                     "end_byte": len(source[:end].encode("utf-8"))})
        steps.append(step)
        current, index = following, index + 1
        if end == len(source):
            break
        start = end - 256
    steps.append(_step(first_number + len(steps), "verification-finish", "EditCanvas", {
        "canvas_id": CANVAS_ID, "old_string": marker(index), "new_string": "",
        "replace_all": False}, current, source))
    return steps


def build_handoff_plan(source: str, title: str) -> dict:
    """Build exact sequential calls; replace only the canvas-id argument at delivery.

    Stop after any failed tool call. A failed compile rolls back its edit, so the
    next step is valid only after the current step succeeds. These local steps do
    not establish native compilation or delivery, and are not resumable blindly.
    """
    if not isinstance(title, str) or not title.strip() or len(_json(title)) > 1024:
        raise ValueError("Handoff title must be nonempty and at most 1024 serialized JSON bytes.")
    prefix, sections, final = _source_sections(source)
    current = prefix + ANCHOR + PLACEHOLDER
    steps = [_step(1, "bootstrap", "WriteCanvas", {"contents": current, "title": title}, None, current)]
    for label, section in sections:
        if not _unique(current, ANCHOR):
            raise ValueError("Handoff insertion anchor is not unique.")
        arguments = {"canvas_id": CANVAS_ID, "old_string": ANCHOR,
                     "new_string": section + ANCHOR, "replace_all": False}
        following = current.replace(ANCHOR, section + ANCHOR, 1)
        steps.append(_step(len(steps) + 1, label, "EditCanvas", arguments, current, following))
        current = following
    arguments = {"canvas_id": CANVAS_ID, "old_string": ANCHOR + PLACEHOLDER,
                 "new_string": final, "replace_all": False}
    following = current.replace(ANCHOR + PLACEHOLDER, final, 1)
    if following != source:
        raise ValueError("Handoff final source does not equal the input bytes.")
    steps.append(_step(len(steps) + 1, "activate-exported-app", "EditCanvas", arguments, current, following))

    verification = _verification(source, final, len(steps) + 1)
    return {"schema_version": 1, "title": title,
            "expected_source": {"sha256": _sha(source), "bytes": len(source.encode("utf-8")),
                                "lines": len(source.splitlines()), "encoding": "utf-8"},
            "argument_budget_bytes": MAX_ARGUMENT_BYTES,
            "argument_budget_meaning": "Conservative project guardrail; not a documented Grok host limit.",
            "canvas_id_placeholder": CANVAS_ID, "max_canvas_id_json_bytes": MAX_CANVAS_ID_JSON_BYTES,
            "execution": "Execute in order. Bind the returned canvas_id without changing source. Stop on any failure; failed compilation preserves the published revision. Reconcile ReadCanvas with the expected pre-step source before explicitly retrying the exact failed call. Never skip a failed step or silently repair a failed draft.",
            "verification_meaning": "Atomic edits round-trip each unique expected fragment and update only a temporary trailing comment; overlapping fragments cover every expected source byte. The final edit removes the comment. Local hashes are not remote hashes; exact full ReadCanvas comparison is still required to exclude extra or reordered source.",
            "steps": steps, "verification_steps": verification,
            "readback": {"tool": "ReadCanvas", "arguments": {"canvas_id": CANVAS_ID},
                         "acceptance": "Compare the complete returned source with source.canvas.tsx, preserving whitespace and order and excluding only the tool's identified wrapper. If only text inspection is available, report that limit rather than claiming byte-level identity; local hashes do not establish a remote SHA."}}


def bind_canvas_id(step: dict, canvas_id: str) -> dict:
    """Return bounded tool arguments with the actual WriteCanvas result ID."""
    if not isinstance(canvas_id, str) or not canvas_id or canvas_id == CANVAS_ID or len(_json(canvas_id)) > MAX_CANVAS_ID_JSON_BYTES:
        raise ValueError("Canvas ID must be nonempty and within the reserved serialized size.")
    arguments = dict(step["arguments"])
    if "canvas_id" in arguments:
        if arguments["canvas_id"] != CANVAS_ID:
            raise ValueError("Handoff arguments already contain an unexpected canvas ID.")
        arguments["canvas_id"] = canvas_id
    if _argument_size(arguments) > MAX_ARGUMENT_BYTES:
        raise ValueError("Bound tool arguments exceed the project size guardrail.")
    return arguments


def _check_directory_chain(directory: Path) -> None:
    for part in (*reversed(directory.parents), directory):
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise ValueError("Handoff output must not traverse symbolic links or junctions; use its canonical parent path.")
        if not part.is_dir():
            raise NotADirectoryError(str(part))


def write_handoff(new_dir: Path, source: str, title: str) -> dict:
    """Write an exclusively created private handoff directory, without networking.

    The parent must already exist and have no symlink/junction components. On
    POSIX, directory-relative exclusive opens also prevent link substitution
    during file writes. Mode bits do not establish Windows ACL confidentiality.
    A failed write can leave an incomplete private directory; no existing path is
    overwritten and the absence of plan.json marks it as incomplete.
    """
    plan = build_handoff_plan(source, title)
    target = Path(new_dir).expanduser().absolute()
    if target.name in {"", ".", ".."} or ".." in target.parts:
        raise ValueError("Handoff requires a new named directory.")
    _check_directory_chain(target.parent)
    directory_fd = None
    if os.name == "posix":
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        parent_fd = os.open(target.anchor, flags)
        try:
            for part in target.parent.parts[1:]:
                next_fd = os.open(part, flags, dir_fd=parent_fd)
                os.close(parent_fd)
                parent_fd = next_fd
            os.mkdir(target.name, 0o700, dir_fd=parent_fd)
            created = os.stat(target.name, dir_fd=parent_fd, follow_symlinks=False)
            directory_fd = os.open(target.name, flags, dir_fd=parent_fd)
            opened = os.fstat(directory_fd)
            if (created.st_dev, created.st_ino) != (opened.st_dev, opened.st_ino):
                raise OSError("Handoff directory changed during creation.")
            os.fchmod(directory_fd, 0o700)
        except BaseException:
            if directory_fd is not None:
                os.close(directory_fd)
            raise
        finally:
            os.close(parent_fd)
    else:
        target.mkdir(mode=0o700)
        _check_directory_chain(target)

    def write_file(name: str, contents: str) -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
        fd = os.open(name if directory_fd is not None else target / name, flags, 0o600,
                     **({"dir_fd": directory_fd} if directory_fd is not None else {}))
        with os.fdopen(fd, "wb") as stream:
            if os.name == "posix":
                os.fchmod(stream.fileno(), 0o600)
            stream.write(contents.encode("utf-8"))

    try:
        write_file("source.canvas.tsx", source)
        for step in [*plan["steps"], *plan["verification_steps"]]:
            name = f'{step["number"]:03d}-{step["label"]}.json'
            write_file(name, _json(step["arguments"]))
            step["arguments_file"] = name
        write_file("readback.json", _json(plan["readback"]["arguments"]))
        plan["readback"]["arguments_file"] = "readback.json"
        # Publish a complete manifest exclusively. A failed write cannot leave a
        # partial plan.json that looks ready to a later caller.
        write_file("plan.pending.json", json.dumps(plan, ensure_ascii=True, indent=2) + "\n")
        if directory_fd is not None:
            os.link("plan.pending.json", "plan.json", src_dir_fd=directory_fd,
                    dst_dir_fd=directory_fd, follow_symlinks=False)
            os.unlink("plan.pending.json", dir_fd=directory_fd)
        else:
            os.link(target / "plan.pending.json", target / "plan.json")
            (target / "plan.pending.json").unlink()
    finally:
        if directory_fd is not None:
            os.close(directory_fd)
    return {"output_dir": str(target), "plan_path": str(target / "plan.json"),
            "source_path": str(target / "source.canvas.tsx"), "expected_source": plan["expected_source"],
            "delivery_steps": len(plan["steps"]), "verification_steps": len(plan["verification_steps"]),
            "argument_budget_bytes": MAX_ARGUMENT_BYTES,
            "verification": "Local plan only; native tool execution and exact full-source readback remain required."}
