/** Frontend liveness for the Compose healthcheck (ARCHITECTURE §5.4, §11). */
export const dynamic = "force-dynamic";

export function GET(): Response {
  return Response.json({ status: "ok" });
}
