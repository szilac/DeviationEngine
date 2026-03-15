import { useEffect, useState } from 'react';

/**
 * useScrollSpy Hook
 *
 * Tracks which section is currently visible in the viewport using IntersectionObserver.
 * Updates activeSection as the user scrolls through content.
 *
 * @param sectionIds - Array of section element IDs to observe
 * @param options - IntersectionObserver options
 * @returns The ID of the currently active section, or undefined
 */
export const useScrollSpy = (
  sectionIds: string[],
  options: IntersectionObserverInit = { rootMargin: '-20% 0px -35% 0px' }
): string | undefined => {
  const [activeSection, setActiveSection] = useState<string | undefined>(undefined);

  useEffect(() => {
    const observers: IntersectionObserver[] = [];

    sectionIds.forEach((id) => {
      const element = document.getElementById(id);
      if (!element) return;

      const observer = new IntersectionObserver(([entry]) => {
        if (entry.isIntersecting) {
          setActiveSection(id);
        }
      }, options);

      observer.observe(element);
      observers.push(observer);
    });

    return () => {
      observers.forEach((observer) => observer.disconnect());
    };
  }, [sectionIds.join(','), JSON.stringify(options)]);

  return activeSection;
};
