import { eq, sql, desc, and, gte, lte } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import { InsertUser, users, waitlist, InsertWaitlistEntry, contactMessages, InsertContactMessage, blogPosts, InsertBlogPost } from "../drizzle/schema";
import { ENV } from './_core/env';

let _db: ReturnType<typeof drizzle> | null = null;

// Lazily create the drizzle instance so local tooling can run without a DB.
export async function getDb() {
  if (!_db && process.env.DATABASE_URL) {
    try {
      _db = drizzle(process.env.DATABASE_URL);
    } catch (error) {
      console.warn("[Database] Failed to connect:", error);
      _db = null;
    }
  }
  return _db;
}

export async function upsertUser(user: InsertUser): Promise<void> {
  if (!user.openId) {
    throw new Error("User openId is required for upsert");
  }

  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot upsert user: database not available");
    return;
  }

  try {
    const values: InsertUser = {
      openId: user.openId,
    };
    const updateSet: Record<string, unknown> = {};

    const textFields = ["name", "email", "loginMethod"] as const;
    type TextField = (typeof textFields)[number];

    const assignNullable = (field: TextField) => {
      const value = user[field];
      if (value === undefined) return;
      const normalized = value ?? null;
      values[field] = normalized;
      updateSet[field] = normalized;
    };

    textFields.forEach(assignNullable);

    if (user.lastSignedIn !== undefined) {
      values.lastSignedIn = user.lastSignedIn;
      updateSet.lastSignedIn = user.lastSignedIn;
    }
    if (user.role !== undefined) {
      values.role = user.role;
      updateSet.role = user.role;
    } else if (user.openId === ENV.ownerOpenId) {
      values.role = 'admin';
      updateSet.role = 'admin';
    }

    if (!values.lastSignedIn) {
      values.lastSignedIn = new Date();
    }

    if (Object.keys(updateSet).length === 0) {
      updateSet.lastSignedIn = new Date();
    }

    await db.insert(users).values(values).onDuplicateKeyUpdate({
      set: updateSet,
    });
  } catch (error) {
    console.error("[Database] Failed to upsert user:", error);
    throw error;
  }
}

export async function getUserByOpenId(openId: string) {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot get user: database not available");
    return undefined;
  }

  const result = await db.select().from(users).where(eq(users.openId, openId)).limit(1);

  return result.length > 0 ? result[0] : undefined;
}

// ── Waitlist ──────────────────────────────────────────────────

export async function addToWaitlist(entry: InsertWaitlistEntry): Promise<{ success: boolean; duplicate: boolean }> {
  const db = await getDb();
  if (!db) {
    throw new Error("Database not available");
  }

  try {
    await db.insert(waitlist).values(entry);
    return { success: true, duplicate: false };
  } catch (error: any) {
    // MySQL duplicate key error code
    if (error?.code === "ER_DUP_ENTRY" || error?.errno === 1062) {
      return { success: false, duplicate: true };
    }
    throw error;
  }
}

export async function getWaitlistCount(): Promise<number> {
  const db = await getDb();
  if (!db) return 0;

  const result = await db.select({ count: sql<number>`count(*)` }).from(waitlist);
  return result[0]?.count ?? 0;
}

export async function getWaitlistEntries(opts?: { situation?: string; from?: Date; to?: Date }) {
  const db = await getDb();
  if (!db) return [];

  return db.select().from(waitlist).orderBy(desc(waitlist.createdAt));
}

// ── Contact Messages ─────────────────────────────────────────

export async function addContactMessage(msg: InsertContactMessage): Promise<{ success: boolean }> {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  await db.insert(contactMessages).values(msg);
  return { success: true };
}

export async function getContactMessages(opts?: { status?: string }) {
  const db = await getDb();
  if (!db) return [];

  if (opts?.status) {
    return db.select().from(contactMessages)
      .where(eq(contactMessages.status, opts.status as any))
      .orderBy(desc(contactMessages.createdAt));
  }
  return db.select().from(contactMessages).orderBy(desc(contactMessages.createdAt));
}

export async function getContactMessageCount(): Promise<number> {
  const db = await getDb();
  if (!db) return 0;

  const result = await db.select({ count: sql<number>`count(*)` }).from(contactMessages);
  return result[0]?.count ?? 0;
}

export async function updateContactMessageStatus(id: number, status: "new" | "read" | "replied" | "archived"): Promise<void> {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  await db.update(contactMessages).set({ status }).where(eq(contactMessages.id, id));
}

// ── Waitlist Stats ───────────────────────────────────────────

export async function getWaitlistStats() {
  const db = await getDb();
  if (!db) return { total: 0, daily: [] as { date: string; count: number }[] };

  const total = await getWaitlistCount();
  const daily = await db.select({
    date: sql<string>`DATE(createdAt)`,
    count: sql<number>`count(*)`,
  }).from(waitlist).groupBy(sql`DATE(createdAt)`).orderBy(sql`DATE(createdAt)`);

  return { total, daily };
}

// ── Blog Posts ─────────────────────────────────────────────────────

export async function createBlogPost(post: InsertBlogPost): Promise<{ id: number }> {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  const result = await db.insert(blogPosts).values(post);
  return { id: Number(result[0].insertId) };
}

export async function updateBlogPost(id: number, data: Partial<InsertBlogPost>): Promise<void> {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  await db.update(blogPosts).set(data).where(eq(blogPosts.id, id));
}

export async function deleteBlogPost(id: number): Promise<void> {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  await db.delete(blogPosts).where(eq(blogPosts.id, id));
}

export async function getBlogPostBySlug(slug: string) {
  const db = await getDb();
  if (!db) return undefined;

  const result = await db.select().from(blogPosts).where(eq(blogPosts.slug, slug)).limit(1);
  return result.length > 0 ? result[0] : undefined;
}

export async function getBlogPostById(id: number) {
  const db = await getDb();
  if (!db) return undefined;

  const result = await db.select().from(blogPosts).where(eq(blogPosts.id, id)).limit(1);
  return result.length > 0 ? result[0] : undefined;
}

export async function getPublishedBlogPosts(opts?: { category?: string; limit?: number }) {
  const db = await getDb();
  if (!db) return [];

  let query = db.select().from(blogPosts)
    .where(eq(blogPosts.published, true))
    .orderBy(desc(blogPosts.publishedAt));

  if (opts?.limit) {
    query = query.limit(opts.limit) as any;
  }

  return query;
}

export async function getAllBlogPosts() {
  const db = await getDb();
  if (!db) return [];

  return db.select().from(blogPosts).orderBy(desc(blogPosts.createdAt));
}

export async function getBlogPostCount(): Promise<number> {
  const db = await getDb();
  if (!db) return 0;

  const result = await db.select({ count: sql<number>`count(*)` }).from(blogPosts);
  return result[0]?.count ?? 0;
}
