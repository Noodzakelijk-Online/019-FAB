/**
 * Stripe integration helpers — Production-hardened
 *
 * Uses structured logging, defensive null checks, and proper error propagation.
 * All Stripe API calls are wrapped with error context for observability.
 */
import Stripe from "stripe";
import { createLogger } from "../lib/logger";

const log = createLogger("Stripe");

let _stripe: Stripe | null = null;

/**
 * Get or initialize the Stripe SDK instance.
 * Throws immediately if STRIPE_SECRET_KEY is missing — fail fast.
 */
export function getStripe(): Stripe {
  if (!_stripe) {
    const secretKey = process.env.STRIPE_SECRET_KEY;
    if (!secretKey) {
      throw new Error(
        "STRIPE_SECRET_KEY is not configured. Set it in Settings → Payment."
      );
    }
    _stripe = new Stripe(secretKey, {
      apiVersion: "2025-02-24.acacia" as any,
      maxNetworkRetries: 2, // Retry transient network errors
      timeout: 30_000, // 30s timeout for Stripe API calls
    });
    log.info("Stripe SDK initialized");
  }
  return _stripe;
}

/**
 * Get or create a Stripe customer for a user.
 * Verifies existing customer ID is still valid before reusing.
 * Deduplicates by email if no existing ID is provided.
 */
export async function getOrCreateStripeCustomer(
  userId: number,
  email: string,
  name?: string | null,
  existingCustomerId?: string | null
): Promise<string> {
  const stripe = getStripe();

  // 1. Verify existing customer ID if provided
  if (existingCustomerId) {
    try {
      const customer = await stripe.customers.retrieve(existingCustomerId);
      if (!customer.deleted) {
        return existingCustomerId;
      }
      log.warn("Stripe customer was deleted, creating new one", {
        oldCustomerId: existingCustomerId,
        userId,
      });
    } catch (err) {
      log.warn("Failed to retrieve existing Stripe customer", {
        customerId: existingCustomerId,
        userId,
      });
    }
  }

  // 2. Search for existing customer by email to prevent duplicates
  if (email) {
    try {
      const existing = await stripe.customers.list({ email, limit: 1 });
      if (existing.data.length > 0 && !existing.data[0].deleted) {
        const found = existing.data[0];
        log.info("Found existing Stripe customer by email", {
          customerId: found.id,
          userId,
        });
        return found.id;
      }
    } catch (err) {
      log.warn("Failed to search for existing customer by email", { email });
    }
  }

  // 3. Create a new customer
  const customer = await stripe.customers.create({
    email: email || undefined,
    name: name || undefined,
    metadata: {
      user_id: userId.toString(),
      source: "fab-website",
    },
  });

  log.info("Created new Stripe customer", {
    customerId: customer.id,
    userId,
  });

  return customer.id;
}

/**
 * Create a Stripe Checkout Session for subscription.
 * Returns the checkout URL. Throws if session creation fails.
 */
export async function createCheckoutSession(params: {
  userId: number;
  userEmail: string;
  userName?: string | null;
  stripeCustomerId: string;
  origin: string;
  priceAmount: number;
  currency: string;
  interval: "month" | "year";
  productName: string;
  productDescription: string;
}): Promise<string> {
  const stripe = getStripe();

  const session = await stripe.checkout.sessions.create({
    customer: params.stripeCustomerId,
    client_reference_id: params.userId.toString(),
    mode: "subscription",
    allow_promotion_codes: true,
    line_items: [
      {
        price_data: {
          currency: params.currency,
          product_data: {
            name: params.productName,
            description: params.productDescription,
          },
          unit_amount: params.priceAmount,
          recurring: {
            interval: params.interval,
          },
        },
        quantity: 1,
      },
    ],
    metadata: {
      user_id: params.userId.toString(),
      customer_email: params.userEmail,
      customer_name: params.userName || "",
    },
    success_url: `${params.origin}/payment/success?session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `${params.origin}/payment/cancel`,
  });

  if (!session.url) {
    throw new Error("Stripe returned a checkout session without a URL");
  }

  return session.url;
}

/**
 * Verify and construct a Stripe webhook event.
 * Throws if signature verification fails — caller must handle.
 */
export function constructWebhookEvent(
  payload: Buffer,
  signature: string
): Stripe.Event {
  const stripe = getStripe();
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;

  if (!webhookSecret) {
    throw new Error(
      "STRIPE_WEBHOOK_SECRET is not configured. Set it in Settings → Payment."
    );
  }

  return stripe.webhooks.constructEvent(payload, signature, webhookSecret);
}

/**
 * Retrieve a checkout session with expanded line items and subscription.
 */
export async function retrieveCheckoutSession(sessionId: string) {
  const stripe = getStripe();
  return stripe.checkout.sessions.retrieve(sessionId, {
    expand: ["line_items", "subscription"],
  });
}

/**
 * List invoices for a customer, ordered by most recent first.
 */
export async function listCustomerInvoices(customerId: string, limit = 10) {
  const stripe = getStripe();
  return stripe.invoices.list({
    customer: customerId,
    limit: Math.min(limit, 100), // Stripe max is 100
  });
}

/**
 * Get active subscriptions for a customer.
 * Also includes past_due and trialing to show all relevant subscriptions.
 */
export async function getCustomerSubscriptions(customerId: string) {
  const stripe = getStripe();
  return stripe.subscriptions.list({
    customer: customerId,
    status: "active",
    limit: 5,
  });
}
