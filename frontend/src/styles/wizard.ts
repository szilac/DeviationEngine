/**
 * Wizard Styling Utilities
 *
 * Only the exports actively used by wizard components.
 */

/**
 * Character count colour coding
 */
export const getCharacterCountColor = (current: number, max: number): string => {
  const percentage = (current / max) * 100;
  if (current > max) return 'text-rubric';
  if (percentage >= 90) return 'text-warning';
  if (percentage >= 75) return 'text-gold-dim';
  return 'text-faint';
};

export const getCharacterCountStyle = (current: number, max: number): string => {
  const color = getCharacterCountColor(current, max);
  return `font-mono text-[10px] ${color}`;
};

/**
 * Scenario type icon configuration
 */
export const SCENARIO_ICONS = {
  local_deviation: {
    icon: '/icons/icon_local_deviation_default.png',
    label: 'Local Deviation',
    tooltip: 'A single historical event is altered (e.g., assassination prevented, treaty signed)',
  },
  global_deviation: {
    icon: '/icons/icon_global_deviation_default.png',
    label: 'Global Deviation',
    tooltip: 'Large-scale world event (e.g., pandemic, war outcome, economic collapse)',
  },
  reality_fracture: {
    icon: '/icons/icon_reality_fracture_default.png',
    label: 'Reality Fracture',
    tooltip: 'Break in natural laws or physics (e.g., magic becomes real, new technology emerges)',
  },
  geological_shift: {
    icon: '/icons/icon_geological_shift_default.png',
    label: 'Geological Shift',
    tooltip: 'Physical environment changes (e.g., earthquake, volcano, climate shift)',
  },
  external_intervention: {
    icon: '/icons/icon_external_intervention_default.png',
    label: 'External Intervention',
    tooltip: 'Time traveler or alien intervention alters history',
  },
} as const;

/**
 * Workflow type configuration
 */
export const WORKFLOW_CONFIG = {
  direct: {
    title: 'Direct Generation',
    description: 'Faster generation with immediate results',
    estimatedTime: '1-2 minutes',
    features: [
      'Structured analysis report',
      'Optional narrative generation',
      'Immediate results',
    ],
  },
  skeleton: {
    title: 'Skeleton Workflow',
    description: 'Editable timeline with more control',
    estimatedTime: '2-5 minutes total',
    features: [
      'Generate series of editable events',
      'Review and modify events',
      'Approve for final generation',
    ],
  },
} as const;

/**
 * Narrative mode configuration
 */
export const NARRATIVE_MODE_CONFIG = {
  none: {
    title: 'None',
    description: 'Structured report only',
    estimatedTime: '~60 seconds',
    badge: 'Fastest',
  },
  basic: {
    title: 'Basic Narrative',
    description: 'Single-pass story generation',
    estimatedTime: '~90 seconds',
    badge: 'Recommended',
  },
  advanced_omniscient: {
    title: 'Advanced: Omniscient Historian',
    description: 'Two-pass neutral perspective',
    estimatedTime: '~120 seconds',
    badge: 'Advanced',
  },
  advanced_custom_pov: {
    title: 'Advanced: Custom Perspective',
    description: 'Two-pass from custom viewpoint',
    estimatedTime: '~120 seconds',
    badge: 'Advanced',
  },
} as const;
