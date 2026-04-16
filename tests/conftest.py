import sys
from pathlib import Path
from typing import Callable

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "experimental: marks tests for experimental/frozen surfaces",
    )


@pytest.fixture(autouse=True)
def _reset_global_state():
    """
    Vermyth uses a process-global AspectRegistry and a cached canonical key function.
    Tests must be isolated from each other regardless of execution order.
    """
    from vermyth.engine.keys import canonical_aspect_key
    from vermyth.registry import AspectRegistry

    AspectRegistry.reset()
    canonical_aspect_key.cache_clear()
    yield
    AspectRegistry.reset()
    canonical_aspect_key.cache_clear()


@pytest.fixture
def repo_root() -> Path:
    return _REPO_ROOT


@pytest.fixture
def composition_engine():
    from vermyth.engine.composition import CompositionEngine

    return CompositionEngine()


@pytest.fixture
def resonance_engine(composition_engine):
    from vermyth.engine.resonance import ResonanceEngine

    return ResonanceEngine(composition_engine, backend=None)


@pytest.fixture
def tmp_grimoire(tmp_path: Path):
    from vermyth.grimoire.store import Grimoire

    return Grimoire(db_path=tmp_path / "grimoire.db")


@pytest.fixture
def tools_factory() -> Callable[[Path], object]:
    from vermyth.engine.composition import CompositionEngine
    from vermyth.engine.resonance import ResonanceEngine
    from vermyth.grimoire.store import Grimoire
    from vermyth.mcp.tools import VermythTools

    def _make(tmp_path: Path) -> VermythTools:
        db = tmp_path / "grimoire.db"
        composition = CompositionEngine()
        engine = ResonanceEngine(composition, backend=None)
        grimoire = Grimoire(db_path=db)
        return VermythTools(engine, grimoire)

    return _make


@pytest.fixture
def make_tools(tools_factory, tmp_path: Path):
    return tools_factory(tmp_path)


@pytest.fixture
def valid_intent():
    return {
        "objective": "study the pattern",
        "scope": "local workspace",
        "reversibility": "REVERSIBLE",
        "side_effect_tolerance": "HIGH",
    }


@pytest.fixture
def make_cli(tmp_path: Path):
    from vermyth.cli.main import VermythCLI
    from vermyth.engine.composition import CompositionEngine
    from vermyth.engine.resonance import ResonanceEngine
    from vermyth.grimoire.store import Grimoire

    db = tmp_path / "cli.db"
    eng = ResonanceEngine(CompositionEngine(), backend=None)
    g = Grimoire(db_path=db)
    return VermythCLI(engine=eng, grimoire=g)

