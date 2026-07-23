import { createHash, timingSafeEqual } from "crypto";
import type { Application, Request, Response } from "express";
import { ENV } from "./_core/env";
import { sdk } from "./_core/sdk";
import { isLoopbackRequest } from "./_core/trpc";
import { getFabLocalApiBaseUrl } from "./fabLocalGateway";

export const MAX_FAB_SOURCE_PREVIEW_BYTES = 25 * 1024 * 1024;

const SAFE_PREVIEW_MIME_TYPES = new Set([
  "application/json",
  "application/pdf",
  "application/xml",
  "image/bmp",
  "image/gif",
  "image/jpeg",
  "image/png",
  "image/tiff",
  "image/webp",
  "text/csv",
  "text/plain",
  "text/xml",
]);

type FabSourcePreviewOptions = {
  authenticateRequest?: typeof sdk.authenticateRequest;
  baseUrl?: string;
  fetchImpl?: typeof fetch;
  localOperatorMode?: boolean;
  maxBytes?: number;
  timeoutMs?: number;
  token?: string;
};

function sourceSecurityHeaders(res: Response, contentType?: string) {
  res.setHeader("cache-control", "no-store");
  res.setHeader(
    "content-security-policy",
    contentType === "application/pdf"
      ? "frame-ancestors 'self'"
      : "sandbox; default-src 'none'",
  );
  res.setHeader("cross-origin-resource-policy", "same-origin");
  res.setHeader("referrer-policy", "no-referrer");
  res.setHeader("x-content-type-options", "nosniff");
  res.setHeader("x-frame-options", "SAMEORIGIN");
}

function sourceError(res: Response, status: number, error: string) {
  sourceSecurityHeaders(res);
  res.status(status).json({ error });
}

function validSha256(value: string): boolean {
  return /^[a-f0-9]{64}$/.test(value);
}

function equalSha256(left: string, right: string): boolean {
  if (!validSha256(left) || !validSha256(right)) return false;
  return timingSafeEqual(Buffer.from(left, "hex"), Buffer.from(right, "hex"));
}

export function registerFabSourcePreviewRoutes(
  app: Application,
  options: FabSourcePreviewOptions = {},
) {
  app.get("/api/fab/source/:documentId", async (req: Request, res: Response) => {
    const documentId = Number(req.params.documentId);
    if (!Number.isSafeInteger(documentId) || documentId <= 0) {
      sourceError(res, 400, "Invalid FAB document id");
      return;
    }

    const localOperatorMode = options.localOperatorMode ?? ENV.fabOperatorLocalMode;
    const localOperator = localOperatorMode && isLoopbackRequest(req);
    let adminOperator = false;
    if (!localOperator) {
      try {
        const authenticateRequest = options.authenticateRequest
          ?? sdk.authenticateRequest.bind(sdk);
        const user = await authenticateRequest(req);
        adminOperator = user?.role === "admin";
      } catch {
        adminOperator = false;
      }
    }
    if (!localOperator && !adminOperator) {
      sourceError(res, 403, "FAB operator access is required");
      return;
    }

    const maxBytes = options.maxBytes ?? MAX_FAB_SOURCE_PREVIEW_BYTES;
    const baseUrl = getFabLocalApiBaseUrl(options.baseUrl);
    const target = new URL(`/api/documents/${documentId}/source`, baseUrl);
    if (target.origin !== baseUrl.origin) {
      sourceError(res, 500, "FAB source preview configuration is invalid");
      return;
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), options.timeoutMs ?? 12_000);
    const headers = new Headers({ accept: "application/pdf,image/*,text/plain,application/json,application/xml" });
    const token = options.token ?? ENV.fabLocalApiToken;
    if (token) headers.set("authorization", `Bearer ${token}`);

    try {
      const fetchImpl = options.fetchImpl ?? fetch;
      const upstream = await fetchImpl(target, { headers, signal: controller.signal });
      if (!upstream.ok) {
        const status = [404, 409, 413, 415].includes(upstream.status) ? upstream.status : 502;
        sourceError(res, status, "The verified FAB source preview is unavailable");
        return;
      }

      const contentType = String(upstream.headers.get("content-type") || "")
        .split(";", 1)[0]
        .trim()
        .toLowerCase();
      if (!SAFE_PREVIEW_MIME_TYPES.has(contentType)) {
        sourceError(res, 415, "This FAB source file type cannot be previewed safely");
        return;
      }

      const advertisedLength = Number(upstream.headers.get("content-length") || "0");
      if (Number.isFinite(advertisedLength) && advertisedLength > maxBytes) {
        sourceError(res, 413, "The FAB source file exceeds the preview limit");
        return;
      }

      const body = Buffer.from(await upstream.arrayBuffer());
      if (body.byteLength > maxBytes) {
        sourceError(res, 413, "The FAB source file exceeds the preview limit");
        return;
      }

      const expectedSha256 = String(upstream.headers.get("x-fab-source-sha256") || "").toLowerCase();
      const integrity = String(upstream.headers.get("x-fab-source-integrity") || "").toLowerCase();
      const actualSha256 = createHash("sha256").update(body).digest("hex");
      if (integrity !== "verified" || !equalSha256(actualSha256, expectedSha256)) {
        sourceError(res, 502, "The FAB source preview failed its gateway integrity check");
        return;
      }

      sourceSecurityHeaders(res, contentType);
      res.setHeader("content-disposition", "inline");
      res.setHeader("content-length", String(body.byteLength));
      res.setHeader("content-type", contentType);
      res.setHeader("x-fab-source-integrity", "verified");
      res.setHeader("x-fab-source-sha256", expectedSha256);
      res.status(200).send(body);
    } catch (error) {
      const timedOut = error instanceof DOMException && error.name === "AbortError";
      sourceError(res, timedOut ? 504 : 502, timedOut
        ? "The FAB source preview request timed out"
        : "The verified FAB source preview is unavailable");
    } finally {
      clearTimeout(timeout);
    }
  });
}
