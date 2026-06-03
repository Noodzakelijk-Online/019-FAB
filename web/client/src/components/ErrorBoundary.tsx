/**
 * Production-grade React Error Boundary
 *
 * Catches unhandled errors in the React component tree and displays
 * a user-friendly fallback UI instead of a blank screen.
 *
 * Features:
 * - componentDidCatch for error logging (extend with Sentry/LogRocket)
 * - "Try Again" button to reset state without full page reload
 * - Shows stack trace only in development mode
 * - Styled to match FAB design system
 */
import { Component, type ReactNode, type ErrorInfo } from "react";
import { Button } from "@/components/ui/button";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log to console — extend with external error tracking service in production
    console.error("[ErrorBoundary] Uncaught error:", error);
    console.error("[ErrorBoundary] Component stack:", errorInfo.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex items-center justify-center min-h-[400px] p-8 bg-background">
          <div className="flex flex-col items-center w-full max-w-md text-center space-y-6">
            <div className="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center">
              <AlertTriangle className="w-8 h-8 text-red-500" />
            </div>

            <div className="space-y-2">
              <h2 className="text-xl font-semibold text-foreground">
                Something went wrong
              </h2>
              <p className="text-muted-foreground text-sm leading-relaxed">
                An unexpected error occurred. Please try again or refresh the
                page. If the problem persists, contact support.
              </p>
            </div>

            {import.meta.env.DEV && this.state.error && (
              <div className="w-full p-4 rounded-lg bg-muted overflow-auto max-h-40">
                <pre className="text-xs text-muted-foreground whitespace-break-spaces text-left">
                  {this.state.error.stack || this.state.error.message}
                </pre>
              </div>
            )}

            <div className="flex gap-3 justify-center">
              <Button
                onClick={this.handleReset}
                className="bg-teal hover:bg-teal-light text-white"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Try Again
              </Button>
              <Button
                variant="outline"
                onClick={() => (window.location.href = "/")}
                className="border-teal/20 text-teal hover:bg-teal/5"
              >
                <Home className="w-4 h-4 mr-2" />
                Go Home
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
