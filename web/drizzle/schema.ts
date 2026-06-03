import {
  boolean,
  index,
  int,
  mysqlEnum,
  mysqlTable,
  text,
  timestamp,
  varchar,
} from "drizzle-orm/mysql-core";

/**
 * Core user table backing auth flow.
 * Indexes on email and stripeCustomerId for lookup performance.
 */
export const users = mysqlTable(
  "users",
  {
    id: int("id").autoincrement().primaryKey(),
    openId: varchar("openId", { length: 64 }).notNull().unique(),
    name: text("name"),
    email: varchar("email", { length: 320 }),
    loginMethod: varchar("loginMethod", { length: 64 }),
    role: mysqlEnum("role", ["user", "admin"]).default("user").notNull(),
    createdAt: timestamp("createdAt").defaultNow().notNull(),
    updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
    lastSignedIn: timestamp("lastSignedIn").defaultNow().notNull(),
    stripeCustomerId: varchar("stripeCustomerId", { length: 255 }),
  },
  (table) => [
    index("idx_users_email").on(table.email),
    index("idx_users_stripe_customer").on(table.stripeCustomerId),
    index("idx_users_role").on(table.role),
  ]
);

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;

/**
 * Waitlist signups.
 * Unique constraint on email prevents duplicates.
 * Index on createdAt for admin listing sorted by date.
 */
export const waitlist = mysqlTable(
  "waitlist",
  {
    id: int("id").autoincrement().primaryKey(),
    email: varchar("email", { length: 320 }).notNull().unique(),
    firstName: varchar("firstName", { length: 100 }),
    lastName: varchar("lastName", { length: 100 }),
    source: varchar("source", { length: 50 }).default("website"),
    createdAt: timestamp("createdAt").defaultNow().notNull(),
  },
  (table) => [
    index("idx_waitlist_created").on(table.createdAt),
  ]
);

export type WaitlistEntry = typeof waitlist.$inferSelect;
export type InsertWaitlistEntry = typeof waitlist.$inferInsert;

/**
 * Contact form messages.
 * Indexes on status (for admin filtering) and createdAt (for sorting).
 */
export const contactMessages = mysqlTable(
  "contact_messages",
  {
    id: int("id").autoincrement().primaryKey(),
    firstName: varchar("firstName", { length: 100 }).notNull(),
    lastName: varchar("lastName", { length: 100 }).notNull(),
    email: varchar("email", { length: 320 }).notNull(),
    subject: varchar("subject", { length: 100 }).notNull(),
    message: text("message").notNull(),
    status: mysqlEnum("status", ["new", "read", "replied", "archived"])
      .default("new")
      .notNull(),
    createdAt: timestamp("createdAt").defaultNow().notNull(),
  },
  (table) => [
    index("idx_contact_status").on(table.status),
    index("idx_contact_created").on(table.createdAt),
    index("idx_contact_email").on(table.email),
  ]
);

export type ContactMessage = typeof contactMessages.$inferSelect;
export type InsertContactMessage = typeof contactMessages.$inferInsert;

/**
 * Blog posts.
 * Unique constraint on slug for URL routing.
 * Composite index on (published, publishedAt) for efficient public listing.
 * Index on category for filtered queries.
 */
export const blogPosts = mysqlTable(
  "blog_posts",
  {
    id: int("id").autoincrement().primaryKey(),
    title: varchar("title", { length: 255 }).notNull(),
    titleNl: varchar("titleNl", { length: 255 }),
    slug: varchar("slug", { length: 255 }).notNull().unique(),
    excerpt: text("excerpt").notNull(),
    excerptNl: text("excerptNl"),
    content: text("content").notNull(),
    contentNl: text("contentNl"),
    category: varchar("category", { length: 50 }).default("update").notNull(),
    coverImage: varchar("coverImage", { length: 500 }),
    published: boolean("published").default(false).notNull(),
    authorId: int("authorId"),
    readTimeMinutes: int("readTimeMinutes").default(3),
    createdAt: timestamp("createdAt").defaultNow().notNull(),
    updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
    publishedAt: timestamp("publishedAt"),
  },
  (table) => [
    index("idx_blog_published_date").on(table.published, table.publishedAt),
    index("idx_blog_category").on(table.category),
    index("idx_blog_author").on(table.authorId),
  ]
);

export type BlogPost = typeof blogPosts.$inferSelect;
export type InsertBlogPost = typeof blogPosts.$inferInsert;
