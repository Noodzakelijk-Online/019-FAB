import type { Request } from "express";

type LoopbackRequest = Pick<Request, "hostname" | "socket">;

function isPrivateDockerGateway(address: string): boolean {
  const normalized = address.startsWith("::ffff:") ? address.slice(7) : address;
  const octets = normalized.split(".").map(Number);
  if (octets.length !== 4 || octets.some(value => !Number.isInteger(value) || value < 0 || value > 255)) {
    return false;
  }
  const [first, second, , last] = octets;
  const privateAddress = first === 10
    || (first === 172 && second >= 16 && second <= 31)
    || (first === 192 && second === 168);
  return privateAddress && last === 1;
}

export function isLoopbackRequest(
  req: LoopbackRequest,
  trustedProxyAddresses: readonly string[] = [],
  trustDockerGateway: boolean = false,
): boolean {
  const remoteAddress = String(req.socket?.remoteAddress || "").toLowerCase();
  const hostname = String(req.hostname || "").toLowerCase();
  const remoteIsLoopback = (
    remoteAddress === "::1"
    || remoteAddress === "127.0.0.1"
    || remoteAddress.startsWith("127.")
    || remoteAddress === "::ffff:127.0.0.1"
  );
  const remoteIsTrustedProxy = trustedProxyAddresses.includes(remoteAddress);
  const remoteIsDockerGateway = trustDockerGateway && isPrivateDockerGateway(remoteAddress);
  return (remoteIsLoopback || remoteIsTrustedProxy || remoteIsDockerGateway)
    && ["127.0.0.1", "localhost", "::1", "[::1]"].includes(hostname);
}
