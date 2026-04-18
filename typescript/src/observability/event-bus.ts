export type VermythEvent = {
  readonly name: string;
  readonly payload: Record<string, unknown>;
  readonly castId?: string | null;
  readonly branchId?: string | null;
};

/**
 * In-process event fan-out (Python `EventBus` parity for MCP/CLI hooks).
 */
export class EventBus {
  private readonly listeners = new Set<(e: VermythEvent) => void>();
  private readonly buffer: VermythEvent[] = [];
  private readonly maxBuffer = 2000;

  subscribe(fn: (e: VermythEvent) => void): () => void {
    this.listeners.add(fn);
    return () => {
      this.listeners.delete(fn);
    };
  }

  emit(event: VermythEvent): void {
    this.buffer.push(event);
    if (this.buffer.length > this.maxBuffer) {
      this.buffer.splice(0, this.buffer.length - this.maxBuffer);
    }
    for (const fn of this.listeners) {
      try {
        fn(event);
      } catch {
        /* best-effort */
      }
    }
  }

  tail(n: number, eventType?: string | null): VermythEvent[] {
    const take = Math.max(0, Math.min(5000, Math.floor(n)));
    let slice = this.buffer.slice(-take);
    if (eventType !== undefined && eventType !== null && eventType !== "") {
      slice = slice.filter((e) => e.name === eventType);
    }
    return slice;
  }
}
