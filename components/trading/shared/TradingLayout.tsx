import { ReactNode } from 'react';

interface TradingLayoutProps {
  topBar: ReactNode;
  sidebar: ReactNode;
  children: ReactNode;
}

export function TradingLayout({ topBar, sidebar, children }: TradingLayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {topBar}
      {sidebar}
      <main className="ml-16 md:ml-56 mt-12 flex-1 flex flex-col overflow-hidden bg-background">
        {children}
      </main>
    </div>
  );
}
