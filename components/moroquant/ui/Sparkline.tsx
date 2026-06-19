import React from 'react';

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
}

export default function Sparkline({ data, width = 100, height = 30, color }: SparklineProps) {
  if (!data || data.length < 2) {
    return <div className="h-6 w-20 flex items-center justify-center text-xs text-neutral-600">—</div>;
  }

  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;

  // Generate SVG path coordinates
  const points = data.map((val, idx) => {
    const x = (idx / (data.length - 1)) * width;
    // In SVG, y=0 is at the top, so we subtract scaled value from height
    const y = height - ((val - min) / range) * (height - 4) - 2; // leave 2px padding top/bottom
    return { x, y };
  });

  const pathD = `M ${points.map(p => `${p.x} ${p.y}`).join(' L ')}`;
  const areaD = `${pathD} L ${width} ${height} L 0 ${height} Z`;

  // Auto-detect color if not specified
  const isPositive = data[data.length - 1] >= data[0];
  const strokeColor = color || (isPositive ? '#00ff87' : '#ff0055');
  const gradientId = `sparkline-grad-${Math.random().toString(36).substr(2, 9)}`;

  return (
    <svg width={width} height={height} className="overflow-visible">
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={strokeColor} stopOpacity="0.2" />
          <stop offset="100%" stopColor={strokeColor} stopOpacity="0.0" />
        </linearGradient>
      </defs>
      
      {/* Filled Area */}
      <path
        d={areaD}
        fill={`url(#${gradientId})`}
        stroke="none"
      />
      
      {/* Stroke Line */}
      <path
        d={pathD}
        fill="none"
        stroke={strokeColor}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Endpoint dot */}
      {points.length > 0 && (
        <circle
          cx={points[points.length - 1].x}
          cy={points[points.length - 1].y}
          r="2.5"
          fill={strokeColor}
          stroke="#000000"
          strokeWidth="1"
        />
      )}
    </svg>
  );
}
