/**
 * Rate limiting configuration using express-rate-limit
 * Battle-tested package with 3M+ weekly downloads.
 *
 * Provides tiered rate limits for different endpoint types:
 * - Strict: auth, payment endpoints (prevent abuse)
 * - Standard: public form submissions (prevent spam)
 * - Relaxed: general API reads (prevent scraping)
 * - Webhook: Stripe webhook endpoint (generous but bounded)
 */
import rateLimit from "express-rate-limit";

/**
 * Strict rate limiter for sensitive operations:
 * - Stripe checkout creation
 * - Authentication endpoints
 *
 * 10 requests per 15 minutes per IP
 */
export const strictLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 10,
  standardHeaders: "draft-7",
  legacyHeaders: false,
  validate: { trustProxy: false, xForwardedForHeader: false },
  message: {
    error: "Too many requests from this IP. Please try again later.",
    retryAfter: 15,
  },
});

/**
 * Standard rate limiter for public form submissions:
 * - Waitlist signups
 * - Contact form
 *
 * 20 requests per 15 minutes per IP
 */
export const standardLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 20,
  standardHeaders: "draft-7",
  legacyHeaders: false,
  validate: { trustProxy: false, xForwardedForHeader: false },
  message: {
    error: "Too many submissions. Please wait a few minutes before trying again.",
    retryAfter: 15,
  },
});

/**
 * Relaxed rate limiter for general API reads:
 * - Blog listing
 * - Product info
 * - Public queries
 *
 * 100 requests per 15 minutes per IP
 */
export const relaxedLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
  standardHeaders: "draft-7",
  legacyHeaders: false,
  validate: { trustProxy: false, xForwardedForHeader: false },
  message: {
    error: "Rate limit exceeded. Please slow down.",
    retryAfter: 15,
  },
});

/**
 * Webhook rate limiter — generous but still bounded:
 * 100 requests per minute (Stripe sends bursts during events)
 */
export const webhookLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 100,
  standardHeaders: "draft-7",
  legacyHeaders: false,
  validate: { trustProxy: false, xForwardedForHeader: false },
  message: { error: "Too many webhook requests." },
});
