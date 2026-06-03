'use client';

import { useNewsStore } from '@/lib/stores/newsStore';
import { useEffect } from 'react';

const categoryColors = {
  'macro': 'bg-blue-900/50 text-blue-300',
  'geopolitical': 'bg-red-900/50 text-red-300',
  'crypto': 'bg-purple-900/50 text-purple-300',
  'central-bank': 'bg-yellow-900/50 text-yellow-300',
};

const impactColors = {
  'bullish': 'text-green-400',
  'bearish': 'text-red-400',
  'neutral': 'text-gray-400',
};

export default function NewsFeed() {
  const { news } = useNewsStore();

  return (
    <div className="w-96 bg-gray-950 border-l border-gray-800 flex flex-col">
      <div className="p-4 border-b border-gray-800">
        <h2 className="text-lg font-semibold text-white">Market News</h2>
        <p className="text-xs text-gray-500 mt-1">Real-time geopolitical & macro updates</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {news.map((item) => (
          <div key={item.id} className="bg-gray-900 rounded-lg p-3 border border-gray-800">
            <div className="flex items-start gap-2 mb-2">
              <span className={`text-xs px-2 py-1 rounded ${categoryColors[item.category]}`}>
                {item.category}
              </span>
              <span className="text-xs text-gray-500">
                {new Date(item.publishedAt).toLocaleTimeString()}
              </span>
            </div>

            <h3 className="text-sm font-medium text-white mb-2 leading-tight">
              {item.title}
            </h3>

            <p className="text-xs text-gray-400 mb-3">
              {item.description}
            </p>

            {item.aiAnalysis && (
              <div className="border-t border-gray-800 pt-3 mt-3 space-y-2">
                <div className="text-xs">
                  <span className="text-gray-500">Impact: </span>
                  <span className={`font-medium ${impactColors[item.aiAnalysis.marketImpact]}`}>
                    {item.aiAnalysis.marketImpact.toUpperCase()}
                  </span>
                </div>

                <div className="text-xs text-gray-400">
                  <span className="text-gray-500">Cause: </span>
                  {item.aiAnalysis.cause}
                </div>

                {item.aiAnalysis?.affectedAssets?.length > 0 && (
                  <div className="text-xs">
                    <span className="text-gray-500">Assets: </span>
                    <span className="text-gray-300">
                      {item.aiAnalysis.affectedAssets.join(', ')}
                    </span>
                  </div>
                )}

                <div className="text-xs text-gray-400 italic">
                  {item.aiAnalysis.institutionalPerspective}
                </div>
              </div>
            )}

            <div className="mt-3 pt-2 border-t border-gray-800">
              <p className="text-xs text-gray-600 italic">
                AI-generated analysis for educational purposes, not financial advice
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
