import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { lazy, Suspense } from "react";
import { Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import { LanguageProvider } from "./contexts/LanguageContext";
const Home = lazy(() => import("./pages/Home"));
const Contact = lazy(() => import("./pages/Contact"));
const About = lazy(() => import("./pages/About"));
const FAQ = lazy(() => import("./pages/FAQ"));
const HowItWorks = lazy(() => import("./pages/HowItWorks"));
const AdminOverview = lazy(() => import("./pages/admin/Overview"));
const AdminWaitlist = lazy(() => import("./pages/admin/Waitlist"));
const AdminMessages = lazy(() => import("./pages/admin/Messages"));
const AdminOperations = lazy(() => import("./pages/admin/Operations"));
const Blog = lazy(() => import("./pages/Blog"));
const BlogPost = lazy(() => import("./pages/BlogPost"));
const AdminBlog = lazy(() => import("./pages/admin/Blog"));
const PaymentSuccess = lazy(() => import("./pages/PaymentSuccess"));
const PaymentCancel = lazy(() => import("./pages/PaymentCancel"));
const Account = lazy(() => import("./pages/Account"));
const PrivacyPolicy = lazy(() => import("./pages/PrivacyPolicy"));
const TermsOfService = lazy(() => import("./pages/TermsOfService"));
const GDPR = lazy(() => import("./pages/GDPR"));
const CookiePolicy = lazy(() => import("./pages/CookiePolicy"));
const NotFound = lazy(() => import("./pages/NotFound"));

function Router() {
  return (
    <Suspense fallback={<div role="status" aria-live="polite" className="route-loading"><span />Loading FAB...</div>}><Switch>
      <Route path={"/"} component={Home} />
      <Route path={"/about"} component={About} />
      <Route path={"/faq"} component={FAQ} />
      <Route path={"/contact"} component={Contact} />
      <Route path={"/how-it-works"} component={HowItWorks} />
      <Route path={"/blog"} component={Blog} />
      <Route path={"/blog/:slug"} component={BlogPost} />
      {/* Payment routes */}
      <Route path="/payment/success" component={PaymentSuccess} />
      <Route path="/payment/cancel" component={PaymentCancel} />
      <Route path="/account" component={Account} />
      {/* Legal pages */}
      <Route path="/privacy" component={PrivacyPolicy} />
      <Route path="/terms" component={TermsOfService} />
      <Route path="/gdpr" component={GDPR} />
      <Route path="/cookies" component={CookiePolicy} />
      {/* Admin routes */}
      <Route path={"/admin"} component={AdminOverview} />
      <Route path={"/admin/operations"} component={AdminOperations} />
      <Route path={"/admin/waitlist"} component={AdminWaitlist} />
      <Route path={"/admin/messages"} component={AdminMessages} />
      <Route path={"/admin/blog"} component={AdminBlog} />
      <Route path={"/404"} component={NotFound} />
      {/* Final fallback route */}
      <Route component={NotFound} />
    </Switch></Suspense>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider
        defaultTheme="light"
      >
        <LanguageProvider>
          <TooltipProvider>
            <Toaster />
            <Router />
          </TooltipProvider>
        </LanguageProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
