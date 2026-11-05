import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export async function GET() {
  const reportsDir = path.resolve(process.cwd(), "../api/reports");

  function readReport(filename: string) {
    const filePath = path.join(reportsDir, filename);
    if (fs.existsSync(filePath)) {
      try {
        const raw = fs.readFileSync(filePath, "utf-8");
        return JSON.parse(raw);
      } catch {
        return {};
      }
    }
    return {};
  }

  const booking = readReport("booking_results.json");
  const dispatch = readReport("dispatch_results.json");
  const collection = readReport("collection_results.json");
  const extractorComparison = readReport("extractor_comparison.json");
  const audioEval = readReport("audio_eval.json");
  const holdoutV2 = readReport("holdout_v2_results.json");

  return NextResponse.json({
    status: "ok",
    generated_at: new Date().toISOString(),
    booking,
    dispatch,
    collection,
    extractor_comparison: extractorComparison,
    audio_eval: audioEval,
    holdout_v2: holdoutV2,
  });
}
