/**
 * ManuscriptRuling — Fixed overlay that renders subtle horizontal ruling lines
 * across the entire viewport, evoking medieval vellum manuscript paper.
 * Applied once at root level; pointer-events: none so it never blocks interaction.
 */
export default function ManuscriptRuling() {
  return (
    <div
      aria-hidden="true"
      style={{
        position: 'fixed',
        inset: 0,
        pointerEvents: 'none',
        zIndex: 0,
        backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 27px, rgba(210,180,80,0.05) 28px)',
      }}
    />
  );
}
