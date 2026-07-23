import type { Request } from "express";

type LoopbackRequest = Pick<Request, "hostname" | "socket">;

export function isLoopbackRequest(req: LoopbackRequest): boolean {
  const remoteAddress = String(req.socket?.remoteAddress || "").toLowerCase();
  const hostname = String(req.hostname || "").toLowerCase();
  const remoteIsLoopback = (
    remoteAddress === "::1"
    || remoteAddress === "127.0.0.1"
    || remoteAddress.startsWith("127.")
    || remoteAddress === "::ffff:127.0.0.1"
  );
  return remoteIsLoopback && ["127.0.0.1", "localhost", "::1", "[::1]"].includes(hostname);
}
