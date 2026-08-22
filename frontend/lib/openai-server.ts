import OpenAI from "openai";
import type { AiSummaryPayload } from "@/lib/ai";

const MODEL = process.env.OPENAI_MODEL || "gpt-4o-mini";

function getClient() {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error("Missing OPENAI_API_KEY");
  }
  return new OpenAI({ apiKey });
}

const SHARED_RULES = `
You are a botanical guide for PlantDex.

Rules:
- Write a useful plain-text overview from the provided plant/search payload and careful botanical knowledge.
- Prefer scientific names for botanical identity; common names are vernacular aliases.
- Be concise and practical. No marketing copy. No invented hardiness zones or toxicity numbers.
- Do not include URLs, citations, source lists, or video links.
- Return ONLY valid JSON: { "summary": "2-4 short paragraphs as plain text" }
`.trim();

function extractJsonObject(text: string): unknown {
  const trimmed = text.trim();
  try {
    return JSON.parse(trimmed);
  } catch {
    const start = trimmed.indexOf("{");
    const end = trimmed.lastIndexOf("}");
    if (start >= 0 && end > start) {
      return JSON.parse(trimmed.slice(start, end + 1));
    }
    throw new Error("Model did not return JSON");
  }
}

function parseSummary(raw: unknown): string {
  const obj = (raw && typeof raw === "object" ? raw : {}) as Record<
    string,
    unknown
  >;
  if (typeof obj.summary === "string" && obj.summary.trim()) {
    return obj.summary.trim();
  }
  return "No summary available.";
}

async function completeSummary(system: string, user: string): Promise<string> {
  const client = getClient();

  try {
    const response = await client.responses.create({
      model: MODEL,
      temperature: 0.3,
      input: [
        { role: "system", content: [{ type: "input_text", text: system }] },
        { role: "user", content: [{ type: "input_text", text: user }] },
      ],
    });
    const text = response.output_text?.trim();
    if (text) return parseSummary(extractJsonObject(text));
  } catch {
    // fall through
  }

  const chat = await client.chat.completions.create({
    model: MODEL,
    temperature: 0.3,
    response_format: { type: "json_object" },
    messages: [
      { role: "system", content: system },
      { role: "user", content: user },
    ],
  });

  const content = chat.choices[0]?.message?.content;
  if (!content) throw new Error("Empty model response");
  return parseSummary(extractJsonObject(content));
}

function asPayload(summary: string): AiSummaryPayload {
  return {
    summary,
    highlights: [],
    sources: [],
    tasting_video: null,
    model: MODEL,
  };
}

export async function summarizeSearchResults(input: {
  query: string;
  results: unknown[];
}): Promise<AiSummaryPayload> {
  const system = `${SHARED_RULES}

Task: Summarize this PlantDex search result set for query "${input.query}".
Call out shared taxonomy, traits, and ranges across the hits.`;

  const summary = await completeSummary(
    system,
    JSON.stringify(
      {
        query: input.query,
        result_count: input.results.length,
        results: input.results,
      },
      null,
      2
    )
  );

  return asPayload(summary);
}

export async function summarizePlantProfile(input: {
  plant: unknown;
}): Promise<AiSummaryPayload> {
  const plant = input.plant as Record<string, unknown>;
  const scientific =
    typeof plant.scientific_name === "string" && plant.scientific_name.trim()
      ? plant.scientific_name.trim()
      : null;
  const common =
    typeof plant.common_name === "string" && plant.common_name.trim()
      ? plant.common_name.trim()
      : null;
  const lookupName = scientific || common || "this plant";

  const system = `${SHARED_RULES}

Task: Write a short AI overview for ${lookupName}.
Use scientific name for botanical identity${scientific ? ` ("${scientific}")` : ""}.
Common name${common ? ` ("${common}")` : ""} is vernacular only.`;

  const summary = await completeSummary(
    system,
    JSON.stringify(
      {
        lookup_scientific_name: scientific,
        vernacular_common_name: common,
        plant: input.plant,
      },
      null,
      2
    )
  );

  return asPayload(summary);
}
