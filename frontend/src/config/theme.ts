/**
 * Cosmic Intelligence Theme Configuration
 *
 * This theme creates a sophisticated "mission control" aesthetic with:
 * - Deep space backgrounds
 * - Golden accents for primary actions
 * - Teal highlights for data visualization
 * - Soft glows on interactive elements
 */

export const CosmicTheme = {
  background: {
    deepSpace: '#0a0e1a',    // Deep Space Blue (darker than current slate-900)
    midnight: '#1a1f35',      // Midnight Blue (surfaces/cards)
    elevated: '#252b45',      // Slightly lighter for hover states
    card: '#1e293b'          // Card background (extracted from timeline cards: slate-800)
  },
  accent: {
    solarGold: '#f59e0b',     // Solar Flare Gold (primary actions)
    starlightTeal: '#06b6d4', // Starlight Teal (data viz, secondary)
    cosmicLatte: '#f5f5f0'    // Cosmic Latte (text)
  },
  text: {
    primary: '#f5f5f0',       // High contrast text
    secondary: '#9ca3af',     // Lower contrast metadata
    muted: '#6b7280'          // Very low contrast
  },
  glow: {
    gold: '0 0 20px rgba(245, 158, 11, 0.3)',
    teal: '0 0 20px rgba(6, 182, 212, 0.3)'
  }
} as const;

// Type exports for TypeScript usage
export type CosmicThemeColors = typeof CosmicTheme;
