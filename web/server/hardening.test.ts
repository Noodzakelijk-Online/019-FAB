/**
 * Tests for production hardening: sanitization, validation schemas, and security patterns.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { appRouter } from "./routers";
import type { TrpcContext } from "./_core/context";
import { sanitizeText, sanitizeRichContent, sanitizeSlug, sanitizeEmail } from "./lib/sanitize";
import {
  emailSchema,
  nameSchema,
  waitlistJoinSchema,
  contactSubmitSchema,
  blogSlugSchema,
  stripeCheckoutSchema,
  stripeVerifySessionSchema,
} from "@shared/validation";

// ── Mock dependencies ──────────────────────────────────────────

vi.mock("./db", () => ({
  addToWaitlist: vi.fn().mockResolvedValue({ success: true, duplicate: false }),
  getWaitlistCount: vi.fn().mockResolvedValue(1),
  getWaitlistEntries: vi.fn().mockResolvedValue([]),
  getWaitlistStats: vi.fn().mockResolvedValue({}),
  addContactMessage: vi.fn().mockResolvedValue({ id: 1 }),
  getContactMessages: vi.fn().mockResolvedValue([]),
  getContactMessageCount: vi.fn().mockResolvedValue(0),
  updateContactMessageStatus: vi.fn(),
  createBlogPost: vi.fn().mockResolvedValue({ id: 1 }),
  updateBlogPost: vi.fn(),
  deleteBlogPost: vi.fn(),
  getBlogPostBySlug: vi.fn(),
  getBlogPostById: vi.fn(),
  getPublishedBlogPosts: vi.fn().mockResolvedValue([]),
  getAllBlogPosts: vi.fn().mockResolvedValue([]),
  getBlogPostCount: vi.fn().mockResolvedValue(0),
}));

vi.mock("./_core/notification", () => ({
  notifyOwner: vi.fn().mockResolvedValue(true),
}));

vi.mock("./stripe/stripe", () => ({
  getStripe: vi.fn().mockReturnValue({}),
  getOrCreateStripeCustomer: vi.fn().mockResolvedValue("cus_test"),
  createCheckoutSession: vi.fn().mockResolvedValue("https://checkout.stripe.com/test"),
  retrieveCheckoutSession: vi.fn(),
  getCustomerSubscriptions: vi.fn().mockResolvedValue({ data: [] }),
  listCustomerInvoices: vi.fn().mockResolvedValue({ data: [] }),
}));

import { addContactMessage } from "./db";

// ── Helpers ────────────────────────────────────────────────────

type AuthenticatedUser = NonNullable<TrpcContext["user"]>;

function createPublicContext(): TrpcContext {
  return {
    user: null,
    req: { protocol: "https", headers: {} } as TrpcContext["req"],
    res: { clearCookie: vi.fn() } as unknown as TrpcContext["res"],
  };
}

function createAuthContext(overrides?: Partial<AuthenticatedUser>): TrpcContext {
  return {
    user: {
      id: 1,
      openId: "test-openid",
      email: "user@example.com",
      name: "Test User",
      loginMethod: "manus",
      role: "user",
      createdAt: new Date(),
      updatedAt: new Date(),
      lastSignedIn: new Date(),
      stripeCustomerId: null,
      ...overrides,
    },
    req: { protocol: "https", headers: {} } as TrpcContext["req"],
    res: { clearCookie: vi.fn() } as unknown as TrpcContext["res"],
  };
}

function createAdminContext(): TrpcContext {
  return createAuthContext({ role: "admin" });
}

// ═══════════════════════════════════════════════════════════════
// SANITIZATION UNIT TESTS
// ═══════════════════════════════════════════════════════════════

describe("sanitizeText", () => {
  it("strips all HTML tags", () => {
    expect(sanitizeText("<script>alert('xss')</script>")).toBe("");
    expect(sanitizeText("<b>bold</b>")).toBe("bold");
    expect(sanitizeText('<img src="x" onerror="alert(1)">')).toBe("");
  });

  it("preserves plain text", () => {
    expect(sanitizeText("Hello World")).toBe("Hello World");
    expect(sanitizeText("John O'Brien")).toBe("John O'Brien");
  });

  it("trims whitespace", () => {
    expect(sanitizeText("  hello  ")).toBe("hello");
  });

  it("handles empty string", () => {
    expect(sanitizeText("")).toBe("");
  });

  it("strips event handlers in attributes", () => {
    expect(sanitizeText('<div onmouseover="alert(1)">test</div>')).toBe("test");
  });
});

describe("sanitizeRichContent", () => {
  it("allows safe formatting tags", () => {
    expect(sanitizeRichContent("<strong>bold</strong>")).toContain("<strong>");
    expect(sanitizeRichContent("<em>italic</em>")).toContain("<em>");
    expect(sanitizeRichContent("<h2>heading</h2>")).toContain("<h2>");
  });

  it("strips script tags", () => {
    const result = sanitizeRichContent('<script>alert("xss")</script><p>safe</p>');
    expect(result).not.toContain("<script>");
    expect(result).toContain("<p>safe</p>");
  });

  it("strips iframe tags", () => {
    const result = sanitizeRichContent('<iframe src="evil.com"></iframe>');
    expect(result).not.toContain("<iframe>");
  });

  it("strips event handler attributes", () => {
    const result = sanitizeRichContent('<p onclick="alert(1)">click me</p>');
    expect(result).not.toContain("onclick");
    expect(result).toContain("<p>click me</p>");
  });

  it("adds rel=noopener noreferrer to links", () => {
    const result = sanitizeRichContent('<a href="https://example.com">link</a>');
    expect(result).toContain('rel="noopener noreferrer"');
  });

  it("strips javascript: URLs from links", () => {
    const result = sanitizeRichContent('<a href="javascript:alert(1)">link</a>');
    expect(result).not.toContain("javascript:");
  });
});

describe("sanitizeSlug", () => {
  it("lowercases and strips special characters", () => {
    expect(sanitizeSlug("Hello World!")).toBe("helloworld");
    expect(sanitizeSlug("My-Blog-Post")).toBe("my-blog-post");
  });

  it("collapses multiple hyphens", () => {
    expect(sanitizeSlug("hello---world")).toBe("hello-world");
  });

  it("strips leading/trailing hyphens", () => {
    expect(sanitizeSlug("-hello-world-")).toBe("hello-world");
  });

  it("allows alphanumeric and hyphens", () => {
    expect(sanitizeSlug("post-123-test")).toBe("post-123-test");
  });
});

describe("sanitizeEmail", () => {
  it("lowercases and trims", () => {
    expect(sanitizeEmail("  Test@Example.COM  ")).toBe("test@example.com");
  });

  it("strips HTML from email", () => {
    expect(sanitizeEmail("<script>alert(1)</script>test@example.com")).toBe("test@example.com");
  });
});

// ═══════════════════════════════════════════════════════════════
// VALIDATION SCHEMA TESTS
// ═══════════════════════════════════════════════════════════════

describe("emailSchema", () => {
  it("accepts valid emails", () => {
    expect(emailSchema.parse("user@example.com")).toBe("user@example.com");
    expect(emailSchema.parse("USER@Example.COM")).toBe("user@example.com");
  });

  it("rejects invalid emails", () => {
    expect(() => emailSchema.parse("not-an-email")).toThrow();
    expect(() => emailSchema.parse("@missing.com")).toThrow();
    expect(() => emailSchema.parse("")).toThrow();
  });

  it("rejects emails exceeding max length", () => {
    const longEmail = "a".repeat(310) + "@example.com";
    expect(() => emailSchema.parse(longEmail)).toThrow();
  });
});

describe("nameSchema", () => {
  it("accepts valid names", () => {
    expect(nameSchema.parse("John")).toBe("John");
    expect(nameSchema.parse("  Jane  ")).toBe("Jane");
  });

  it("rejects empty names", () => {
    expect(() => nameSchema.parse("")).toThrow();
  });

  it("rejects names exceeding max length", () => {
    expect(() => nameSchema.parse("a".repeat(101))).toThrow();
  });
});

describe("blogSlugSchema", () => {
  it("accepts valid slugs", () => {
    expect(blogSlugSchema.parse("my-blog-post")).toBe("my-blog-post");
    expect(blogSlugSchema.parse("post-123")).toBe("post-123");
  });

  it("rejects slugs with uppercase", () => {
    expect(() => blogSlugSchema.parse("My-Post")).toThrow();
  });

  it("rejects slugs with special characters", () => {
    expect(() => blogSlugSchema.parse("my post!")).toThrow();
    expect(() => blogSlugSchema.parse("my_post")).toThrow();
  });
});

describe("stripeCheckoutSchema", () => {
  it("accepts valid checkout input", () => {
    const result = stripeCheckoutSchema.parse({
      origin: "https://example.com",
      productKey: "payAsYouGo",
    });
    expect(result.origin).toBe("https://example.com");
    expect(result.productKey).toBe("payAsYouGo");
  });

  it("rejects invalid origin URL", () => {
    expect(() =>
      stripeCheckoutSchema.parse({ origin: "not-a-url", productKey: "payAsYouGo" })
    ).toThrow();
  });

  it("defaults productKey to payAsYouGo", () => {
    const result = stripeCheckoutSchema.parse({ origin: "https://example.com" });
    expect(result.productKey).toBe("payAsYouGo");
  });
});

describe("stripeVerifySessionSchema", () => {
  it("accepts valid session IDs", () => {
    const result = stripeVerifySessionSchema.parse({ sessionId: "cs_test_123" });
    expect(result.sessionId).toBe("cs_test_123");
  });

  it("rejects session IDs without cs_ prefix", () => {
    expect(() =>
      stripeVerifySessionSchema.parse({ sessionId: "invalid_123" })
    ).toThrow();
  });

  it("rejects empty session ID", () => {
    expect(() => stripeVerifySessionSchema.parse({ sessionId: "" })).toThrow();
  });
});

// ═══════════════════════════════════════════════════════════════
// INTEGRATION: XSS PREVENTION IN PROCEDURES
// ═══════════════════════════════════════════════════════════════

describe("XSS prevention in contact form", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sanitizes HTML in contact form fields before storing", async () => {
    const ctx = createPublicContext();
    const caller = appRouter.createCaller(ctx);
    const mockAdd = addContactMessage as ReturnType<typeof vi.fn>;

    await caller.contact.submit({
      firstName: '<script>alert("xss")</script>John',
      lastName: '<img src=x onerror=alert(1)>Doe',
      email: "test@example.com",
      subject: '<b>Important</b> subject',
      message: 'Hello <script>document.cookie</script> this is a test message',
    });

    expect(mockAdd).toHaveBeenCalledWith(
      expect.objectContaining({
        firstName: expect.not.stringContaining("<script>"),
        lastName: expect.not.stringContaining("<img"),
        subject: expect.not.stringContaining("<b>"),
        message: expect.not.stringContaining("<script>"),
      })
    );
  });
});

// ═══════════════════════════════════════════════════════════════
// AUTHORIZATION TESTS
// ═══════════════════════════════════════════════════════════════

describe("Authorization enforcement", () => {
  it("admin procedures reject unauthenticated users", async () => {
    const ctx = createPublicContext();
    const caller = appRouter.createCaller(ctx);

    await expect(caller.waitlist.list()).rejects.toThrow();
    await expect(caller.contact.count()).rejects.toThrow();
    await expect(caller.blog.list()).rejects.toThrow();
  });

  it("admin procedures reject non-admin users", async () => {
    const ctx = createAuthContext({ role: "user" });
    const caller = appRouter.createCaller(ctx);

    await expect(caller.waitlist.list()).rejects.toThrow();
    await expect(caller.contact.count()).rejects.toThrow();
    await expect(caller.blog.list()).rejects.toThrow();
  });

  it("admin procedures accept admin users", async () => {
    const ctx = createAdminContext();
    const caller = appRouter.createCaller(ctx);

    // These should not throw
    await caller.waitlist.list();
    await caller.contact.count();
    await caller.blog.list();
  });

  it("protected procedures reject unauthenticated users", async () => {
    const ctx = createPublicContext();
    const caller = appRouter.createCaller(ctx);

    await expect(
      caller.stripe.createCheckout({
        origin: "https://example.com",
        productKey: "payAsYouGo",
      })
    ).rejects.toThrow();
  });
});

// ═══════════════════════════════════════════════════════════════
// INPUT BOUNDARY TESTS
// ═══════════════════════════════════════════════════════════════

describe("Input boundary validation", () => {
  it("rejects contact message shorter than 10 chars", async () => {
    const ctx = createPublicContext();
    const caller = appRouter.createCaller(ctx);

    await expect(
      caller.contact.submit({
        firstName: "John",
        lastName: "Doe",
        email: "test@example.com",
        subject: "Test",
        message: "Short",
      })
    ).rejects.toThrow();
  });

  it("rejects contact message longer than 5000 chars", async () => {
    const ctx = createPublicContext();
    const caller = appRouter.createCaller(ctx);

    await expect(
      caller.contact.submit({
        firstName: "John",
        lastName: "Doe",
        email: "test@example.com",
        subject: "Test",
        message: "x".repeat(5001),
      })
    ).rejects.toThrow();
  });

  it("rejects blog slug with invalid characters", async () => {
    const ctx = createAdminContext();
    const caller = appRouter.createCaller(ctx);

    await expect(
      caller.blog.create({
        title: "Test Post",
        slug: "Invalid Slug!",
        excerpt: "Test excerpt",
        content: "Test content",
      })
    ).rejects.toThrow();
  });

  it("rejects negative blog post ID", async () => {
    const ctx = createAdminContext();
    const caller = appRouter.createCaller(ctx);

    await expect(caller.blog.byId({ id: -1 })).rejects.toThrow();
    await expect(caller.blog.delete({ id: 0 })).rejects.toThrow();
  });
});
