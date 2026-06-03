CREATE INDEX `idx_blog_published_date` ON `blog_posts` (`published`,`publishedAt`);--> statement-breakpoint
CREATE INDEX `idx_blog_category` ON `blog_posts` (`category`);--> statement-breakpoint
CREATE INDEX `idx_blog_author` ON `blog_posts` (`authorId`);--> statement-breakpoint
CREATE INDEX `idx_contact_status` ON `contact_messages` (`status`);--> statement-breakpoint
CREATE INDEX `idx_contact_created` ON `contact_messages` (`createdAt`);--> statement-breakpoint
CREATE INDEX `idx_contact_email` ON `contact_messages` (`email`);--> statement-breakpoint
CREATE INDEX `idx_users_email` ON `users` (`email`);--> statement-breakpoint
CREATE INDEX `idx_users_stripe_customer` ON `users` (`stripeCustomerId`);--> statement-breakpoint
CREATE INDEX `idx_users_role` ON `users` (`role`);--> statement-breakpoint
CREATE INDEX `idx_waitlist_created` ON `waitlist` (`createdAt`);