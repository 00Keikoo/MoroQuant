import { NextRequest, NextResponse } from 'next/server';

const CLAUDE_API_URL = 'http://127.0.0.1:8085/v1/chat/completions';
const MODEL = 'claude-sonnet-4.5';
const API_KEY = process.env.CLAUDE_API_KEY || '';

export async function POST(request: NextRequest) {
  try {
    const { pairs, news } = await request.json();

    const marketSummary = pairs.slice(0, 10).map((p: any) =>
      `${p.symbol}: $${p.price.toFixed(2)} (${p.change24h > 0 ? '+' : ''}${p.change24h.toFixed(2)}%)`
    ).join('\n');

    const newsSummary = news.slice(0, 5).map((n: any) =>
      `- ${n.title} [${n.category}]`
    ).join('\n');

    const prompt = `You are a senior trader at Goldman Sachs writing the morning market brief. Analyze current market conditions:

MARKET DATA:
${marketSummary}

RECENT NEWS:
${newsSummary}

Provide institutional-grade analysis in the following JSON format:
{
  "sentiment": "risk-on" | "risk-off" | "neutral",
  "keyLevels": {
    "BTCUSDT": {"support": [65000, 63500], "resistance": [69000, 71000]},
    "ETHUSDT": {"support": [3100, 3000], "resistance": [3300, 3450]}
  },
  "bias": {
    "BTCUSDT": "long" | "short" | "neutral",
    "ETHUSDT": "long" | "short" | "neutral"
  },
  "riskFactors": ["list", "of", "key", "risks"],
  "summary": "2-3 paragraph institutional perspective on market conditions, confluence of technicals and fundamentals, and positioning recommendations"
}

Write in the style of a professional trading desk brief. Be specific about levels and actionable.`;

    const response = await fetch(CLAUDE_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${API_KEY}`,
      },
      body: JSON.stringify({
        model: MODEL,
        messages: [{ role: 'user', content: prompt }],
        max_tokens: 2000,
        temperature: 0.7,
      }),
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`);
    }

    const data = await response.json();
    const content = data.choices[0]?.message?.content || '';

    const jsonMatch = content.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      try {
        const analysis = JSON.parse(jsonMatch[0]);
        return NextResponse.json({
          ...analysis,
          timestamp: Date.now(),
        });
      } catch (parseError) {
        console.error('JSON parse error:', parseError);
        console.error('Raw content:', content);
      }
    }

    return NextResponse.json({
      sentiment: 'neutral',
      keyLevels: {},
      bias: {},
      riskFactors: ['Analysis unavailable'],
      summary: 'Unable to generate market analysis at this time. Please check API connection.',
      timestamp: Date.now(),
    });
  } catch (error) {
    console.error('Error generating market analysis:', error);
    return NextResponse.json(
      {
        sentiment: 'neutral',
        keyLevels: {},
        bias: {},
        riskFactors: ['Analysis unavailable'],
        summary: 'Unable to generate market analysis at this time. Please check API connection.',
        timestamp: Date.now(),
      },
      { status: 500 }
    );
  }
}
