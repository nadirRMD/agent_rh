import crypto from "crypto";

const AUTH_SECRET = process.env.FRONTEND_AUTH_SECRET || "agent-rh-dev-secret";
const TOKEN_TTL_SECONDS = 60 * 60 * 24;

function base64UrlEncode(input) {
  return Buffer.from(input).toString("base64url");
}

function base64UrlDecode(input) {
  return Buffer.from(input, "base64url").toString("utf8");
}

function sign(value) {
  return crypto.createHmac("sha256", AUTH_SECRET).update(value).digest("base64url");
}

export function createAuthPayload(login) {
  const payload = {
    login,
    exp: Math.floor(Date.now() / 1000) + TOKEN_TTL_SECONDS,
  };
  const payloadPart = base64UrlEncode(JSON.stringify(payload));
  const signature = sign(payloadPart);

  return {
    token: `${payloadPart}.${signature}`,
  };
}

export function getTokenFromHeaders(headers) {
  const explicitToken = headers.get("x-agent-rh-token");
  if (explicitToken) {
    return explicitToken;
  }

  const authorization = headers.get("authorization");
  if (!authorization) {
    return "";
  }

  const [scheme, token] = authorization.split(" ");
  if (scheme?.toLowerCase() !== "bearer" || !token) {
    return "";
  }

  return token;
}

export function isAuthenticatedToken(token) {
  if (typeof token !== "string" || !token) {
    return false;
  }

  const [payloadPart, signature] = token.split(".");
  if (!payloadPart || !signature) {
    return false;
  }

  if (sign(payloadPart) !== signature) {
    return false;
  }

  try {
    const payload = JSON.parse(base64UrlDecode(payloadPart));
    if (typeof payload?.exp !== "number") {
      return false;
    }

    return payload.exp >= Math.floor(Date.now() / 1000);
  } catch {
    return false;
  }
}
