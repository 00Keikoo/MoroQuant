import React from 'react';

interface TrendIndicatorProps {
  value: number;
  format?: 'percent' | 'dollar' | 'raw';
  inverse?: boolean;
}

export default function TrendIndicator({ value, format = 'percent', inverse = false }: TrendIndicatorProps) {
  const isZero = value === 0;
  const isPositive = value > 0;
  
  // Determine if this change is "good" or "bad"
  const isGood = inverse ? !isPositive : isPositive;

  let colorClass = 'text-neutral-400';
  let arrow = '■';

  if (!isZero) {
    if (isGood) {
      colorClass = 'text-mq-long';
      arrow = '▲';
    } else {
      colorClass = 'text-mq-short';
      arrow = '▼';
    }
  }

  const formatValue = (val: number) => {
    const absVal = Math.abs(val);
    switch (format) {
      case 'percent':
        return `${absVal.toFixed(2)}%`;
      case 'dollar':
        return `$${absVal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
      case 'raw':
      default:
        return absVal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
  };

  return (
    <span className={`inline-flex items-center gap-1 text-xs font-mono font-semibold ${colorClass}`}>
      <span className="text-[10px] leading-none">{arrow}</span>
      <span>{formatValue(value)}</span>
    </span>
  );
}
