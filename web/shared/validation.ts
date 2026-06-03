/**
 * Shared Zod validation schemas — used by both server procedures and tests.
 * Centralizing schemas prevents drift between frontend validation and backend enforcement.
 */
import { z } from "zod";

// ── Common field schemas ────────────────────────────────────────

export const emailSchema = z
  .string()
  .email("Invalid email address")
  .max(320, "Email too long")
  .transform((v) => v.toLowerCase().trim());

export const nameSchema = z
  .string()
  .min(1, "Name is required")
  .max(100, "Name too long")
  .transform((v) => v.trim());

export const optionalNameSchema = z
  .string()
  .max(100, "Name too long")
  .optional()
  .transform((v) => v?.trim() || undefined);

// ── Waitlist schemas ────────────────────────────────────────────

export const waitlistJoinSchema = z.object({
  email: emailSchema,
  firstName: optionalNameSchema,
  lastName: optionalNameSchema,
});

// ── Contact form schemas ────────────────────────────────────────

export const contactSubmitSchema = z.object({
  firstName: nameSchema,
  lastName: nameSchema,
  email: emailSchema,
  subject: z
    .string()
    .min(1, "Subject is required")
    .max(100, "Subject too long")
    .transform((v) => v.trim()),
  message: z
    .string()
    .min(10, "Message must be at least 10 characters")
    .max(5000, "Message too long")
    .transform((v) => v.trim()),
});

// ── Blog post schemas ───────────────────────────────────────────

export const blogSlugSchema = z
  .string()
  .min(1)
  .max(255)
  .regex(/^[a-z0-9\-]+$/, "Slug must contain only lowercase letters, numbers, and hyphens");

export const blogCreateSchema = z.object({
  title: z.string().min(1, "Title is required").max(255),
  titleNl: z.string().max(255).optional(),
  slug: blogSlugSchema,
  excerpt: z.string().min(1, "Excerpt is required"),
  excerptNl: z.string().optional(),
  content: z.string().min(1, "Content is required"),
  contentNl: z.string().optional(),
  category: z.string().max(50).default("update"),
  coverImage: z.string().url("Invalid image URL").max(500).optional().or(z.literal("")),
  published: z.boolean().default(false),
  readTimeMinutes: z.number().int().min(1).max(60).default(3),
});

export const blogUpdateSchema = z.object({
  id: z.number().int().positive(),
  title: z.string().min(1).max(255).optional(),
  titleNl: z.string().max(255).optional(),
  slug: blogSlugSchema.optional(),
  excerpt: z.string().min(1).optional(),
  excerptNl: z.string().optional(),
  content: z.string().min(1).optional(),
  contentNl: z.string().optional(),
  category: z.string().max(50).optional(),
  coverImage: z.string().url().max(500).optional().or(z.literal("")),
  published: z.boolean().optional(),
  readTimeMinutes: z.number().int().min(1).max(60).optional(),
});

// ── Stripe schemas ──────────────────────────────────────────────

export const stripeCheckoutSchema = z.object({
  origin: z.string().url("Invalid origin URL"),
  productKey: z.string().min(1).max(50).default("payAsYouGo"),
});

export const stripePortalSchema = z.object({
  origin: z.string().url("Invalid origin URL"),
});

export const stripeVerifySessionSchema = z.object({
  sessionId: z
    .string()
    .min(1, "Session ID is required")
    .regex(/^cs_/, "Invalid session ID format"),
});

// ── Contact message status ──────────────────────────────────────

export const contactStatusSchema = z.enum(["new", "read", "replied", "archived"]);

export const contactUpdateStatusSchema = z.object({
  id: z.number().int().positive(),
  status: contactStatusSchema,
});

export const contactListSchema = z.object({
  status: contactStatusSchema.optional(),
}).optional();
