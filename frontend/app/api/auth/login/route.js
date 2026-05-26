import { NextResponse } from "next/server";

import { createAuthPayload, verifyCredentials } from "../../../../lib/auth";

export async function POST(request) {
  let payload;

  try {
    payload = await request.json();
  } catch {
    return new Response("Invalid JSON body.", { status: 400 });
  }

  if (typeof payload?.login !== "string" || !payload.login) {
    return new Response("Missing login.", { status: 400 });
  }

  if (typeof payload?.password !== "string" || !payload.password) {
    return new Response("Missing password.", { status: 400 });
  }

  if (!verifyCredentials(payload.login, payload.password)) {
    return new Response("Invalid credentials.", { status: 401 });
  }

  const response = NextResponse.json({ ok: true, ...createAuthPayload(payload.login) });
  return response;
}
