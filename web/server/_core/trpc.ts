import { NOT_ADMIN_ERR_MSG, UNAUTHED_ERR_MSG } from '@shared/const';
import { initTRPC, TRPCError } from "@trpc/server";
import type { Request } from "express";
import superjson from "superjson";
import type { TrpcContext } from "./context";
import { ENV } from "./env";

const t = initTRPC.context<TrpcContext>().create({
  transformer: superjson,
});

export const router = t.router;
export const publicProcedure = t.procedure;

const requireUser = t.middleware(async opts => {
  const { ctx, next } = opts;

  if (!ctx.user) {
    throw new TRPCError({ code: "UNAUTHORIZED", message: UNAUTHED_ERR_MSG });
  }

  return next({
    ctx: {
      ...ctx,
      user: ctx.user,
    },
  });
});

export const protectedProcedure = t.procedure.use(requireUser);

export function isLoopbackRequest(req: Pick<Request, "hostname" | "socket">): boolean {
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

export function isLoopbackFabOperatorRequest(ctx: TrpcContext): boolean {
  return isLoopbackRequest(ctx.req);
}

export const fabOperatorProcedure = t.procedure.use(
  t.middleware(async opts => {
    const { ctx, next } = opts;
    const adminUser = ctx.user?.role === "admin";
    const localOperator = ENV.fabOperatorLocalMode && isLoopbackFabOperatorRequest(ctx);
    if (!adminUser && !localOperator) {
      throw new TRPCError({ code: "FORBIDDEN", message: NOT_ADMIN_ERR_MSG });
    }
    return next({ ctx: { ...ctx, fabOperatorMode: adminUser ? "admin" as const : "local" as const } });
  }),
);

export const adminProcedure = t.procedure.use(
  t.middleware(async opts => {
    const { ctx, next } = opts;

    if (!ctx.user || ctx.user.role !== 'admin') {
      throw new TRPCError({ code: "FORBIDDEN", message: NOT_ADMIN_ERR_MSG });
    }

    return next({
      ctx: {
        ...ctx,
        user: ctx.user,
      },
    });
  }),
);
