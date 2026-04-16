from __future__ import annotations

import functools

from vermyth.registry import AspectRegistry
from vermyth.schema import Aspect


@functools.cache
def canonical_aspect_key(aspects: frozenset[Aspect]) -> str:
    order_index = {a: i for i, a in enumerate(AspectRegistry.get().full_order)}
    ordered = sorted(aspects, key=lambda a: order_index.get(a, 10**9))
    return "+".join(a.name for a in ordered)

