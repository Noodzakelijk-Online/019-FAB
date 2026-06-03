import { COOKIE_NAME } from "@shared/const";
import {
  waitlistJoinSchema,
  contactSubmitSchema,
  contactListSchema,
  contactUpdateStatusSchema,
  blogCreateSchema,
  blogUpdateSchema,
  blogSlugSchema,
} from "@shared/validation";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { stripeRouter } from "./routers/stripe";
import { publicProcedure, router, adminProcedure } from "./_core/trpc";
import {
  addToWaitlist,
  getWaitlistCount,
  getWaitlistEntries,
  getWaitlistStats,
  addContactMessage,
  getContactMessages,
  getContactMessageCount,
  updateContactMessageStatus,
  createBlogPost,
  updateBlogPost,
  deleteBlogPost,
  getBlogPostBySlug,
  getBlogPostById,
  getPublishedBlogPosts,
  getAllBlogPosts,
  getBlogPostCount,
} from "./db";
import { notifyOwner } from "./_core/notification";
import { sanitizeText, sanitizeRichContent, sanitizeSlug } from "./lib/sanitize";
import { createLogger } from "./lib/logger";
import { z } from "zod";

const log = createLogger("Router");

export const appRouter = router({
  system: systemRouter,
  stripe: stripeRouter,

  auth: router({
    me: publicProcedure.query(opts => opts.ctx.user),
    logout: publicProcedure.mutation(({ ctx }) => {
      const cookieOptions = getSessionCookieOptions(ctx.req);
      ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 });
      return { success: true } as const;
    }),
  }),

  waitlist: router({
    join: publicProcedure
      .input(waitlistJoinSchema)
      .mutation(async ({ input }) => {
        // Sanitize all text inputs to prevent stored XSS
        const sanitizedEmail = sanitizeText(input.email).toLowerCase();
        const sanitizedFirst = input.firstName ? sanitizeText(input.firstName) : null;
        const sanitizedLast = input.lastName ? sanitizeText(input.lastName) : null;

        const result = await addToWaitlist({
          email: sanitizedEmail,
          firstName: sanitizedFirst,
          lastName: sanitizedLast,
          source: "website",
        });

        if (result.duplicate) {
          return { success: true, message: "already_registered" } as const;
        }

        const count = await getWaitlistCount();
        log.info("New waitlist signup", { email: sanitizedEmail, total: count });

        await notifyOwner({
          title: `New waitlist signup: ${sanitizedEmail}`,
          content: `${sanitizedFirst || ""} ${sanitizedLast || ""} (${sanitizedEmail}) just joined the FAB waitlist.\n\nTotal signups: ${count}.`,
        }).catch((err) => {
          log.warn("Failed to notify owner about waitlist signup", {}, err instanceof Error ? err : undefined);
        });

        return { success: true, message: "registered" } as const;
      }),

    count: publicProcedure.query(async () => {
      const count = await getWaitlistCount();
      return { count };
    }),

    list: adminProcedure.query(async () => {
      return getWaitlistEntries();
    }),

    stats: adminProcedure.query(async () => {
      return getWaitlistStats();
    }),
  }),

  contact: router({
    submit: publicProcedure
      .input(contactSubmitSchema)
      .mutation(async ({ input }) => {
        // Sanitize all text inputs
        const sanitized = {
          firstName: sanitizeText(input.firstName),
          lastName: sanitizeText(input.lastName),
          email: sanitizeText(input.email).toLowerCase(),
          subject: sanitizeText(input.subject),
          message: sanitizeText(input.message),
        };

        await addContactMessage(sanitized);

        log.info("New contact message", {
          from: sanitized.email,
          subject: sanitized.subject,
        });

        await notifyOwner({
          title: `New contact message from ${sanitized.firstName} ${sanitized.lastName}`,
          content: `From: ${sanitized.firstName} ${sanitized.lastName} (${sanitized.email})\nSubject: ${sanitized.subject}\n\n${sanitized.message}`,
        }).catch((err) => {
          log.warn("Failed to notify owner about contact message", {}, err instanceof Error ? err : undefined);
        });

        return { success: true } as const;
      }),

    list: adminProcedure
      .input(contactListSchema)
      .query(async ({ input }) => {
        return getContactMessages(input);
      }),

    count: adminProcedure.query(async () => {
      const count = await getContactMessageCount();
      return { count };
    }),

    updateStatus: adminProcedure
      .input(contactUpdateStatusSchema)
      .mutation(async ({ input }) => {
        await updateContactMessageStatus(input.id, input.status);
        return { success: true } as const;
      }),
  }),

  blog: router({
    published: publicProcedure
      .input(
        z.object({
          category: z.string().max(50).optional(),
          limit: z.number().int().min(1).max(50).optional(),
        }).optional()
      )
      .query(async ({ input }) => {
        return getPublishedBlogPosts(input);
      }),

    bySlug: publicProcedure
      .input(z.object({ slug: blogSlugSchema }))
      .query(async ({ input }) => {
        const post = await getBlogPostBySlug(input.slug);
        if (!post || !post.published) return null;
        return post;
      }),

    list: adminProcedure.query(async () => {
      return getAllBlogPosts();
    }),

    byId: adminProcedure
      .input(z.object({ id: z.number().int().positive() }))
      .query(async ({ input }) => {
        return getBlogPostById(input.id);
      }),

    count: adminProcedure.query(async () => {
      const count = await getBlogPostCount();
      return { count };
    }),

    create: adminProcedure
      .input(blogCreateSchema)
      .mutation(async ({ input, ctx }) => {
        // Sanitize content fields to prevent stored XSS
        const sanitized = {
          title: sanitizeText(input.title),
          titleNl: input.titleNl ? sanitizeText(input.titleNl) : null,
          slug: sanitizeSlug(input.slug),
          excerpt: sanitizeText(input.excerpt),
          excerptNl: input.excerptNl ? sanitizeText(input.excerptNl) : null,
          content: sanitizeRichContent(input.content),
          contentNl: input.contentNl ? sanitizeRichContent(input.contentNl) : null,
          category: sanitizeText(input.category),
          coverImage: input.coverImage || null,
          published: input.published,
          readTimeMinutes: input.readTimeMinutes,
          authorId: ctx.user.id,
          publishedAt: input.published ? new Date() : null,
        };

        const result = await createBlogPost(sanitized);
        log.info("Blog post created", { id: result.id, slug: sanitized.slug });
        return result;
      }),

    update: adminProcedure
      .input(blogUpdateSchema)
      .mutation(async ({ input }) => {
        const { id, ...rawData } = input;

        // Sanitize any provided text fields
        const data: Record<string, unknown> = {};
        if (rawData.title !== undefined) data.title = sanitizeText(rawData.title);
        if (rawData.titleNl !== undefined) data.titleNl = rawData.titleNl ? sanitizeText(rawData.titleNl) : null;
        if (rawData.slug !== undefined) data.slug = sanitizeSlug(rawData.slug);
        if (rawData.excerpt !== undefined) data.excerpt = sanitizeText(rawData.excerpt);
        if (rawData.excerptNl !== undefined) data.excerptNl = rawData.excerptNl ? sanitizeText(rawData.excerptNl) : null;
        if (rawData.content !== undefined) data.content = sanitizeRichContent(rawData.content);
        if (rawData.contentNl !== undefined) data.contentNl = rawData.contentNl ? sanitizeRichContent(rawData.contentNl) : null;
        if (rawData.category !== undefined) data.category = sanitizeText(rawData.category);
        if (rawData.coverImage !== undefined) data.coverImage = rawData.coverImage || null;
        if (rawData.published !== undefined) data.published = rawData.published;
        if (rawData.readTimeMinutes !== undefined) data.readTimeMinutes = rawData.readTimeMinutes;

        // If publishing for the first time, set publishedAt
        if (data.published === true) {
          const existing = await getBlogPostById(id);
          if (existing && !existing.publishedAt) {
            data.publishedAt = new Date();
          }
        }

        await updateBlogPost(id, data);
        log.info("Blog post updated", { id });
        return { success: true } as const;
      }),

    delete: adminProcedure
      .input(z.object({ id: z.number().int().positive() }))
      .mutation(async ({ input }) => {
        await deleteBlogPost(input.id);
        log.info("Blog post deleted", { id: input.id });
        return { success: true } as const;
      }),
  }),
});

export type AppRouter = typeof appRouter;
