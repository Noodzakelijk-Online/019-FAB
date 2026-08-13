import type { CreateExpressContextOptions } from "@trpc/server/adapters/express";
import type { User } from "../drizzle/schema";
import { ENV } from "./_core/env";
import { isLoopbackRequest } from "./lib/loopback";

export type FabContext = {
  req: CreateExpressContextOptions["req"];
  res: CreateExpressContextOptions["res"];
  user: User | null;
};

export async function createFabContext(
  options: CreateExpressContextOptions,
): Promise<FabContext> {
  const localOperatorRequest = ENV.fabOperatorLocalMode && isLoopbackRequest(
    options.req,
    ENV.fabOperatorTrustedProxyAddresses,
    ENV.fabOperatorTrustDockerGateway,
  );
  if (localOperatorRequest) {
    return { req: options.req, res: options.res, user: null };
  }

  let user: User | null = null;
  try {
    const { sdk } = await import("./_core/sdk");
    user = await sdk.authenticateRequest(options.req);
  } catch {
    user = null;
  }
  return { req: options.req, res: options.res, user };
}
