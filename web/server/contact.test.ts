import { describe, expect, it, vi, beforeEach } from "vitest";
import { appRouter } from "./routers";
import type { TrpcContext } from "./_core/context";

// Mock the db module
vi.mock("./db", () => ({
  addToWaitlist: vi.fn(),
  getWaitlistCount: vi.fn(),
  getWaitlistEntries: vi.fn(),
  getWaitlistStats: vi.fn(),
  addContactMessage: vi.fn(),
  getContactMessages: vi.fn(),
  getContactMessageCount: vi.fn(),
  updateContactMessageStatus: vi.fn(),
}));

// Mock the notification module
vi.mock("./_core/notification", () => ({
  notifyOwner: vi.fn().mockResolvedValue(true),
}));

import {
  addContactMessage,
  getContactMessages,
  getContactMessageCount,
  updateContactMessageStatus,
} from "./db";

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

function createAdminContext(): TrpcContext {
  return {
    user: {
      id: 1,
      openId: "admin-user",
      email: "admin@fab.nl",
      name: "Admin",
      loginMethod: "manus",
      role: "admin",
      createdAt: new Date(),
      updatedAt: new Date(),
      lastSignedIn: new Date(),
    },
    req: {
      protocol: "https",
      headers: {},
    } as TrpcContext["req"],
    res: {
      clearCookie: vi.fn(),
    } as unknown as TrpcContext["res"],
  };
}

function createUserContext(): TrpcContext {
  return {
    user: {
      id: 2,
      openId: "regular-user",
      email: "user@example.com",
      name: "Regular User",
      loginMethod: "manus",
      role: "user",
      createdAt: new Date(),
      updatedAt: new Date(),
      lastSignedIn: new Date(),
    },
    req: {
      protocol: "https",
      headers: {},
    } as TrpcContext["req"],
    res: {
      clearCookie: vi.fn(),
    } as unknown as TrpcContext["res"],
  };
}

describe("contact.submit", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submits a contact message successfully", async () => {
    const mockAdd = addContactMessage as ReturnType<typeof vi.fn>;
    mockAdd.mockResolvedValue({ success: true });

    const ctx = createPublicContext();
    const caller = appRouter.createCaller(ctx);

    const result = await caller.contact.submit({
      firstName: "John",
      lastName: "Doe",
      email: "john@example.com",
      subject: "general",
      message: "Hello, I have a question about FAB.",
    });

    expect(result).toEqual({ success: true });
    expect(mockAdd).toHaveBeenCalledWith({
      firstName: "John",
      lastName: "Doe",
      email: "john@example.com",
      subject: "general",
      message: "Hello, I have a question about FAB.",
    });
  });

  it("trims and lowercases the email", async () => {
    const mockAdd = addContactMessage as ReturnType<typeof vi.fn>;
    mockAdd.mockResolvedValue({ success: true });

    const ctx = createPublicContext();
    const caller = appRouter.createCaller(ctx);

    await caller.contact.submit({
      firstName: "  Jane  ",
      lastName: "  Smith  ",
      email: "Jane@Example.COM",
      subject: "demo",
      message: "I would like to see a demo of FAB please.",
    });

    expect(mockAdd).toHaveBeenCalledWith(
      expect.objectContaining({
        firstName: "Jane",
        lastName: "Smith",
        email: "jane@example.com",
      })
    );
  });

  it("rejects invalid email format", async () => {
    const ctx = createPublicContext();
    const caller = appRouter.createCaller(ctx);

    await expect(
      caller.contact.submit({
        firstName: "Test",
        lastName: "User",
        email: "not-an-email",
        subject: "general",
        message: "This should fail validation.",
      })
    ).rejects.toThrow();
  });

  it("rejects message shorter than 10 characters", async () => {
    const ctx = createPublicContext();
    const caller = appRouter.createCaller(ctx);

    await expect(
      caller.contact.submit({
        firstName: "Test",
        lastName: "User",
        email: "test@example.com",
        subject: "general",
        message: "Short",
      })
    ).rejects.toThrow();
  });
});

describe("contact.list (admin)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns messages for admin users", async () => {
    const mockGet = getContactMessages as ReturnType<typeof vi.fn>;
    mockGet.mockResolvedValue([
      {
        id: 1,
        firstName: "John",
        lastName: "Doe",
        email: "john@example.com",
        subject: "general",
        message: "Test message",
        status: "new",
        createdAt: new Date(),
      },
    ]);

    const ctx = createAdminContext();
    const caller = appRouter.createCaller(ctx);

    const result = await caller.contact.list({});

    expect(result).toHaveLength(1);
    expect(result[0].firstName).toBe("John");
    expect(mockGet).toHaveBeenCalled();
  });

  it("rejects non-admin users", async () => {
    const ctx = createUserContext();
    const caller = appRouter.createCaller(ctx);

    await expect(caller.contact.list({})).rejects.toThrow();
  });

  it("rejects unauthenticated users", async () => {
    const ctx = createPublicContext();
    const caller = appRouter.createCaller(ctx);

    await expect(caller.contact.list({})).rejects.toThrow();
  });
});

describe("contact.updateStatus (admin)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("updates message status for admin users", async () => {
    const mockUpdate = updateContactMessageStatus as ReturnType<typeof vi.fn>;
    mockUpdate.mockResolvedValue(undefined);

    const ctx = createAdminContext();
    const caller = appRouter.createCaller(ctx);

    const result = await caller.contact.updateStatus({
      id: 1,
      status: "read",
    });

    expect(result).toEqual({ success: true });
    expect(mockUpdate).toHaveBeenCalledWith(1, "read");
  });

  it("rejects non-admin users from updating status", async () => {
    const ctx = createUserContext();
    const caller = appRouter.createCaller(ctx);

    await expect(
      caller.contact.updateStatus({ id: 1, status: "read" })
    ).rejects.toThrow();
  });
});
