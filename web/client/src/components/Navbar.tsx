import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X, Globe, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link, useLocation } from "wouter";
import { useLanguage } from "@/contexts/LanguageContext";
import { useAuth } from "@/_core/hooks/useAuth";
import { getLoginUrl } from "@/const";
import WaitlistModal from "@/components/WaitlistModal";

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [waitlistOpen, setWaitlistOpen] = useState(false);
  const [location] = useLocation();
  const { lang, setLang, t } = useLanguage();
  const { user, isAuthenticated } = useAuth();

  const isHome = location === "/";

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const sectionLinks = [
    { label: t("nav.features"), href: "#features" },
    { label: t("nav.security"), href: "#security" },
    { label: t("nav.pricing"), href: "#pricing" },
    { label: t("nav.impact"), href: "#impact" },
  ];

  const pageLinks = [
    { label: t("nav.howItWorks"), href: "/how-it-works" },
    { label: t("nav.about"), href: "/about" },
    { label: t("nav.faq"), href: "/faq" },
    { label: t("nav.contact"), href: "/contact" },
    { label: t("nav.blog"), href: "/blog" },
  ];

  const toggleLang = () => setLang(lang === "en" ? "nl" : "en");

  return (
    <>
      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled
            ? "bg-white/90 backdrop-blur-lg shadow-sm border-b border-sand-dark/10"
            : "bg-transparent"
        }`}
      >
        <div className="container flex items-center justify-between h-16 lg:h-20">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-xl bg-teal flex items-center justify-center">
              <span className="text-white font-serif text-lg">F</span>
            </div>
            <span className="font-serif text-xl text-charcoal">FAB</span>
          </Link>

          {/* Desktop links */}
          <div className="hidden lg:flex items-center gap-7">
            {isHome ? (
              <>
                {sectionLinks.map((link) => (
                  <a
                    key={link.href}
                    href={link.href}
                    className="text-sm text-charcoal-light hover:text-teal transition-colors duration-200"
                  >
                    {link.label}
                  </a>
                ))}
                {pageLinks.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className="text-sm text-charcoal-light hover:text-teal transition-colors duration-200"
                  >
                    {link.label}
                  </Link>
                ))}
              </>
            ) : (
              <>
                <Link
                  href="/"
                  className="text-sm text-charcoal-light hover:text-teal transition-colors duration-200"
                >
                  {t("nav.home")}
                </Link>
                {pageLinks.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`text-sm transition-colors duration-200 ${
                      location === link.href
                        ? "text-teal font-medium"
                        : "text-charcoal-light hover:text-teal"
                    }`}
                  >
                    {link.label}
                  </Link>
                ))}
              </>
            )}
          </div>

          {/* Desktop CTA + Language */}
          <div className="hidden lg:flex items-center gap-3">
            {/* Language toggle */}
            <button
              onClick={toggleLang}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-sand-dark/20 hover:border-teal/30 hover:bg-teal/5 transition-all text-sm text-charcoal-light"
              title={lang === "en" ? "Switch to Dutch" : "Schakel naar Engels"}
            >
              <Globe className="w-3.5 h-3.5" />
              <span className="font-sans font-medium text-xs uppercase tracking-wide">
                {lang === "en" ? "NL" : "EN"}
              </span>
            </button>
            {isAuthenticated ? (
              <Link href="/account">
                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-lg border-teal/20 text-teal hover:bg-teal/5"
                >
                  <User className="w-4 h-4 mr-1.5" />
                  {user?.name?.split(" ")[0] || t("nav.account")}
                </Button>
              </Link>
            ) : (
              <>
                <a href={getLoginUrl()}>
                  <Button
                    variant="outline"
                    size="sm"
                    className="rounded-lg border-teal/20 text-teal hover:bg-teal/5"
                  >
                    {t("nav.signIn")}
                  </Button>
                </a>
                <Button
                  size="sm"
                  className="rounded-lg bg-teal hover:bg-teal-light text-white"
                  onClick={() => setWaitlistOpen(true)}
                >
                  {t("nav.getStarted")}
                </Button>
              </>
            )}
          </div>

          {/* Mobile toggle */}
          <div className="lg:hidden flex items-center gap-2">
            <button
              onClick={toggleLang}
              className="p-2 rounded-lg border border-sand-dark/20 text-charcoal-light"
            >
              <Globe className="w-4 h-4" />
            </button>
            <button
              className="p-2 text-charcoal"
              onClick={() => setMobileOpen(!mobileOpen)}
              aria-label="Toggle menu"
            >
              {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        <AnimatePresence>
          {mobileOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="lg:hidden bg-white border-b border-sand-dark/10 overflow-hidden"
            >
              <div className="container py-4 space-y-3">
                {isHome &&
                  sectionLinks.map((link) => (
                    <a
                      key={link.href}
                      href={link.href}
                      className="block py-2 text-charcoal-light hover:text-teal transition-colors"
                      onClick={() => setMobileOpen(false)}
                    >
                      {link.label}
                    </a>
                  ))}
                {!isHome && (
                  <Link
                    href="/"
                    className="block py-2 text-charcoal-light hover:text-teal transition-colors"
                    onClick={() => setMobileOpen(false)}
                  >
                    {t("nav.home")}
                  </Link>
                )}
                {pageLinks.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`block py-2 transition-colors ${
                      location === link.href
                        ? "text-teal font-medium"
                        : "text-charcoal-light hover:text-teal"
                    }`}
                    onClick={() => setMobileOpen(false)}
                  >
                    {link.label}
                  </Link>
                ))}
                {/* Mobile language indicator */}
                <div className="py-2 text-xs text-charcoal-light font-sans">
                  {lang === "en" ? "Language: English" : "Taal: Nederlands"} —{" "}
                  <button onClick={toggleLang} className="text-teal underline">
                    {lang === "en" ? "Switch to Dutch" : "Schakel naar Engels"}
                  </button>
                </div>
                <div className="pt-3 flex gap-3">
                  {isAuthenticated ? (
                    <Link
                      href="/account"
                      className="flex-1"
                      onClick={() => setMobileOpen(false)}
                    >
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full rounded-lg border-teal/20 text-teal"
                      >
                        <User className="w-4 h-4 mr-1.5" />
                        {t("nav.account")}
                      </Button>
                    </Link>
                  ) : (
                    <>
                      <a href={getLoginUrl()} className="flex-1">
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full rounded-lg border-teal/20 text-teal"
                        >
                          {t("nav.signIn")}
                        </Button>
                      </a>
                      <Button
                        size="sm"
                        className="flex-1 rounded-lg bg-teal text-white"
                        onClick={() => {
                          setMobileOpen(false);
                          setWaitlistOpen(true);
                        }}
                      >
                        {t("nav.getStarted")}
                      </Button>
                    </>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </nav>

      <WaitlistModal isOpen={waitlistOpen} onClose={() => setWaitlistOpen(false)} />
    </>
  );
}
