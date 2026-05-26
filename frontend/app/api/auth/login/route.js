import { NextResponse } from "next/server";

import { createAuthPayload } from "../../../../lib/auth";

const BACKEND_URL = (process.env.BACKEND_URL || "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

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

  let existsResponse;

  try {
    existsResponse = await fetch(
      `${BACKEND_URL}/jibble/member-exists?user_id=${encodeURIComponent(payload.login)}`,
    );
  } catch {
    return new Response("Jibble member lookup failed.", { status: 502 });
  }

  if (!existsResponse.ok) {
    const message = await existsResponse.text();
    return new Response(message || "Jibble member lookup failed.", {
      status: existsResponse.status,
    });
  }

  let existsPayload;

  try {
    existsPayload = await existsResponse.json();
  } catch {
    return new Response("Jibble member lookup failed.", { status: 502 });
  }

  if (existsPayload?.exists !== true) {
    return new Response("Jibble member not found.", { status: 401 });
  }

  const response = NextResponse.json({ ok: true, ...createAuthPayload(payload.login) });
  return response;
}
