/**
 * Stripe Webhook Handler — Production-hardened
 *
 * Key hardening:
 * - Structured logging for every event
 * - Idempotency guard: logs duplicate event IDs (Stripe can retry)
 * - Defensive parseInt with NaN check
 * - Notification failures don't break the webhook response
 * - Always returns 200 to Stripe to prevent retries for handled events
 */
import type { Request, Response } from "express";
import { constructWebhookEvent } from "./stripe";
import { eq } from "drizzle-orm";
import { users } from "../../drizzle/schema";
import { getDb } from "../db";
import { notifyOwner } from "../_core/notification";
import { createLogger } from "../lib/logger";

const log = createLogger("Webhook");

// Simple in-memory set to detect duplicate events within this process lifetime.
// In a multi-instance deployment, use Redis or a DB table for idempotency.
const processedEvents = new Set<string>();
const MAX_PROCESSED_EVENTS = 10_000;

function markProcessed(eventId: string) {
  // Prevent unbounded memory growth
  if (processedEvents.size >= MAX_PROCESSED_EVENTS) {
    const firstKey = processedEvents.values().next().value;
    if (firstKey) processedEvents.delete(firstKey);
  }
  processedEvents.add(eventId);
}

export async function handleStripeWebhook(req: Request, res: Response) {
  const signature = req.headers["stripe-signature"] as string;

  if (!signature) {
    log.warn("Missing stripe-signature header");
    return res.status(400).json({ error: "Missing signature" });
  }

  let event;
  try {
    event = constructWebhookEvent(req.body, signature);
  } catch (err: any) {
    log.error("Signature verification failed", {
      error: err.message,
    });
    return res.status(400).json({ error: "Webhook signature verification failed" });
  }

  // Handle test events (required for Stripe webhook verification)
  if (event.id.startsWith("evt_test_")) {
    log.info("Test event detected", { eventId: event.id });
    return res.json({ verified: true });
  }

  // Idempotency check — skip if we've already processed this event
  if (processedEvents.has(event.id)) {
    log.info("Duplicate event skipped", { eventId: event.id, type: event.type });
    return res.json({ received: true, duplicate: true });
  }

  log.info("Processing event", { eventId: event.id, type: event.type });

  try {
    switch (event.type) {
      case "checkout.session.completed": {
        const session = event.data.object as any;
        const userIdStr = session.metadata?.user_id;
        const customerId = session.customer;

        if (userIdStr && customerId) {
          const userId = parseInt(userIdStr, 10);
          if (isNaN(userId)) {
            log.error("Invalid user_id in checkout metadata", {
              rawUserId: userIdStr,
              sessionId: session.id,
            });
            break;
          }

          const db = await getDb();
          if (db) {
            await db
              .update(users)
              .set({ stripeCustomerId: customerId })
              .where(eq(users.id, userId));
          }

          log.info("Checkout completed", {
            sessionId: session.id,
            userId,
            customerId,
          });

          // Notification is best-effort — don't let it break the webhook
          await notifyOwner({
            title: "New Subscription!",
            content: `A user has subscribed to FAB Pay-As-You-Go.\n\nUser ID: ${userId}\nEmail: ${session.metadata?.customer_email || "N/A"}\nName: ${session.metadata?.customer_name || "N/A"}\nSession ID: ${session.id}`,
          }).catch((err) => {
            log.warn("Failed to send checkout notification", {}, err instanceof Error ? err : undefined);
          });
        } else {
          log.warn("Checkout session missing metadata", {
            sessionId: session.id,
            hasUserId: !!userIdStr,
            hasCustomerId: !!customerId,
          });
        }
        break;
      }

      case "invoice.paid": {
        const invoice = event.data.object as any;
        log.info("Invoice paid", {
          invoiceId: invoice.id,
          amount: invoice.amount_paid,
          currency: invoice.currency,
          customer: invoice.customer,
        });
        break;
      }

      case "invoice.payment_failed": {
        const invoice = event.data.object as any;
        log.warn("Invoice payment failed", {
          invoiceId: invoice.id,
          customer: invoice.customer,
          amount: invoice.amount_due,
          currency: invoice.currency,
        });

        await notifyOwner({
          title: "Payment Failed",
          content: `A subscription payment has failed.\n\nInvoice ID: ${invoice.id}\nCustomer: ${invoice.customer}\nAmount: ${(invoice.amount_due || 0) / 100} ${(invoice.currency || "EUR").toUpperCase()}`,
        }).catch((err) => {
          log.warn("Failed to send payment failure notification", {}, err instanceof Error ? err : undefined);
        });
        break;
      }

      case "customer.subscription.deleted": {
        const subscription = event.data.object as any;
        log.info("Subscription cancelled", {
          subscriptionId: subscription.id,
          customer: subscription.customer,
        });

        await notifyOwner({
          title: "Subscription Cancelled",
          content: `A subscription has been cancelled.\n\nSubscription ID: ${subscription.id}\nCustomer: ${subscription.customer}`,
        }).catch((err) => {
          log.warn("Failed to send cancellation notification", {}, err instanceof Error ? err : undefined);
        });
        break;
      }

      case "customer.subscription.updated": {
        const subscription = event.data.object as any;
        log.info("Subscription updated", {
          subscriptionId: subscription.id,
          customer: subscription.customer,
          status: subscription.status,
        });
        break;
      }

      default:
        log.info("Unhandled event type", { type: event.type, eventId: event.id });
    }
  } catch (err) {
    // Log but don't return error — we want Stripe to know we received the event
    log.error(
      `Error processing ${event.type}`,
      { eventId: event.id },
      err instanceof Error ? err : new Error(String(err))
    );
  }

  // Mark as processed for idempotency
  markProcessed(event.id);

  return res.json({ received: true });
}
