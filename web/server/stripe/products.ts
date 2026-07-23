/**
 * FAB Stripe Product & Price Configuration
 *
 * Products are created dynamically in Stripe on first checkout.
 * This file defines the product catalog for the Pay-As-You-Go tier.
 */

export interface FABProduct {
  id: string;
  name: string;
  nameNl: string;
  description: string;
  descriptionNl: string;
  priceAmountCents: number; // Deprecated compatibility field; FAB has no fixed fee.
  usageMultiplier: number;
  currency: string;
  interval: "month" | "year";
  features: string[];
  featuresNl: string[];
  popular: boolean;
}

export const FAB_PRODUCTS: Record<string, FABProduct> = {
  payAsYouGo: {
    id: "fab-payg-monthly",
    name: "FAB Pay-As-You-Go",
    nameNl: "FAB Betaal per Gebruik",
    description:
      "Full access to FAB's financial orchestration platform with usage-based pricing.",
    descriptionNl:
      "Volledige toegang tot FAB's financiële orkestratieplatform met prijzen op basis van gebruik.",
    priceAmountCents: 0,
    usageMultiplier: 2.5,
    currency: "eur",
    interval: "month",
    features: [
      "Full financial orchestration",
      "AI-powered document processing",
      "Real-time cost dashboard",
      "Configurable spending caps",
      "PGB & Wajong/WIA support",
      "GDPR data export & deletion",
      "Priority email support",
    ],
    featuresNl: [
      "Volledige financiële orkestratie",
      "AI-gestuurde documentverwerking",
      "Realtime kostendashboard",
      "Configureerbare bestedingslimieten",
      "PGB & Wajong/WIA ondersteuning",
      "AVG data-export & verwijdering",
      "Prioriteit e-mailondersteuning",
    ],
    popular: true,
  },
};

export type ProductKey = keyof typeof FAB_PRODUCTS;

/**
 * Get a product by its key
 */
export function getProductByKey(key: ProductKey): FABProduct {
  return FAB_PRODUCTS[key];
}

/**
 * Get the default (most popular) product
 */
export function getDefaultProduct(): FABProduct {
  return FAB_PRODUCTS.payAsYouGo;
}
