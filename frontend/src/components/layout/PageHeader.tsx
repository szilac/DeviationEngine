import { NavLink } from 'react-router-dom';

const NAV_LINKS = [
  { to: '/console',  label: 'Console'  },
  { to: '/library',  label: 'Library'  },
  { to: '/atlas',    label: 'Atlas'    },
  { to: '/settings', label: 'Settings' },
] as const;

export default function PageHeader() {
  return (
    <header
      className="relative z-10 bg-vellum border-b border-border"
      style={{ borderTop: '2px solid #7A5C10' }}
    >
      {/* Skip to main content — visible on focus for keyboard users */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:bg-vellum focus:text-gold focus:border focus:border-gold focus:px-3 focus:py-1 focus:font-mono focus:text-xs focus:tracking-widest focus:uppercase"
      >
        Skip to main content
      </a>
      <div className="flex items-center justify-between px-6 h-14">

        {/* Logo */}
        <NavLink
          to="/"
          className="flex items-center gap-2.5 hover:opacity-85 transition-opacity duration-150"
        >
          <img
            src="/DeviationEngine_logo.png"
            alt="Deviation Engine"
            className="h-8 w-8 object-cover rounded-full"
          />
          <span className="font-display text-gold text-3xl leading-none">
            Deviation Engine
          </span>
        </NavLink>

        {/* Nav */}
        <nav className="flex items-center gap-1">
          {/* Separator after logo */}
          <span className="text-faint font-mono text-sm mr-3">|</span>

          {NAV_LINKS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => [
                'px-3 py-1 font-mono text-xs tracking-widest uppercase transition-colors duration-150',
                isActive
                  ? 'text-gold border-b border-gold'
                  : 'text-dim hover:text-ink',
              ].join(' ')}
            >
              {label}
            </NavLink>
          ))}

          {/* Quantum state tag */}
          <NavLink
            to="/about"
            aria-label="About"
            className="ml-4 font-mono text-xs text-quantum hover:text-wave transition-colors duration-150"
          >
            <span aria-hidden="true">|ψ⟩</span>
          </NavLink>
        </nav>
      </div>
    </header>
  );
}
