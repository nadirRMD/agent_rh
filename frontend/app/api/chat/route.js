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

  if (typeof payload?.question !== "string" || !payload.question.trim()) {
    return new Response("Missing question.", { status: 400 });
  }

  const token = request.headers.get("x-agent-rh-token") || "";

  try {
    const backendResponse = await fetch(`${BACKEND_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "x-agent-rh-token": token } : {}),
      },
      body: JSON.stringify({ question: payload.question }),
    });

    const text = await backendResponse.text();
    return new Response(text, {
      status: backendResponse.status,
      headers: {
        "Content-Type":
          backendResponse.headers.get("content-type") ||
          "text/plain; charset=utf-8",
      },
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Backend request failed.";
    return new Response(message, { status: 502 });
  }
}
