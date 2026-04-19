"""Human-readable formatting for CLI output."""

import json
import textwrap

from vermyth.schema import VerdictType  # noqa: F401 — required schema import per brief


def resonance_bar(score: float, width: int = 15) -> str:
    s = max(0.0, min(1.0, float(score)))
    filled = int(round(s * width))
    filled = max(0, min(width, filled))
    return "█" * filled + "░" * (width - filled)


def format_arcane_transcript(transcript: dict) -> str:
    """Pretty-print a presentation-only arcane transcript (same structure as MCP ``arcane_transcript``)."""
    header = "--- Arcane transcript (presentation-only; derived from cast result fields) ---"
    return header + "\n" + json.dumps(transcript, indent=2)


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
    prov = result.get("provenance")
    if prov is not None:
        src = prov.get("source")
        if src == "crystallized":
            nm = prov.get("crystallized_sigil_name")
            gen = prov.get("generation")
            lines.append(f"Provenance  crystallized  gen={gen}  sigil={nm}")
        elif src == "base":
            lines.append("Provenance  base")
        elif src == "fluid":
            lines.append("Provenance  fluid")
    out = "\n".join(lines)
    lin = result.get("lineage")
    if lin is not None:
        out += (
            "\n\n"
            f"Lineage     depth: {lin['depth']}  branch: {lin['branch_id']}\n"
            f"            parent: {lin['parent_cast_id']}"
        )
        div = lin.get("divergence")
        if div:
            st = str(div.get("status", "") or "")
            l2 = float(div.get("l2_magnitude", 0.0) or 0.0)
            cd = float(div.get("cosine_distance", 0.0) or 0.0)
            out += f"\n            divergence: {st}  L2={l2:.4f}  cosine_distance={cd:.4f}"
        else:
            dv = lin.get("divergence_vector")
            if dv:
                mag = sum(float(x) * float(x) for x in dv) ** 0.5
                out += f"\n            divergence L2: {mag:.4f}"
    return out


def format_crystallized_sigils_table(sigils: list[dict]) -> str:
    if not sigils:
        return "No crystallized sigils."
    hdr = f"{'NAME':<26}{'ASPECTS':<30}{'EFFECT':<16}{'CEILING':<9}{'GEN':<5}CRYSTALLIZED_AT"
    sep = "-" * len(hdr)
    parts = [hdr, sep]
    for r in sigils:
        nm = str(r.get("name", ""))[:25]
        sig = r.get("sigil", {}) or {}
        asp_raw = " + ".join(sorted(sig.get("aspects", []) or []))
        asp = (asp_raw[:29] + " ")[:30]
        eff = str(sig.get("effect_class", "") or "")[:15]
        ceil = float(sig.get("resonance_ceiling", 0.0) or 0.0)
        gen = int(r.get("generation", 1) or 1)
        ts = str(r.get("crystallized_at", "") or "")
        parts.append(f"{nm:<26}{asp:<30}{eff:<16}{ceil:<9.2f}{gen:<5}{ts}")
    return "\n".join(parts)


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


def format_lineage_chain(results: list[dict]) -> str:
    if not results:
        return "No lineage."
    lines: list[str] = []
    for i, r in enumerate(results):
        depth = i
        cid = r.get("cast_id", "")[:14]
        sig = r.get("sigil_name", "")
        ver = r.get("verdict", "")
        res = float(r.get("resonance", 0.0))
        indent = "  " * depth
        lines.append(
            f"{indent}- [{depth}] {cid}  {sig}  {ver}  resonance={res:.4f}"
        )
        lin = r.get("lineage")
        if lin:
            div = lin.get("divergence")
            if div:
                st = str(div.get("status", "") or "")
                l2 = float(div.get("l2_magnitude", 0.0) or 0.0)
                cd = float(div.get("cosine_distance", 0.0) or 0.0)
                lines.append(
                    f"{indent}  divergence from parent: {st}  L2={l2:.4f}  cosine_distance={cd:.4f}"
                )
            elif lin.get("divergence_vector"):
                dv = lin["divergence_vector"]
                mag = sum(float(x) * float(x) for x in dv) ** 0.5
                lines.append(f"{indent}  divergence from parent (L2): {mag:.4f}")
    return "\n".join(lines)


def format_divergence_report(report: dict) -> str:
    cid = str(report.get("cast_id", "") or "")
    pid = str(report.get("parent_cast_id", "") or "")
    st = str(report.get("status", "") or "")
    l2 = float(report.get("l2_magnitude", 0.0) or 0.0)
    cd = float(report.get("cosine_distance", 0.0) or 0.0)
    at = str(report.get("computed_at", "") or "")
    return (
        "Divergence\n"
        f"  cast:   {cid}\n"
        f"  parent: {pid}\n"
        f"  status: {st}\n"
        f"  L2:     {l2:.6f}\n"
        f"  cosine_distance: {cd:.6f}\n"
        f"  computed_at: {at}"
    )


def format_divergence_thresholds(thresholds: dict) -> str:
    l2s = float(thresholds.get("l2_stable_max", 0.0) or 0.0)
    l2d = float(thresholds.get("l2_diverged_min", 0.0) or 0.0)
    cs = float(thresholds.get("cosine_stable_max", 0.0) or 0.0)
    cd = float(thresholds.get("cosine_diverged_min", 0.0) or 0.0)
    return (
        "Divergence thresholds\n"
        f"  l2_stable_max:       {l2s:.4f}\n"
        f"  l2_diverged_min:     {l2d:.4f}\n"
        f"  cosine_stable_max:   {cs:.4f}\n"
        f"  cosine_diverged_min: {cd:.4f}"
    )


def format_divergence_reports_table(reports: list[dict]) -> str:
    if not reports:
        return "No divergence reports."
    hdr = f"{'CAST ID':<14}{'STATUS':<10}{'L2':<10}{'COS_DIST':<10}COMPUTED_AT"
    sep = "-" * len(hdr)
    parts = [hdr, sep]
    for r in reports:
        cid = str(r.get("cast_id", "") or "")[:14]
        st = str(r.get("status", "") or "")[:9]
        l2 = float(r.get("l2_magnitude", 0.0) or 0.0)
        cd = float(r.get("cosine_distance", 0.0) or 0.0)
        ts = str(r.get("computed_at", "") or "")
        parts.append(f"{cid:<14}{st:<10}{l2:<10.4f}{cd:<10.4f}{ts}")
    return "\n".join(parts)


def format_aspects_table(canonical: list[dict], registered: list[dict]) -> str:
    rows = canonical + registered
    if not rows:
        return "No aspects."
    hdr = f"{'NAME':<18}{'POL':<5}{'ENTROPY':<10}SYMBOL"
    sep = "-" * len(hdr)
    parts = [hdr, sep]
    for r in rows:
        nm = str(r.get("name", ""))[:17]
        pol = int(r.get("polarity", 0) or 0)
        ent = float(r.get("entropy_coefficient", 0.0) or 0.0)
        sym = str(r.get("symbol", "") or "")[:1]
        parts.append(f"{nm:<18}{pol:<5}{ent:<10.2f}{sym}")
    return "\n".join(parts)


def format_drift_branches_table(rows: list[dict]) -> str:
    if not rows:
        return "No branch drift data."
    hdr = (
        f"{'BRANCH':<22}{'CASTS':<7}{'DIV':<5}{'DRIFT':<7}"
        f"{'MAX_L2':<10}{'MAX_COS':<10}LATEST"
    )
    sep = "-" * len(hdr)
    parts = [hdr, sep]
    for r in rows:
        bid = str(r.get("branch_id", "") or "")[:21]
        casts = int(r.get("casts_with_divergence", 0) or 0)
        div = int(r.get("diverged_count", 0) or 0)
        dr = int(r.get("drifting_count", 0) or 0)
        ml2 = float(r.get("max_l2", 0.0) or 0.0)
        mcd = float(r.get("max_cosine_distance", 0.0) or 0.0)
        ts = str(r.get("latest_computed_at", "") or "")
        parts.append(f"{bid:<22}{casts:<7}{div:<5}{dr:<7}{ml2:<10.4f}{mcd:<10.4f}{ts}")
    return "\n".join(parts)


def format_lineage_drift(report: dict) -> str:
    cid = str(report.get("cast_id", "") or "")
    n = int(report.get("chain_length", 0) or 0)
    cl2 = float(report.get("cumulative_l2", 0.0) or 0.0)
    ccos = float(report.get("cumulative_cosine_distance", 0.0) or 0.0)
    ml2 = float(report.get("max_l2", 0.0) or 0.0)
    mcos = float(report.get("max_cosine_distance", 0.0) or 0.0)
    top = report.get("top_contributors", []) or []
    top_txt = ", ".join(
        f"{t.get('aspect')}={float(t.get('abs_delta_sum', 0.0) or 0.0):.3f}"
        for t in top
    )
    lines = [
        "Lineage drift",
        f"  cast_id: {cid}",
        f"  chain_length: {n}",
        f"  cumulative_l2: {cl2:.4f}",
        f"  cumulative_cosine_distance: {ccos:.4f}",
        f"  max_l2: {ml2:.4f}",
        f"  max_cosine_distance: {mcos:.4f}",
    ]
    if top_txt:
        lines.append(f"  top_contributors: {top_txt}")
    lines.append("")
    lines.append("Hops")
    hops = report.get("hops", []) or []
    if not hops:
        lines.append("  (no hops)")
        return "\n".join(lines)
    for h in hops:
        hid = str(h.get("cast_id", "") or "")[:14]
        st = str(h.get("status", "") or "")
        l2 = float(h.get("l2_magnitude", 0.0) or 0.0)
        cd = float(h.get("cosine_distance", 0.0) or 0.0)
        contrib = h.get("top_contributors", []) or []
        contrib_txt = ", ".join(
            f"{c.get('aspect')}={float(c.get('abs_delta', 0.0) or 0.0):.3f}"
            for c in contrib
        )
        if contrib_txt:
            lines.append(f"  - {hid}  {st}  L2={l2:.4f}  cos={cd:.4f}  top: {contrib_txt}")
        else:
            lines.append(f"  - {hid}  {st}  L2={l2:.4f}  cos={cd:.4f}")
    return "\n".join(lines)


def format_registered_sigils_table(sigils: list[dict]) -> str:
    if not sigils:
        return "No registered sigils."
    hdr = f"{'NAME':<26}{'ASPECTS':<30}{'EFFECT':<16}{'CEILING':<9}{'OVERRIDE':<9}CONTRA"
    sep = "-" * len(hdr)
    parts = [hdr, sep]
    for r in sigils:
        nm = str(r.get("name", ""))[:25]
        asp_raw = " + ".join(sorted(r.get("aspects", []) or []))
        asp = (asp_raw[:29] + " ")[:30]
        eff = str(r.get("effect_class", "") or "")[:15]
        ceil = float(r.get("resonance_ceiling", 0.0) or 0.0)
        ov = "yes" if r.get("is_override") else "no"
        contra = str(r.get("contradiction_severity", "") or "")[:10]
        parts.append(f"{nm:<26}{asp:<30}{eff:<16}{ceil:<9.2f}{ov:<9}{contra}")
    return "\n".join(parts)
