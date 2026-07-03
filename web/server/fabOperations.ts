import type { Application, NextFunction, Request, RequestHandler, Response } from "express";
import crypto from "crypto";
import { z, ZodError } from "zod";
import {
  bookkeepingDocumentRegisterSchema,
  bookkeepingDocumentUpdateSchema,
  reviewItemCreateSchema,
  reconciliationMatchCreateSchema,
  routingAttemptCreateSchema,
  workflowRunCreateSchema,
  workflowRunUpdateSchema,
  auditEventCreateSchema,
} from "../shared/validation";
import { ENV } from "./_core/env";
import { sanitizeText } from "./lib/sanitize";
import {
  addReviewItem,
  createBookkeepingDocument,
  createReconciliationMatch,
  createRoutingAttempt,
  createWorkflowRun,
  recordAuditEvent,
  updateBookkeepingDocument,
  updateWorkflowRun,
} from "./db";

function readToken(req: Request): string {
  const bearer = req.header("authorization")?.match(/^Bearer\s+(.+)$/i)?.[1];
  return bearer || req.header("x-fab-operations-token") || "";
}

export function isValidOperationsToken(candidate: string, expected: string): boolean {
  if (!candidate || !expected) return false;

  const candidateBuffer = Buffer.from(candidate);
  const expectedBuffer = Buffer.from(expected);
  if (candidateBuffer.length !== expectedBuffer.length) return false;

  return crypto.timingSafeEqual(candidateBuffer, expectedBuffer);
}

export function requireFabOperationsToken(req: Request, res: Response, next: NextFunction) {
  if (!ENV.fabOperationsServiceToken) {
    res.status(503).json({ error: "FAB operations service token is not configured" });
    return;
  }

  if (!isValidOperationsToken(readToken(req), ENV.fabOperationsServiceToken)) {
    res.status(401).json({ error: "Invalid FAB operations token" });
    return;
  }

  next();
}

function handleServiceError(res: Response, err: unknown) {
  if (err instanceof ZodError) {
    res.status(400).json({ error: "Invalid request body", issues: err.issues });
    return;
  }

  res.status(500).json({ error: err instanceof Error ? err.message : "FAB operations request failed" });
}

const serviceWorkflowRunUpdateSchema = workflowRunUpdateSchema.extend({
  startedAt: z.coerce.date().optional(),
  finishedAt: z.coerce.date().optional(),
});

export function registerFabOperationsRoutes(app: Application, limiter?: RequestHandler) {
  const middleware = limiter ? [limiter, requireFabOperationsToken] : [requireFabOperationsToken];
  app.use("/api/fab/operations", ...middleware);

  app.post("/api/fab/operations/workflow-runs", async (req, res) => {
    try {
      const input = workflowRunCreateSchema.parse(req.body);
      const result = await createWorkflowRun({
        status: input.status,
        triggerSource: sanitizeText(input.triggerSource),
        metadata: input.metadata || null,
      });
      await recordAuditEvent({
        actorUserId: null,
        action: "service.workflow_run.create",
        entityType: "workflow_run",
        entityId: String(result.id),
        details: input,
      });
      res.json(result);
    } catch (err) {
      handleServiceError(res, err);
    }
  });

  app.patch("/api/fab/operations/workflow-runs/:id", async (req, res) => {
    try {
      const input = serviceWorkflowRunUpdateSchema.parse({ ...req.body, id: Number(req.params.id) });
      const { id, ...data } = input;
      await updateWorkflowRun(id, data);
      await recordAuditEvent({
        actorUserId: null,
        action: "service.workflow_run.update",
        entityType: "workflow_run",
        entityId: String(id),
        details: data,
      });
      res.json({ success: true });
    } catch (err) {
      handleServiceError(res, err);
    }
  });

  app.post("/api/fab/operations/documents", async (req, res) => {
    try {
      const input = bookkeepingDocumentRegisterSchema.parse(req.body);
      const result = await createBookkeepingDocument({
        source: sanitizeText(input.source),
        sourceDocumentId: input.sourceDocumentId ? sanitizeText(input.sourceDocumentId) : null,
        originalFilename: sanitizeText(input.originalFilename),
        mimeType: input.mimeType ? sanitizeText(input.mimeType) : null,
        storagePath: input.storagePath ? sanitizeText(input.storagePath) : null,
        documentType: input.documentType,
        processingStatus: input.processingStatus,
        duplicateFingerprint: input.duplicateFingerprint ? sanitizeText(input.duplicateFingerprint) : null,
        duplicateOfDocumentId: input.duplicateOfDocumentId || null,
        vendorName: input.vendorName ? sanitizeText(input.vendorName) : null,
        category: input.category ? sanitizeText(input.category) : null,
        transactionDate: input.transactionDate || null,
        totalAmount: input.totalAmount?.toFixed(2),
        vatAmount: input.vatAmount?.toFixed(2),
        confidenceScore: input.confidenceScore?.toFixed(4),
        ocrText: input.ocrText || null,
        extractedData: input.extractedData || null,
        metadata: input.metadata || null,
      });
      await recordAuditEvent({
        actorUserId: null,
        action: "service.document.register",
        entityType: "bookkeeping_document",
        entityId: String(result.id),
        details: { source: input.source, sourceDocumentId: input.sourceDocumentId },
      });
      res.json(result);
    } catch (err) {
      handleServiceError(res, err);
    }
  });

  app.patch("/api/fab/operations/documents/:id", async (req, res) => {
    try {
      const input = bookkeepingDocumentUpdateSchema.parse({ ...req.body, id: Number(req.params.id) });
      const { id, ...data } = input;
      await updateBookkeepingDocument(id, {
        source: data.source ? sanitizeText(data.source) : undefined,
        sourceDocumentId: data.sourceDocumentId ? sanitizeText(data.sourceDocumentId) : undefined,
        originalFilename: data.originalFilename ? sanitizeText(data.originalFilename) : undefined,
        mimeType: data.mimeType ? sanitizeText(data.mimeType) : undefined,
        storagePath: data.storagePath ? sanitizeText(data.storagePath) : undefined,
        documentType: data.documentType,
        processingStatus: data.processingStatus,
        duplicateFingerprint: data.duplicateFingerprint ? sanitizeText(data.duplicateFingerprint) : undefined,
        duplicateOfDocumentId: data.duplicateOfDocumentId,
        vendorName: data.vendorName ? sanitizeText(data.vendorName) : undefined,
        category: data.category ? sanitizeText(data.category) : undefined,
        transactionDate: data.transactionDate,
        totalAmount: data.totalAmount?.toFixed(2),
        vatAmount: data.vatAmount?.toFixed(2),
        confidenceScore: data.confidenceScore?.toFixed(4),
        ocrText: data.ocrText,
        extractedData: data.extractedData,
        metadata: data.metadata,
      });
      await recordAuditEvent({
        actorUserId: null,
        action: "service.document.update",
        entityType: "bookkeeping_document",
        entityId: String(id),
        details: data,
      });
      res.json({ success: true });
    } catch (err) {
      handleServiceError(res, err);
    }
  });

  app.post("/api/fab/operations/review-items", async (req, res) => {
    try {
      const input = reviewItemCreateSchema.parse(req.body);
      const result = await addReviewItem({
        documentId: input.documentId || null,
        reason: sanitizeText(input.reason),
        details: input.details ? sanitizeText(input.details) : null,
        status: input.status,
        correctedData: input.correctedData || null,
      });
      await recordAuditEvent({
        actorUserId: null,
        action: "service.review_item.create",
        entityType: "review_item",
        entityId: String(result.id),
        details: { documentId: input.documentId || null, reason: input.reason },
      });
      res.json(result);
    } catch (err) {
      handleServiceError(res, err);
    }
  });

  app.post("/api/fab/operations/routing-attempts", async (req, res) => {
    try {
      const input = routingAttemptCreateSchema.parse(req.body);
      const result = await createRoutingAttempt({
        documentId: input.documentId || null,
        bookkeepingRecordId: input.bookkeepingRecordId || null,
        workflowRunId: input.workflowRunId || null,
        target: input.target,
        status: input.status,
        externalId: input.externalId ? sanitizeText(input.externalId) : null,
        message: input.message ? sanitizeText(input.message) : null,
        metadata: input.metadata || null,
      });
      await recordAuditEvent({
        actorUserId: null,
        action: "service.routing_attempt.create",
        entityType: "routing_attempt",
        entityId: String(result.id),
        details: {
          documentId: input.documentId || null,
          bookkeepingRecordId: input.bookkeepingRecordId || null,
          target: input.target,
          status: input.status,
        },
      });
      res.json(result);
    } catch (err) {
      handleServiceError(res, err);
    }
  });

  app.post("/api/fab/operations/reconciliation-matches", async (req, res) => {
    try {
      const input = reconciliationMatchCreateSchema.parse(req.body);
      const result = await createReconciliationMatch({
        documentId: input.documentId || null,
        bankTransactionId: sanitizeText(input.bankTransactionId),
        status: input.status,
        confidenceScore: input.confidenceScore?.toFixed(4),
        amountDifference: input.amountDifference?.toFixed(2),
        matchedAt: input.matchedAt || (input.status === "matched" ? new Date() : null),
        metadata: input.metadata || null,
      });
      await recordAuditEvent({
        actorUserId: null,
        action: "service.reconciliation_match.create",
        entityType: "reconciliation_match",
        entityId: String(result.id),
        details: {
          documentId: input.documentId || null,
          bankTransactionId: input.bankTransactionId,
          status: input.status,
        },
      });
      res.json(result);
    } catch (err) {
      handleServiceError(res, err);
    }
  });

  app.post("/api/fab/operations/audit-events", async (req, res) => {
    try {
      const input = auditEventCreateSchema.parse(req.body);
      const result = await recordAuditEvent({
        actorUserId: null,
        action: sanitizeText(input.action),
        entityType: sanitizeText(input.entityType),
        entityId: input.entityId ? sanitizeText(input.entityId) : null,
        details: input.details || null,
      });
      res.json(result);
    } catch (err) {
      handleServiceError(res, err);
    }
  });
}
