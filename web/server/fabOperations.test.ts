import express from "express";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { isValidOperationsToken, registerFabOperationsRoutes } from "./fabOperations";
import { createRoutingAttempt, recordAuditEvent } from "./db";

vi.mock("./_core/env", () => ({
  ENV: {
    fabOperationsServiceToken: "secret-token",
  },
}));

vi.mock("./db", () => ({
  createRoutingAttempt: vi.fn().mockResolvedValue({ id: 45 }),
  recordAuditEvent: vi.fn().mockResolvedValue({ id: 99 }),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("FAB operations service auth", () => {
  it("validates service tokens without accepting empty or partial values", () => {
    expect(isValidOperationsToken("secret-token", "secret-token")).toBe(true);
    expect(isValidOperationsToken("", "secret-token")).toBe(false);
    expect(isValidOperationsToken("secret", "secret-token")).toBe(false);
    expect(isValidOperationsToken("wrong-token", "secret-token")).toBe(false);
  });

  it("records bookkeeping-record routing attempts through the service endpoint", async () => {
    const app = express();
    app.use(express.json());
    registerFabOperationsRoutes(app);
    const server = app.listen(0);
    try {
      const address = server.address();
      if (!address || typeof address === "string") {
        throw new Error("Expected TCP test server address");
      }

      const response = await fetch(`http://127.0.0.1:${address.port}/api/fab/operations/routing-attempts`, {
        method: "POST",
        headers: {
          authorization: "Bearer secret-token",
          "content-type": "application/json",
        },
        body: JSON.stringify({
          bookkeepingRecordId: 98,
          workflowRunId: 34,
          target: "waveapps_business",
          status: "submitted",
          externalId: "wave-bank-expense-1",
          message: "Bank transaction draft.",
        }),
      });

      expect(response.status).toBe(200);
      await expect(response.json()).resolves.toEqual({ id: 45 });
      expect(createRoutingAttempt).toHaveBeenCalledWith(
        expect.objectContaining({
          documentId: null,
          bookkeepingRecordId: 98,
          workflowRunId: 34,
          target: "waveapps_business",
          status: "submitted",
          externalId: "wave-bank-expense-1",
          message: "Bank transaction draft.",
        })
      );
      expect(recordAuditEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          action: "service.routing_attempt.create",
          details: expect.objectContaining({
            documentId: null,
            bookkeepingRecordId: 98,
          }),
        })
      );
    } finally {
      await new Promise<void>((resolve, reject) => {
        server.close((error) => {
          if (error) reject(error);
          else resolve();
        });
      });
    }
  });
});
