import * as RadixTabs from '@radix-ui/react-tabs';
import type { ReactNode } from 'react';

export interface TabItem {
  value: string;
  label: string;
}

interface TabsProps {
  value: string;
  onValueChange: (value: string) => void;
  tabs: TabItem[];
  children: ReactNode;
  className?: string;
}

export function Tabs({ value, onValueChange, tabs, children, className = '' }: TabsProps) {
  return (
    <RadixTabs.Root value={value} onValueChange={onValueChange} className={className}>
      <RadixTabs.List className="flex border-b border-border gap-0">
        {tabs.map((tab) => (
          <RadixTabs.Trigger
            key={tab.value}
            value={tab.value}
            className={[
              'px-4 py-2.5 font-mono text-[10px] tracking-widest uppercase',
              'text-dim border-b-2 border-transparent -mb-px',
              'hover:text-ink transition-colors duration-150',
              'data-[state=active]:text-gold data-[state=active]:border-gold',
              'focus-visible:outline-none',
              'cursor-pointer',
            ].join(' ')}
          >
            § {tab.label}
          </RadixTabs.Trigger>
        ))}
      </RadixTabs.List>
      {children}
    </RadixTabs.Root>
  );
}

interface TabContentProps {
  value: string;
  children: ReactNode;
  className?: string;
}

export function TabContent({ value, children, className = '' }: TabContentProps) {
  return (
    <RadixTabs.Content
      value={value}
      className={`focus-visible:outline-none ${className}`}
    >
      {children}
    </RadixTabs.Content>
  );
}
