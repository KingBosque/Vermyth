import { createHash } from "node:crypto";

/**
 * Stable execution receipt digest — aligns with hashing step in `vermyth.receipt_signing`.
 * Wire Ed25519 or JWKS when full signing parity is required.
 */
export function receiptDigest(payload: Record<string, unknown>): string {
  return createHash("sha256").update(JSON.stringify(payload), "utf8").digest("hex");
}
