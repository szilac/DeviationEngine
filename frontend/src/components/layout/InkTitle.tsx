import { motion, useReducedMotion } from 'motion/react';
import type { CSSProperties, ReactNode } from 'react';

interface InkTitleProps {
  as?: 'h1' | 'h2' | 'h3';
  className?: string;
  style?: CSSProperties;
  delay?: number;
  children: ReactNode;
}

export default function InkTitle({
  as = 'h1',
  className,
  style,
  delay = 0.1,
  children,
}: InkTitleProps) {
  const shouldReduce = useReducedMotion();

  const inkVariants = {
    hidden: { opacity: shouldReduce ? 1 : 0, filter: shouldReduce ? 'blur(0px)' : 'blur(5px)' },
    visible: { opacity: 1, filter: 'blur(0px)' },
  };

  const transition = {
    duration: shouldReduce ? 0 : 0.55,
    ease: [0.4, 0, 0.2, 1] as const,
    delay: shouldReduce ? 0 : delay,
  };

  const shared = {
    className,
    style,
    variants: inkVariants,
    initial: 'hidden' as const,
    animate: 'visible' as const,
    transition,
  };

  if (as === 'h2') return <motion.h2 {...shared}>{children}</motion.h2>;
  if (as === 'h3') return <motion.h3 {...shared}>{children}</motion.h3>;
  return <motion.h1 {...shared}>{children}</motion.h1>;
}
