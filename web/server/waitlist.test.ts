import { describe, expect, it, vi, beforeEach } from "vitest";
import { appRouter } from "./routers";
import type { TrpcContext } from "./_core/context";

// Mock the db module
vi.mock("./db", () => ({
  addToWaitlist: vi.fn(),
  getWaitlistCount: vi.fn(),
}));

// Mock the notification module
vi.mock("./_core/notification", () => ({
  notifyOwner: vi.fn().mockResolvedValue(true),
}));

import { addToWaitlist, getWaitlistCount } from "./db";

function createPublicContext(): TrpcContext {
  return {
    user: null,
    req: {
      protocol: "https",
      headers: {},
    } as TrpcContext["req"],
    res: {
      clearCookie: vi.fn(),
    } as unknown as TrpcContext["res"],
  };
}

describe("waitlist.join", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("registers a new email successfully", async () => {
    const mockAdd = addToWaitlist as ReturnType<typeof vi.fn>;
    mockAdd.mockResolvedValue({ success: true, duplicate: false });
    const mockCount = getWaitlistCount as ReturnType<typeof vi.fn>;
    mockCount.mockResolvedValue(42);

    const ctx = createPublicContext();
    const caller = appRouter.createCaller(ctx);

    const result = await caller.waitlist.join({
      email: "test@example.com",
      firstName: "John",
    });

    expect(result).toEqual({ success: true, message: "registered" });
    expect(mockAdd).toHaveBeenCalledWith({
      email: "test@example.com",
      firstName: "John",
      lastName: null,
      source: "website",
    });
  });

  it("handles duplicate email gracefully", async () => {
    const mockAdd = addToWaitlist as ReturnType<typeof vi.fn>;
    mockAdd.mockResolvedValue({ success: false, duplicate: true });

    const ctx = createPublicContext();
    const caller = appRouter.createCaller(ctx);

    const result = await caller.waitlist.join({
      email: "existing@example.com",
    });

    expect(result).toEqual({ success: true, message: "already_registered" });
  });

  it("trims and lowercases the email", async () => {
    const mockAdd = addToWaitlist as ReturnType<typeof vi.fn>;
    mockAdd.mockResolvedValue({ success: true, duplicate: false });
    const mockCount = getWaitlistCount as ReturnType<typeof vi.fn>;
    mockCount.mockResolvedValue(1);

    const ctx = createPublicContext();
    const caller = appRouter.createCaller(ctx);

    await caller.waitlist.join({
      email: "Test@Example.COM",
      firstName: "  Jane  ",
    });

    expect(mockAdd).toHaveBeenCalledWith(
      expect.objectContaining({
        email: "test@example.com",
        firstName: "Jane",
      })
    );
  });

  it("rejects invalid email format", async () => {
    const ctx = createPublicContext();
    const caller = appRouter.createCaller(ctx);

    await expect(
      caller.waitlist.join({ email: "not-an-email" })
    ).rejects.toThrow();
  });
});

describe("waitlist.count", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns the current waitlist count", async () => {
    const mockCount = getWaitlistCount as ReturnType<typeof vi.fn>;
    mockCount.mockResolvedValue(99);

    const ctx = createPublicContext();
    const caller = appRouter.createCaller(ctx);

    const result = await caller.waitlist.count();

    expect(result).toEqual({ count: 99 });
    expect(mockCount).toHaveBeenCalled();
  });
});
