"""Human-readable formatting for CLI output."""

import textwrap

from vermyth.schema import VerdictType  # noqa: F401 — required schema import per brief


def resonance_bar(score: float, width: int = 15) -> str:
    s = max(0.0, min(1.0, float(score)))
    filled = int(round(s * width))
    filled = max(0, min(width, filled))
    return "█" * filled + "░" * (width - filled)


def format_cast_result(result: dict) -> str:
    sigil_name = result["sigil_name"]
    aspects = " + ".join(result["sigil_aspects"])
    verdict = result["verdict"]
    resonance = float(result["resonance"])
    bar = resonance_bar(resonance)
    effect = result["effect_description"]
    note = result["casting_note"]
    proj = result["projection_method"]
    conf = float(result["intent_confidence"])
    cast_id = result["cast_id"]

    wrapped_note = textwrap.fill(
        note,
        width=68,
        initial_indent="",
        subsequent_indent=" " * 12,
    )
    note_lines = wrapped_note.splitlines()
    note_block = "Note        " + (note_lines[0] if note_lines else "")
    for ln in note_lines[1:]:
        note_block += "\n            " + ln

    lines = [
        f"Sigil       {sigil_name}  [{aspects}]",
        f"Verdict     {verdict}",
        f"Resonance   {resonance:.4f}  {bar}",
        f"Effect      {effect}",
        note_block,
        f"Projection  {proj}  confidence: {conf:.4f}",
        f"Cast ID     {cast_id}",
    ]
    out = "\n".join(lines)
    lin = result.get("lineage")
    if lin is not None:
        out += (
            "\n\n"
            f"Lineage     depth: {lin['depth']}  branch: {lin['branch_id']}\n"
            f"            parent: {lin['parent_cast_id']}"
        )
    return out


def format_cast_table(results: list[dict]) -> str:
    if not results:
        return "No results."
    hdr = f"{'CAST ID':<14}{'SIGIL':<21}{'VERDICT':<11}RESONANCE"
    sep = "-" * len(hdr)
    parts = [hdr, sep]
    for r in results:
        cid = r["cast_id"][:14]
        sn = r["sigil_name"][:20]
        ver = str(r["verdict"])[:11]
        res = float(r["resonance"])
        row = f"{cid:<14}{sn:<21}{ver:<11}{res:.4f}"
        parts.append(row)
    return "\n".join(parts)


def format_search_table(
    results: list[dict], similarities: list[float] | None = None
) -> str:
    if similarities is None:
        return format_cast_table(results)
    if not results:
        return "No results."
    hdr = (
        f"{'CAST ID':<14}{'SIGIL':<21}{'VERDICT':<11}"
        f"RESONANCE  SIMILARITY"
    )
    sep = "-" * len(hdr)
    parts = [hdr, sep]
    for r, sim in zip(results, similarities, strict=True):
        cid = r["cast_id"][:14]
        sn = r["sigil_name"][:20]
        ver = str(r["verdict"])[:11]
        res = float(r["resonance"])
        row = f"{cid:<14}{sn:<21}{ver:<11}{res:.4f}     {float(sim):.4f}"
        parts.append(row)
    return "\n".join(parts)


def format_seed_table(seeds: list[dict]) -> str:
    if not seeds:
        return "No seeds found."
    hdr = (
        f"{'SEED ID':<14}{'ASPECTS':<30}{'COUNT':<7}"
        f"RESONANCE  COHERENCE  STATUS"
    )
    sep = "-" * len(hdr)
    parts = [hdr, sep]
    for s in seeds:
        sid = s["seed_id"][:14]
        asp_raw = " + ".join(sorted(s["aspects"]))
        asp = (asp_raw[:29] + " ")[:30]
        cnt = s["observed_count"]
        res = float(s["mean_resonance"])
        coh = float(s["coherence_rate"])
        status = "crystallized" if s["crystallized"] else "accumulating"
        row = (
            f"{sid:<14}{asp:<30}{cnt:<7}{res:.4f}     {coh:.4f}     {status}"
        )
        parts.append(row)
    return "\n".join(parts)
