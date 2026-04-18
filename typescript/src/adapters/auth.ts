/**
 * HTTP auth helpers — parity surface with `vermyth.adapters.auth.resolve_principal`.
 * JWT payload decoding is for introspection; verify signatures in production via JWKS or shared secret.
 */
export interface JwtClaims {
  readonly sub?: string;
  readonly iss?: string;
  readonly exp?: number;
  readonly [key: string]: unknown;
}

export interface Principal {
  readonly subject: string | null;
  readonly auth_method: "none" | "bearer_opaque" | "jwt";
}

export function decodeJwtPayload(token: string): JwtClaims | null {
  const parts = token.split(".");
  if (parts.length < 2) {
    return null;
  }
  try {
    const payload = parts[1]!;
    const json = Buffer.from(payload.replace(/-/g, "+").replace(/_/g, "/"), "base64").toString("utf8");
    return JSON.parse(json) as JwtClaims;
  } catch {
    return null;
  }
}

export function resolvePrincipal(headers: { authorization?: string | null }): Principal {
  const auth = headers.authorization ?? "";
  if (!auth.startsWith("Bearer ")) {
    return { subject: null, auth_method: "none" };
  }
  const token = auth.slice(7).trim();
  const claims = decodeJwtPayload(token);
  if (claims && claims.sub !== undefined) {
    return { subject: String(claims.sub), auth_method: "jwt" };
  }
  return { subject: null, auth_method: "bearer_opaque" };
}
