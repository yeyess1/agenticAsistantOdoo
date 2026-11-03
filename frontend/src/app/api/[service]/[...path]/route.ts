/**
 * Same-origin proxy to the internal APIs (ARCHITECTURE §5.4): `/api/agent/*` and
 * `/api/ingestion/*`. Route handler instead of `rewrites` so that the upstream URL is read
 * at runtime (Compose env) and the response body is streamed as it arrives (SSE, uploads).
 */
import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const UPSTREAMS: Record<string, () => string> = {
  agent: () => process.env.AGENT_URL ?? "http://localhost:8000",
  ingestion: () => process.env.INGESTION_URL ?? "http://localhost:8001",
};

// Hop-by-hop headers (RFC 9110 §7.6.1) plus the ones fetch recomputes.
const DROP_REQUEST = new Set(["host", "connection", "content-length", "transfer-encoding", "keep-alive", "upgrade", "expect"]);
const DROP_RESPONSE = new Set(["connection", "content-length", "content-encoding", "transfer-encoding", "keep-alive"]);

function errorBody(code: string, message: string, status: number): Response {
  return Response.json({ detail: { error: { code, message } } }, { status });
}

async function proxy(request: NextRequest, ctx: RouteContext<"/api/[service]/[...path]">): Promise<Response> {
  const { service, path } = await ctx.params;
  const base = UPSTREAMS[service];
  if (!base) return errorBody("unknown_service", `unknown service ${service}`, 404);

  const target = new URL(`${base().replace(/\/$/, "")}/${path.map(encodeURIComponent).join("/")}`);
  target.search = request.nextUrl.search;

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!DROP_REQUEST.has(key.toLowerCase())) headers.set(key, value);
  });

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body: hasBody ? request.body : undefined,
      // Stream the request body (multipart uploads) instead of buffering it.
      ...(hasBody ? { duplex: "half" } : {}),
      signal: request.signal,
      cache: "no-store",
      redirect: "manual",
    } as RequestInit);
  } catch (err) {
    if (request.signal.aborted) return new Response(null, { status: 499 });
    return errorBody("upstream_unreachable", `${service}: ${(err as Error).message}`, 502);
  }

  const outHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!DROP_RESPONSE.has(key.toLowerCase())) outHeaders.set(key, value);
  });
  if (outHeaders.get("content-type")?.startsWith("text/event-stream")) {
    outHeaders.set("cache-control", "no-cache, no-transform");
    outHeaders.set("x-accel-buffering", "no");
  }
  return new Response(upstream.body, { status: upstream.status, statusText: upstream.statusText, headers: outHeaders });
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE };
