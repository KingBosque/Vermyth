import pytest

from vermyth.contracts import GrimoireContract
from vermyth.engine.composition import CompositionEngine
from vermyth.engine.resonance import ResonanceEngine
from vermyth.grimoire.store import Grimoire
from vermyth.schema import (
    AspectID,
    CastResult,
    EffectClass,
    GlyphSeed,
    Intent,
    Lineage,
    ReversibilityClass,
    SemanticQuery,
    SemanticVector,
    SideEffectTolerance,
    VerdictType,
)


def make_cast_result() -> CastResult:
    composition = CompositionEngine()
    engine = ResonanceEngine(composition, backend=None)
    intent = Intent(
        objective="study the pattern",
        scope="local workspace",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.LOW,
    )
    return engine.cast(frozenset({AspectID.MIND, AspectID.LIGHT}), intent)


def test_grimoire_importable():
    from vermyth.grimoire.store import Grimoire as G

    assert G is Grimoire


def test_grimoire_subclass_grimoire_contract():
    assert issubclass(Grimoire, GrimoireContract)


def test_grimoire_creates_database_file(tmp_path):
    db = tmp_path / "test.db"
    assert not db.exists()
    Grimoire(db_path=db)
    assert db.is_file()


def test_migration_schema_migrations_contains_v001(tmp_path):
    db = tmp_path / "m.db"
    g = Grimoire(db_path=db)
    cur = g._conn.cursor()
    cur.execute("SELECT version FROM schema_migrations WHERE version = ?", ("v001",))
    row = cur.fetchone()
    assert row is not None
    assert row[0] == "v001"
    g.close()


def test_write_read_roundtrip(tmp_path):
    g = Grimoire(db_path=tmp_path / "r.db")
    r = make_cast_result()
    g.write(r)
    got = g.read(r.cast_id)
    assert got.cast_id == r.cast_id
    assert got.verdict.verdict_type == r.verdict.verdict_type
    assert got.verdict.resonance.adjusted == r.verdict.resonance.adjusted
    g.close()


def test_write_duplicate_cast_id_raises(tmp_path):
    g = Grimoire(db_path=tmp_path / "d.db")
    r = make_cast_result()
    g.write(r)
    with pytest.raises(ValueError, match="already exists"):
        g.write(r)
    g.close()


def test_read_unknown_raises_keyerror(tmp_path):
    g = Grimoire(db_path=tmp_path / "u.db")
    with pytest.raises(KeyError):
        g.read("nonexistent-cast-id")
    g.close()


def test_delete_removes_cast(tmp_path):
    g = Grimoire(db_path=tmp_path / "del.db")
    r = make_cast_result()
    g.write(r)
    g.delete(r.cast_id)
    with pytest.raises(KeyError):
        g.read(r.cast_id)
    g.close()


def test_delete_unknown_raises_keyerror(tmp_path):
    g = Grimoire(db_path=tmp_path / "del2.db")
    with pytest.raises(KeyError):
        g.delete("missing")
    g.close()


def test_query_no_filters_returns_all_up_to_limit(tmp_path):
    g = Grimoire(db_path=tmp_path / "q1.db")
    r1 = make_cast_result()
    r2 = make_cast_result()
    g.write(r1)
    g.write(r2)
    q = SemanticQuery(limit=20)
    rows = g.query(q)
    ids = {x.cast_id for x in rows}
    assert ids == {r1.cast_id, r2.cast_id}
    g.close()


def test_query_verdict_filter(tmp_path):
    g = Grimoire(db_path=tmp_path / "q2.db")
    r1 = make_cast_result()
    r2 = make_cast_result()
    g.write(r1)
    g.write(r2)
    vt = r1.verdict.verdict_type
    q = SemanticQuery(verdict_filter=vt, limit=20)
    rows = g.query(q)
    assert all(x.verdict.verdict_type == vt for x in rows)
    g.close()


def test_query_min_resonance(tmp_path):
    g = Grimoire(db_path=tmp_path / "q3.db")
    r = make_cast_result()
    g.write(r)
    thr = r.verdict.resonance.adjusted
    q = SemanticQuery(min_resonance=thr, limit=20)
    rows = g.query(q)
    assert len(rows) == 1
    assert rows[0].cast_id == r.cast_id
    g.close()


def test_query_empty_when_no_match(tmp_path):
    g = Grimoire(db_path=tmp_path / "q4.db")
    r = make_cast_result()
    g.write(r)
    q = SemanticQuery(min_resonance=1.0, limit=20)
    assert g.query(q) == []
    g.close()


def test_query_respects_limit(tmp_path):
    g = Grimoire(db_path=tmp_path / "q5.db")
    for _ in range(3):
        g.write(make_cast_result())
    q = SemanticQuery(limit=2)
    rows = g.query(q)
    assert len(rows) == 2
    g.close()


def test_query_aspect_filter(tmp_path):
    g = Grimoire(db_path=tmp_path / "q_aspect.db")
    comp = CompositionEngine()
    eng = ResonanceEngine(comp, backend=None)
    intent = Intent(
        objective="a",
        scope="b",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.LOW,
    )
    r_a = eng.cast(frozenset({AspectID.MIND, AspectID.LIGHT}), intent)
    r_b = eng.cast(frozenset({AspectID.FORM, AspectID.LIGHT}), intent)
    g.write(r_a)
    g.write(r_b)
    q = SemanticQuery(aspect_filter=frozenset({AspectID.MIND, AspectID.LIGHT}), limit=20)
    rows = g.query(q)
    assert {x.cast_id for x in rows} == {r_a.cast_id}
    g.close()


def test_query_effect_class_filter(tmp_path):
    g = Grimoire(db_path=tmp_path / "q_effect.db")
    r = make_cast_result()
    g.write(r)
    q = SemanticQuery(effect_class_filter=r.sigil.effect_class, limit=20)
    rows = g.query(q)
    assert len(rows) == 1
    assert rows[0].cast_id == r.cast_id
    g.close()


def test_query_branch_id_filter(tmp_path):
    g = Grimoire(db_path=tmp_path / "q_branch.db")
    base = make_cast_result()
    r1 = CastResult.model_construct(
        cast_id=base.cast_id,
        timestamp=base.timestamp,
        intent=base.intent,
        sigil=base.sigil,
        verdict=base.verdict,
        immutable=True,
        lineage=Lineage(parent_cast_id="p", depth=1, branch_id="branch-a"),
        glyph_seed_id=None,
        provenance=None,
    )
    r2 = make_cast_result()
    g.write(r1)
    g.write(r2)
    q = SemanticQuery(branch_id="branch-a", limit=20)
    rows = g.query(q)
    assert {x.cast_id for x in rows} == {r1.cast_id}
    g.close()


def test_semantic_search_raises_when_proximity_to_none(tmp_path):
    g = Grimoire(db_path=tmp_path / "s0.db")
    q = SemanticQuery.model_construct(
        proximity_to=None,
        proximity_threshold=0.5,
        limit=10,
    )
    with pytest.raises(ValueError):
        g.semantic_search(q)
    g.close()


def test_semantic_search_orders_by_similarity(tmp_path):
    g = Grimoire(db_path=tmp_path / "s1.db")
    comp = CompositionEngine()
    eng = ResonanceEngine(comp, backend=None)
    intent = Intent(
        objective="a",
        scope="b",
        reversibility=ReversibilityClass.REVERSIBLE,
        side_effect_tolerance=SideEffectTolerance.LOW,
    )
    r_a = eng.cast(frozenset({AspectID.MIND, AspectID.LIGHT}), intent)
    r_b = eng.cast(frozenset({AspectID.FORM, AspectID.LIGHT}), intent)
    g.write(r_a)
    g.write(r_b)
    probe = r_a.sigil.semantic_vector
    q = SemanticQuery(
        proximity_to=probe,
        proximity_threshold=0.0,
        limit=10,
    )
    rows = g.semantic_search(q)
    assert len(rows) >= 2
    sims = [probe.cosine_similarity(r.sigil.semantic_vector) for r in rows]
    assert sims == sorted(sims, reverse=True)
    assert rows[0].cast_id == r_a.cast_id
    g.close()


def test_semantic_search_empty_impossible_threshold(tmp_path):
    g = Grimoire(db_path=tmp_path / "s2.db")
    r = make_cast_result()
    g.write(r)
    q = SemanticQuery.model_construct(
        proximity_to=r.sigil.semantic_vector,
        proximity_threshold=1.01,
        limit=10,
    )
    assert g.semantic_search(q) == []
    g.close()


def test_write_read_seed_roundtrip(tmp_path):
    g = Grimoire(db_path=tmp_path / "seed1.db")
    pattern = frozenset({AspectID.MIND})
    sv = SemanticVector.from_aspects(pattern)
    seed = GlyphSeed.model_construct(
        seed_id="seed-1",
        aspect_pattern=pattern,
        observed_count=7,
        mean_resonance=0.62,
        coherence_rate=0.4,
        candidate_effect_class=EffectClass.COGNITION,
        crystallized=False,
        semantic_vector=sv,
    )
    g.write_seed(seed)
    got = g.read_seed("seed-1")
    assert got.seed_id == "seed-1"
    assert got.observed_count == 7
    assert got.mean_resonance == 0.62
    g.close()


def test_write_seed_upsert(tmp_path):
    g = Grimoire(db_path=tmp_path / "seed2.db")
    pattern = frozenset({AspectID.LIGHT})
    sv = SemanticVector.from_aspects(pattern)
    s1 = GlyphSeed.model_construct(
        seed_id="same",
        aspect_pattern=pattern,
        observed_count=1,
        mean_resonance=0.1,
        coherence_rate=0.0,
        candidate_effect_class=None,
        crystallized=False,
        semantic_vector=sv,
    )
    s2 = GlyphSeed.model_construct(
        seed_id="same",
        aspect_pattern=pattern,
        observed_count=99,
        mean_resonance=0.9,
        coherence_rate=0.5,
        candidate_effect_class=None,
        crystallized=False,
        semantic_vector=sv,
    )
    g.write_seed(s1)
    g.write_seed(s2)
    got = g.read_seed("same")
    assert got.observed_count == 99
    assert got.mean_resonance == 0.9
    g.close()


def test_read_seed_unknown_keyerror(tmp_path):
    g = Grimoire(db_path=tmp_path / "seed3.db")
    with pytest.raises(KeyError):
        g.read_seed("nope")
    g.close()


def test_query_seeds_no_filters(tmp_path):
    g = Grimoire(db_path=tmp_path / "qs1.db")
    p1 = frozenset({AspectID.MIND})
    p2 = frozenset({AspectID.LIGHT})
    g.write_seed(
        GlyphSeed.model_construct(
            seed_id="a",
            aspect_pattern=p1,
            observed_count=0,
            mean_resonance=0.0,
            coherence_rate=0.0,
            candidate_effect_class=None,
            crystallized=False,
            semantic_vector=SemanticVector.from_aspects(p1),
        )
    )
    g.write_seed(
        GlyphSeed.model_construct(
            seed_id="b",
            aspect_pattern=p2,
            observed_count=0,
            mean_resonance=0.0,
            coherence_rate=0.0,
            candidate_effect_class=None,
            crystallized=False,
            semantic_vector=SemanticVector.from_aspects(p2),
        )
    )
    all_s = g.query_seeds(None, None)
    assert {s.seed_id for s in all_s} == {"a", "b"}
    g.close()


def test_query_seeds_crystallized_false(tmp_path):
    g = Grimoire(db_path=tmp_path / "qs2.db")
    p = frozenset({AspectID.MIND})
    sv = SemanticVector.from_aspects(p)
    g.write_seed(
        GlyphSeed.model_construct(
            seed_id="c1",
            aspect_pattern=p,
            observed_count=1,
            mean_resonance=0.5,
            coherence_rate=0.5,
            candidate_effect_class=None,
            crystallized=False,
            semantic_vector=sv,
        )
    )
    g.write_seed(
        GlyphSeed.model_construct(
            seed_id="c2",
            aspect_pattern=p,
            observed_count=1,
            mean_resonance=0.5,
            coherence_rate=0.5,
            candidate_effect_class=None,
            crystallized=True,
            semantic_vector=sv,
        )
    )
    unc = g.query_seeds(None, False)
    assert len(unc) == 1
    assert unc[0].seed_id == "c1"
    assert unc[0].crystallized is False
    g.close()


def test_query_seeds_aspect_pattern(tmp_path):
    g = Grimoire(db_path=tmp_path / "qs3.db")
    p_mind = frozenset({AspectID.MIND})
    p_light = frozenset({AspectID.LIGHT})
    g.write_seed(
        GlyphSeed.model_construct(
            seed_id="m",
            aspect_pattern=p_mind,
            observed_count=0,
            mean_resonance=0.0,
            coherence_rate=0.0,
            candidate_effect_class=None,
            crystallized=False,
            semantic_vector=SemanticVector.from_aspects(p_mind),
        )
    )
    g.write_seed(
        GlyphSeed.model_construct(
            seed_id="l",
            aspect_pattern=p_light,
            observed_count=0,
            mean_resonance=0.0,
            coherence_rate=0.0,
            candidate_effect_class=None,
            crystallized=False,
            semantic_vector=SemanticVector.from_aspects(p_light),
        )
    )
    matches = g.query_seeds(p_mind, None)
    assert len(matches) == 1
    assert matches[0].seed_id == "m"
    g.close()


def test_close_after_operations(tmp_path):
    g = Grimoire(db_path=tmp_path / "close.db")
    g.write(make_cast_result())
    g.close()


def test_roundtrip_lineage(tmp_path):
    g = Grimoire(db_path=tmp_path / "lin.db")
    base = make_cast_result()
    lin = Lineage(
        parent_cast_id="parent-ulid",
        depth=2,
        branch_id="branch-stable",
    )
    r = CastResult.model_construct(
        cast_id=base.cast_id,
        timestamp=base.timestamp,
        intent=base.intent,
        sigil=base.sigil,
        verdict=base.verdict,
        immutable=True,
        lineage=lin,
        glyph_seed_id=None,
    )
    g.write(r)
    got = g.read(r.cast_id)
    assert got.lineage is not None
    assert got.lineage.branch_id == "branch-stable"
    assert got.lineage.parent_cast_id == "parent-ulid"
    assert got.lineage.depth == 2
    g.close()


def test_roundtrip_glyph_seed_id(tmp_path):
    g = Grimoire(db_path=tmp_path / "gid.db")
    base = make_cast_result()
    r = CastResult.model_construct(
        cast_id=base.cast_id,
        timestamp=base.timestamp,
        intent=base.intent,
        sigil=base.sigil,
        verdict=base.verdict,
        immutable=True,
        lineage=None,
        glyph_seed_id="glyph-42",
    )
    g.write(r)
    got = g.read(r.cast_id)
    assert got.glyph_seed_id == "glyph-42"
    g.close()
