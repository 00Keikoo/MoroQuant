import { NextRequest, NextResponse } from 'next/server';

const CLAUDE_API_URL = 'http://127.0.0.1:8085/v1/chat/completions';
const MODEL = 'claude-sonnet-4.5';
const API_KEY = process.env.CLAUDE_API_KEY || '';

function sanitizeAffectedAssets(jsonString: string): string {
  // Extract affectedAssets array and rebuild it properly
  const assetsMatch = jsonString.match(/"affectedA[ss]ets"\s*:\s*\[(.*?)\]/s);

  if (assetsMatch) {
    const arrayContent = assetsMatch[1];
    // Split by comma and clean each item
    const items = arrayContent.split(',').map(item => {
      // Remove all quotes and whitespace, then get the clean value
      const cleaned = item.replace(/["'\s]/g, '');
      return cleaned;
    }).filter(item => item.length > 0);

    // Rebuild as valid JSON array
    const validArray = '["' + items.join('", "') + '"]';
    jsonString = jsonString.replace(assetsMatch[0], `"affectedAssets": ${validArray}`);
  }

  // Fix typo: affectedAsets -> affectedAssets
  jsonString = jsonString.replace(/"affectedAsets"/g, '"affectedAssets"');

  return jsonString;
}

function sanitizeJSON(jsonString: string): string {
  // Fix affectedAssets array issues first
  jsonString = sanitizeAffectedAssets(jsonString);

  // Fix missing commas between quoted strings in arrays: "word" "word" -> "word", "word"
  jsonString = jsonString.replace(/("\s+)(")/g, '", "');

  return jsonString;
}

function extractFieldsWithRegex(content: string) {
  try {
    const causeMatch = content.match(/"cause"\s*:\s*"([^"]*(?:\\.[^"]*)*)"/);
    const impactMatch = content.match(/"marketImpact"\s*:\s*"(bullish|bearish|neutral)"/i);
    const assetsMatch = content.match(/"affectedAssets"\s*:\s*\[[\s\S]*?\]/);
    const perspectiveMatch = content.match(/"institutionalPerspective"\s*:\s*"([^"]*(?:\\.[^"]*)*)"/);

    if (causeMatch || impactMatch || assetsMatch || perspectiveMatch) {
      let assets: string[] = [];
      if (assetsMatch) {
        const assetsStr = assetsMatch[0];
        const assetMatches = assetsStr.match(/"([^"]+)"/g);
        if (assetMatches) {
          assets = assetMatches.map(m => m.replace(/"/g, ''));
        }
      }

      return {
        cause: causeMatch ? causeMatch[1].replace(/\\"/g, '"') : 'Analysis unavailable',
        marketImpact: (impactMatch ? impactMatch[1].toLowerCase() : 'neutral') as 'bullish' | 'bearish' | 'neutral',
        affectedAssets: assets,
        institutionalPerspective: perspectiveMatch ? perspectiveMatch[1].replace(/\\"/g, '"') : 'Unable to parse response',
      };
    }
  } catch (error) {
    console.error('Regex extraction error:', error);
  }

  return null;
}

export async function POST(request: NextRequest) {
  try {
    const { newsItem } = await request.json();

    const prompt = `Analyze this news item from an institutional trader's perspective:

Title: ${newsItem.title}
Description: ${newsItem.description}

Provide a concise analysis in the following JSON format:
{
  "cause": "Brief explanation of what caused this event (1-2 sentences)",
  "marketImpact": "bullish" | "bearish" | "neutral",
  "affectedAssets": ["asset1", "asset2", "asset3"],
  "institutionalPerspective": "How institutional traders view this (2-3 sentences)"
}

CRITICAL: In the affectedAssets array, each item must be a separate string with proper quotes. Never put two items in the same string.

Example of WRONG format:
["USD "Gold", "Oil"]
["Oil", "Gold", "USD "Defense Stocks"]

Example of CORRECT format:
["USD", "Gold", "Oil"]
["Oil", "Gold", "USD", "Defense Stocks"]

Respond with ONLY valid JSON, no markdown code blocks, no backticks, no extra text. Be direct and actionable. Focus on tradeable insights.`;

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
        // First attempt: parse as-is
        const analysis = JSON.parse(jsonMatch[0]);
        return NextResponse.json(analysis);
      } catch (parseError) {
        console.error('JSON parse error:', parseError);
        console.error('Raw content:', content);

        // Second attempt: sanitize and retry
        try {
          const sanitized = sanitizeJSON(jsonMatch[0]);
          const analysis = JSON.parse(sanitized);
          return NextResponse.json(analysis);
        } catch (sanitizeError) {
          console.error('Sanitized parse failed:', sanitizeError);

          // Third attempt: regex extraction
          const fallback = extractFieldsWithRegex(content);
          if (fallback) {
            return NextResponse.json(fallback);
          }
        }
      }
    }

    return NextResponse.json({
      cause: 'Analysis unavailable',
      marketImpact: 'neutral',
      affectedAssets: [],
      institutionalPerspective: 'Unable to parse response',
    });
  } catch (error) {
    console.error('Error generating news analysis:', error);
    return NextResponse.json(
      {
        cause: 'Analysis error',
        marketImpact: 'neutral',
        affectedAssets: [],
        institutionalPerspective: 'Error generating analysis.',
      },
      { status: 500 }
    );
  }
}
