# FAB Website TODO

## Follow-up 1: Custom Favicon & Open Graph Meta Tags
- [x] Generate custom FAB favicon (512x512 PNG)
- [x] Convert to ICO and apple-touch-icon formats
- [x] Upload to CDN via manus-upload-file --webdev
- [x] Generate Open Graph image (1200x630)
- [x] Update index.html with favicon links
- [x] Add Open Graph meta tags (title, description, image, url, type)
- [x] Add Twitter Card meta tags

## Follow-up 2: Waitlist Backend with Database
- [x] Upgrade project to web-db-user template
- [x] Create waitlist table in drizzle schema (email, name, situation, source)
- [x] Push database migration
- [x] Add waitlist database helpers (addToWaitlist, getWaitlistEntries)
- [x] Create tRPC waitlist.join public procedure with Zod validation
- [x] Create tRPC waitlist.list protected procedure for admin access
- [x] Connect WaitlistModal form to tRPC backend
- [x] Handle success, duplicate email, and error states in modal
- [x] Add "already registered" translation keys (EN/NL)
- [x] Write vitest tests for waitlist procedures (5 tests)
- [x] Verify end-to-end: form → API → database → success confirmation

## Follow-up 3: Scroll-Based Entrance Animations
- [x] Create useScrollAnimation hook with IntersectionObserver
- [x] Verify Home page already has framer-motion whileInView animations
- [x] Verify About page already has framer-motion whileInView animations
- [x] Verify FAQ page already has framer-motion whileInView animations
- [x] Verify Contact page already has framer-motion whileInView animations
- [x] Add framer-motion scroll animations to HowItWorks page (all sections)
- [x] Test animations work correctly in browser

## Previous Work (Completed)
- [x] Full EN/NL bilingual translations across all 5 pages
- [x] Waitlist modal wired to all CTA buttons site-wide
- [x] How It Works page link in navbar on all pages
- [x] Dutch translations for FAQ Q&A (30+ pairs across 6 categories)
- [x] Contact form placeholders translated
- [x] HowItWorks page content fully translated
- [x] About page content fully translated

## Follow-up 4: Admin Dashboard for Waitlist Management
- [x] Create admin dashboard page with sidebar layout
- [x] Display waitlist signups in a sortable table
- [x] Add filtering by situation type and date range
- [x] Add CSV export functionality
- [x] Show signup growth chart over time
- [x] Protect admin routes with role-based access control

## Follow-up 5: Confirmation Email Flow for Waitlist Signups
- [x] Implement email notification on new waitlist signup using notifyOwner
- [x] Send welcome/confirmation message to owner when someone joins
- [x] Include signup details (name, email, situation) in notification

## Follow-up 6: Contact Form Backend
- [x] Create contact_messages table in drizzle schema
- [x] Push database migration for contact_messages
- [x] Add tRPC procedure for contact form submission
- [x] Connect Contact.tsx form to tRPC backend
- [x] Trigger owner notification on new contact form submission
- [x] Show success/error states in Contact form UI
- [x] Write vitest tests for contact and admin procedures

## Follow-up 7: Testimonials / Social Proof Section
- [x] Create testimonials data with bilingual EN/NL content
- [x] Build testimonials carousel/grid component on homepage
- [x] Add social proof stats or trust badges
- [x] Add translation keys for testimonials section

## Follow-up 8: Blog / Updates Section
- [x] Create blog_posts table in drizzle schema
- [x] Push database migration for blog_posts
- [x] Add tRPC procedures for blog CRUD (admin) and public listing
- [x] Create blog listing page (/blog) with card grid layout
- [x] Create individual blog post page (/blog/:slug)
- [x] Add blog management to admin dashboard
- [x] Add "Latest Updates" preview section on homepage
- [x] Add translation keys for blog section
- [x] Seed blog with 3 initial posts (announcement, technology, guide)
- [x] Add technology and guide category translations and filter buttons
- [x] Blog link in footer (already present)

## Follow-up 9: Stripe Payment Integration
- [x] Add Stripe feature via webdev_add_feature
- [x] Configure Stripe secret key (auto-injected)
- [x] Create Stripe products definition (products.ts)
- [x] Build Stripe tRPC router (checkout, portal, subscription status, invoices, verify)
- [x] Connect pricing section Pay-As-You-Go button to Stripe checkout
- [x] Create payment success page (/payment/success)
- [x] Create payment cancel page (/payment/cancel)
- [x] Add Stripe info card to admin dashboard overview
- [x] Add stripeCustomerId field to users table
- [x] Write vitest tests for Stripe procedures (11 tests)
- [x] All 26 tests passing (Stripe + Contact + Waitlist + Auth)

## Follow-up 10: User Account / Subscription Page
- [x] Create Account page (/account) with subscription status display
- [x] Show current plan details (Free vs Pay-As-You-Go)
- [x] Add "Manage Billing" button linking to Stripe Customer Portal
- [x] Display invoice history with download links
- [x] Add account page to navbar for authenticated users
- [x] Add bilingual translations for account page (EN/NL)

## Follow-up 11: Privacy Policy & Terms of Service Pages
- [x] Create Privacy Policy page (/privacy) with GDPR-compliant content
- [x] Create Terms of Service page (/terms) with proper legal content
- [x] Create Cookie Policy page (/cookies) with cookie usage details
- [x] Create GDPR page (/gdpr) with data rights information
- [x] Wire all footer legal links to actual pages
- [x] Add bilingual translations for legal pages (EN/NL)
- [x] No new backend procedures needed (frontend-only pages)

## Follow-up 12: Integrations Section & Orchestration Emphasis
- [x] Create Integrations section on homepage showing connected platforms (MijnGeldzaken.nl, Wave Apps, banks, SVB, Gmail/Drive)
- [x] Generate orchestration hero image and upload to CDN
- [x] Update How It Works page Step 1 & Step 3 to emphasize active management of external platforms
- [x] Add bilingual translation keys for integrations content (EN/NL) - 30+ new keys
- [x] Update homepage How It Works summary to reinforce orchestration narrative
- [x] Add callout box: "Not just connecting — actively managing"
- [x] QA all changes across both languages - verified

## Follow-up 13: Production Hardening — Battle-Tested Code
- [x] Audit all server routers for input validation gaps
- [x] Add rate limiting (express-rate-limit) — strict/standard/relaxed/webhook tiers
- [x] Add proper error handling with TRPCError typed responses
- [x] Harden Stripe webhook with idempotency guard and structured logging
- [x] Add shared Zod validation schemas (shared/validation.ts) for all tRPC inputs
- [x] Add React Error Boundary with retry, dev/prod modes, FAB styling
- [x] Harden client-side forms with maxLength, email regex, disabled states
- [x] Add database indexes (email, slug, createdAt, published, status, stripeCustomerId)
- [x] Add Helmet security headers (CSP, HSTS, X-Frame-Options, etc.)
- [x] Install battle-tested packages: helmet, express-rate-limit, sanitize-html
- [x] Add 41 hardening vitest tests (sanitization, validation, auth, XSS, boundaries)
- [x] Add structured logging (server/lib/logger.ts) with levels and JSON output
- [x] Sanitize all user inputs with sanitize-html (XSS prevention)
- [x] TypeScript 0 errors, trust proxy configured, graceful shutdown handler
- [x] All 67 tests passing across 5 test files

## Follow-up 14: End-User Experience Audit
- [x] Audit homepage: hero, navigation, all 12 sections, scroll behavior, CTAs
- [x] Audit How It Works page: 3 steps, platform cards, data flow diagram
- [x] Audit About page: narrative, mission, values, statistics
- [x] Audit FAQ page: 6 categories, search, accordion expand/collapse
- [x] Audit Contact page: form fields, character counter, contact info cards
- [x] Audit Blog listing: 3 posts, category filters, search
- [x] Audit Blog post detail: back link, meta, content rendering
- [x] Audit Account page: profile, subscription, invoice history
- [x] Audit Legal pages: Privacy, Terms, GDPR, Cookie — all render properly
- [x] Audit Waitlist modal: validation, close button, field behavior
- [x] Audit Language toggle: EN/NL switch works across all pages
- [x] Audit Admin dashboard: Overview, Waitlist, Messages, Blog — all functional
- [x] Fix ISSUE-A: Blog post title duplication (strip leading H1 from content)
- [x] Verify rate limiter warnings resolved (stale logs from previous session)
- [x] Verify 0 browser console errors, 0 network errors
- [x] All 67 tests still passing after fixes
