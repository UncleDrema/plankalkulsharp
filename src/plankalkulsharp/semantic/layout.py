"""Stable heap layouts, independent of CLR structure layout."""

from __future__ import annotations

from dataclasses import dataclass

from .analyzer import ResolvedArray, ResolvedBit, ResolvedBitSeq, ResolvedRecord, ResolvedRef, ResolvedType


@dataclass(frozen=True)
class HeapLayout:
    size: int
    alignment: int
    offsets: tuple[int, ...] = ()


def heap_layout(rt: ResolvedType) -> HeapLayout:
    """Return a heap-safe layout or raise ValueError for unsupported values."""
    if isinstance(rt, ResolvedBit):
        return HeapLayout(1, 1)
    if isinstance(rt, ResolvedBitSeq):
        if not 1 <= rt.length <= 64:
            raise ValueError(f"bit sequence width {rt.length} is outside 1..64")
        return HeapLayout(4 if rt.length <= 32 else 8, 4 if rt.length <= 32 else 8)
    if isinstance(rt, ResolvedRef):
        # Ссылка занимает только идентификатор: разметку её цели не разворачиваем.
        # Поэтому рекурсивный node = (int, @node) имеет конечный размер.
        return HeapLayout(8, 8)
    if isinstance(rt, ResolvedArray):
        raise ValueError("arrays cannot be stored in the heap")
    if isinstance(rt, ResolvedRecord):
        offset = 0
        offsets: list[int] = []
        for field in rt.fields:
            layout = heap_layout(field)
            # Округляем смещение вверх до границы, требуемой очередным полем.
            # Например, после int32 поле-ссылка начинается с байта 8, а не 4.
            offset = (offset + layout.alignment - 1) // layout.alignment * layout.alignment
            offsets.append(offset)
            offset += layout.size
        # Хвостовое выравнивание сохраняется и при вложении записи в другую запись.
        return HeapLayout((offset + 7) // 8 * 8, 8, tuple(offsets))
    raise ValueError(f"{rt} cannot be stored in the heap")
