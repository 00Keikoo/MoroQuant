'use client';

import { useAnalysisStore } from '@/lib/stores/analysisStore';

const sentimentColors = {
  'risk-on': 'text-green-400',
  'risk-off': 'text-red-400',
  'neutral': 'text-gray-400',
};

const biasColors = {
  'long': 'text-green-400',
  'short': 'text-red-400',
  'neutral': 'text-gray-400',
};

export default function MarketAnalysis() {
  const { analysis, loading } = useAnalysisStore();

  if (loading) {
    return (
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-gray-800 rounded w-3/4"></div>
          <div className="h-4 bg-gray-800 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
        <p className="text-gray-500 text-sm">Loading market analysis...</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 rounded-lg p-4 border border-gray-800 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">Institutional Analysis</h3>
        <div className="text-xs text-gray-500">
          {new Date(analysis.timestamp).toLocaleTimeString()}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <span className="text-xs text-gray-500">Market Sentiment</span>
          <div className={`text-lg font-semibold ${sentimentColors[analysis.sentiment]}`}>
            {analysis.sentiment.toUpperCase()}
          </div>
        </div>
      </div>

      {Object.keys(analysis.bias).length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-400 mb-2">Trading Bias</h4>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(analysis.bias).map(([symbol, bias]) => (
              <div key={symbol} className="flex items-center justify-between bg-gray-950 px-3 py-2 rounded">
                <span className="text-sm text-gray-300">{symbol}</span>
                <span className={`text-sm font-medium ${biasColors[bias]}`}>
                  {bias.toUpperCase()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {Object.keys(analysis.keyLevels).length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-400 mb-2">Key Levels</h4>
          <div className="space-y-2">
            {Object.entries(analysis.keyLevels).map(([symbol, levels]) => (
              <div key={symbol} className="bg-gray-950 px-3 py-2 rounded">
                <div className="text-sm text-gray-300 mb-1">{symbol}</div>
                <div className="flex gap-4 text-xs">
                  <div>
                    <span className="text-gray-500">Support: </span>
                    <span className="text-green-400">{levels.support.join(', ')}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Resistance: </span>
                    <span className="text-red-400">{levels.resistance.join(', ')}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {analysis.riskFactors.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-400 mb-2">Risk Factors</h4>
          <ul className="space-y-1">
            {analysis.riskFactors.map((risk, idx) => (
              <li key={idx} className="text-sm text-gray-300 flex items-start gap-2">
                <span className="text-yellow-500">⚠</span>
                <span>{risk}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <h4 className="text-sm font-medium text-gray-400 mb-2">Summary</h4>
        <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-line">
          {analysis.summary}
        </p>
      </div>

      <div className="pt-3 border-t border-gray-800">
        <p className="text-xs text-gray-600 italic">
          This is AI-generated analysis for educational purposes, not financial advice
        </p>
      </div>
    </div>
  );
}
