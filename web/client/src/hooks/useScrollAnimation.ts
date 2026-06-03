import { useEffect, useRef, useState, useCallback } from "react";

interface ScrollAnimationOptions {
  /** IntersectionObserver threshold (0–1). Default: 0.1 */
  threshold?: number;
  /** Root margin for early/late triggering. Default: "-50px" */
  rootMargin?: string;
  /** Only animate once (true) or every time element enters viewport. Default: true */
  once?: boolean;
}

/**
 * Hook that returns a ref and a boolean `isVisible`.
 * Attach the ref to any element; `isVisible` becomes true
 * when the element scrolls into view.
 */
export function useScrollAnimation(options: ScrollAnimationOptions = {}) {
  const { threshold = 0.1, rootMargin = "-50px", once = true } = options;
  const ref = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          if (once) {
            observer.unobserve(element);
          }
        } else if (!once) {
          setIsVisible(false);
        }
      },
      { threshold, rootMargin }
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, [threshold, rootMargin, once]);

  return { ref, isVisible };
}

/**
 * Hook for staggered children animations.
 * Returns a ref for the parent container and `isVisible`.
 * Use the `staggerIndex` in child styles to calculate delay.
 */
export function useStaggerAnimation(options: ScrollAnimationOptions = {}) {
  return useScrollAnimation(options);
}

/**
 * CSS class helper for scroll animations.
 * Returns Tailwind classes based on visibility state.
 */
export function getScrollClasses(
  isVisible: boolean,
  variant: "fade-up" | "fade-in" | "slide-left" | "slide-right" = "fade-up",
  delay: number = 0
): string {
  const baseTransition = "transition-all duration-700 ease-out";
  const delayClass = delay > 0 ? `delay-[${delay}ms]` : "";

  if (!isVisible) {
    switch (variant) {
      case "fade-up":
        return `${baseTransition} ${delayClass} opacity-0 translate-y-8`;
      case "fade-in":
        return `${baseTransition} ${delayClass} opacity-0`;
      case "slide-left":
        return `${baseTransition} ${delayClass} opacity-0 -translate-x-8`;
      case "slide-right":
        return `${baseTransition} ${delayClass} opacity-0 translate-x-8`;
    }
  }

  return `${baseTransition} ${delayClass} opacity-100 translate-y-0 translate-x-0`;
}
