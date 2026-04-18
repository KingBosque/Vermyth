/**
 * Capability token verification — stub for Python `vermyth.adapters.a2a.security.verify_capability_token`.
 * Full HMAC/Ed25519 parity can be added when strict A2A auth is required.
 */
export function verifyCapabilityToken(
  tokenPayload: Record<string, unknown>,
  _options: { sharedSecret?: string | null } = {},
): { tool_scope: string } {
  return { tool_scope: String(tokenPayload["tool_scope"] ?? "*") };
}
