import { LANGUAGES, type SupportedLanguage } from '../types';
import { ChevronDown } from 'lucide-react';

interface LanguageSelectorProps {
  currentLanguage: SupportedLanguage;
  onLanguageChange: (lang: SupportedLanguage) => void;
  disabled?: boolean;
  className?: string;
}

export const LanguageSelector = ({
  currentLanguage,
  onLanguageChange,
  disabled = false,
  className = '',
}: LanguageSelectorProps) => {
  const current = LANGUAGES.find((l) => l.code === currentLanguage);

  return (
    <div className={`relative inline-flex items-center ${className}`}>
      <select
        value={currentLanguage}
        onChange={(e) => onLanguageChange(e.target.value as SupportedLanguage)}
        disabled={disabled}
        aria-label="Select language for translation"
        className={[
          'appearance-none bg-transparent',
          'font-mono text-[10px] tracking-widest uppercase',
          'text-dim hover:text-ink',
          'border-b border-border hover:border-gold-dim',
          'pr-5 py-1 pl-0',
          'focus:outline-none focus:border-gold-dim',
          'transition-colors duration-150',
          'cursor-pointer',
          disabled ? 'opacity-40 cursor-not-allowed' : '',
        ].join(' ')}
      >
        {LANGUAGES.map((lang) => (
          <option
            key={lang.code}
            value={lang.code}
            style={{ backgroundColor: '#271E0A', color: '#E8D8A0' }}
          >
            {lang.flag} {lang.nativeName}
          </option>
        ))}
      </select>
      <ChevronDown
        size={9}
        className="absolute right-0 text-faint pointer-events-none"
        aria-hidden
      />
      {current && currentLanguage !== 'en' && (
        <span className="ml-2 font-mono text-[10px] text-quantum tracking-widest">
          {current.flag}
        </span>
      )}
    </div>
  );
};

export default LanguageSelector;
