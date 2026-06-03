import { Heart } from "lucide-react";
import { Link } from "wouter";
import { useLanguage } from "@/contexts/LanguageContext";

export default function Footer() {
  const { t } = useLanguage();

  return (
    <footer className="bg-charcoal text-white/70 py-16">
      <div className="container">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-10 mb-12">
          {/* Brand */}
          <div className="sm:col-span-2 lg:col-span-1">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-9 h-9 rounded-xl bg-teal flex items-center justify-center">
                <span className="text-white font-serif text-lg">F</span>
              </div>
              <span className="font-serif text-xl text-white">FAB</span>
            </div>
            <p className="text-sm leading-relaxed max-w-xs">
              {t("footer.desc")}
            </p>
          </div>

          {/* Product */}
          <div>
            <h4 className="text-white font-sans font-semibold text-sm mb-4">
              {t("footer.product")}
            </h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/how-it-works" className="hover:text-white transition-colors">
                  {t("nav.howItWorks")}
                </Link>
              </li>
              <li>
                <a href="/#features" className="hover:text-white transition-colors">
                  {t("nav.features")}
                </a>
              </li>
              <li>
                <a href="/#pricing" className="hover:text-white transition-colors">
                  {t("nav.pricing")}
                </a>
              </li>
              <li>
                <a href="/#security" className="hover:text-white transition-colors">
                  {t("nav.security")}
                </a>
              </li>
            </ul>
          </div>

          {/* Company */}
          <div>
            <h4 className="text-white font-sans font-semibold text-sm mb-4">
              {t("footer.company")}
            </h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/about" className="hover:text-white transition-colors">
                  {t("nav.about")}
                </Link>
              </li>
              <li>
                <Link href="/faq" className="hover:text-white transition-colors">
                  {t("nav.faq")}
                </Link>
              </li>
              <li>
                <a href="/#impact" className="hover:text-white transition-colors">
                  {t("impact.label")}
                </a>
              </li>
              <li>
                <Link href="/contact" className="hover:text-white transition-colors">
                  {t("nav.contact")}
                </Link>
              </li>
              <li>
                <Link href="/blog" className="hover:text-white transition-colors">
                  {t("nav.blog")}
                </Link>
              </li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h4 className="text-white font-sans font-semibold text-sm mb-4">
              {t("footer.legal")}
            </h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/privacy" className="hover:text-white transition-colors">
                  {t("footer.legal.privacypolicy")}
                </Link>
              </li>
              <li>
                <Link href="/terms" className="hover:text-white transition-colors">
                  {t("footer.legal.termsofservice")}
                </Link>
              </li>
              <li>
                <Link href="/gdpr" className="hover:text-white transition-colors">
                  {t("footer.legal.gdpr")}
                </Link>
              </li>
              <li>
                <Link href="/cookies" className="hover:text-white transition-colors">
                  {t("footer.legal.cookiepolicy")}
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-white/10 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-white/50">
            &copy; {new Date().getFullYear()} FAB — Fully Automated Bookkeeping. {t("footer.rights")}
          </p>
          <p className="text-xs text-white/50 flex items-center gap-1">
            {t("footer.madeWith")} <Heart className="w-3 h-3 text-sage" /> {t("footer.inNL")}
          </p>
        </div>
      </div>
    </footer>
  );
}
