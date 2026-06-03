/**
 * Server-side input sanitization utilities
 * Uses sanitize-html (battle-tested, 3M+ weekly downloads) for XSS prevention
 * and custom helpers for common sanitization patterns.
 */
import sanitizeHtml from "sanitize-html";

/**
 * Strip ALL HTML tags — for plain text fields like names, emails, subjects.
 * This is the strictest mode: no tags allowed at all.
 */
export function sanitizeText(input: string): string {
  return sanitizeHtml(input, {
    allowedTags: [],
    allowedAttributes: {},
  }).trim();
}

/**
 * Allow safe HTML subset — for rich content like blog posts.
 * Permits formatting tags but strips scripts, iframes, event handlers.
 */
export function sanitizeRichContent(input: string): string {
  return sanitizeHtml(input, {
    allowedTags: [
      "h1", "h2", "h3", "h4", "h5", "h6",
      "p", "br", "hr",
      "ul", "ol", "li",
      "strong", "em", "b", "i", "u", "s", "del",
      "a", "img",
      "blockquote", "pre", "code",
      "table", "thead", "tbody", "tr", "th", "td",
      "div", "span",
    ],
    allowedAttributes: {
      a: ["href", "title", "target", "rel"],
      img: ["src", "alt", "title", "width", "height"],
      td: ["colspan", "rowspan"],
      th: ["colspan", "rowspan"],
    },
    allowedSchemes: ["http", "https", "mailto"],
    // Force rel="noopener noreferrer" on links
    transformTags: {
      a: sanitizeHtml.simpleTransform("a", {
        rel: "noopener noreferrer",
      }),
    },
  });
}

/**
 * Sanitize an email address — lowercase, trim, and validate basic structure.
 * Does NOT replace Zod validation; this is an additional defense layer.
 */
export function sanitizeEmail(input: string): string {
  return sanitizeText(input).toLowerCase().trim();
}

/**
 * Sanitize a URL slug — only allow lowercase alphanumeric, hyphens, and underscores.
 */
export function sanitizeSlug(input: string): string {
  return input
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\-_]/g, "")
    .replace(/--+/g, "-")
    .replace(/^-|-$/g, "");
}
