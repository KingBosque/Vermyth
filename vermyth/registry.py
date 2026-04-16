from __future__ import annotations

from vermyth.schema import (
    ASPECT_CANONICAL_ORDER,
    Aspect,
    RegisteredAspect,
    _set_basis_version,
    current_basis_version,
    _reset_registered_aspects_for_tests,
    full_aspect_order,
    register_aspect,
    registered_aspects,
)


class AspectRegistry:
    _instance: AspectRegistry | None = None

    def __init__(self) -> None:
        self._canonical = list(ASPECT_CANONICAL_ORDER)
        self._by_name: dict[str, Aspect] = {a.name: a for a in ASPECT_CANONICAL_ORDER}
        for a in registered_aspects():
            self._by_name[a.name] = a

    @classmethod
    def get(cls) -> AspectRegistry:
        if cls._instance is None:
            cls._instance = AspectRegistry()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
        _reset_registered_aspects_for_tests()

    @property
    def dimensionality(self) -> int:
        return len(full_aspect_order())

    @property
    def full_order(self) -> tuple[Aspect, ...]:
        return full_aspect_order()

    def resolve(self, name: str) -> Aspect:
        return self._by_name[name]

    def is_registered(self, name: str) -> bool:
        v = self._by_name.get(name)
        return isinstance(v, RegisteredAspect)

    def registered_aspects(self) -> list[RegisteredAspect]:
        return registered_aspects()

    def register(self, aspect: RegisteredAspect) -> None:
        register_aspect(aspect)
        self._by_name[aspect.name] = aspect

    def current_basis_version(self) -> int:
        return current_basis_version()

    def set_basis_version(self, version: int) -> None:
        _set_basis_version(version)

