import { ReactNode } from 'react';

interface NavItem {
  icon: string;
  label: string;
  href?: string;
  active?: boolean;
}

interface TradingSidebarProps {
  items: NavItem[];
  footer?: ReactNode;
}

export function TradingSidebar({ items, footer }: TradingSidebarProps) {
  return (
    <nav className="fixed left-0 top-12 bottom-0 w-16 md:w-56 h-full border-r border-outline-variant bg-surface-dim flex flex-col z-40">
      <div className="flex-1 py-4 space-y-1 overflow-y-auto">
        {items.map((item, idx) => (
          <div
            key={idx}
            className={`flex items-center gap-3 px-4 py-3 transition-colors duration-150 cursor-pointer ${
              item.active
                ? 'border-l-2 border-primary bg-surface-container-highest text-primary font-bold'
                : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface'
            }`}
          >
            <span className="material-symbols-outlined">{item.icon}</span>
            <span className="hidden md:block font-label-caps text-label-caps">{item.label}</span>
          </div>
        ))}
      </div>
      {footer && (
        <div className="p-4 mt-auto border-t border-outline-variant">
          {footer}
        </div>
      )}
    </nav>
  );
}
