import { describe, expect, it } from "vitest";
import { formatSimilarity, getDisplayName, metadataEntries, type SearchResult } from "./retrievalDisplay";

const record: SearchResult = {
  rank: 1,
  part_id: "part-001",
  similarity: 0.9284,
  similarity_percentage: 92.8,
  best_view: "iso",
  preview_image: "/cad/part-001.png",
  available_views: [],
  metadata: { part_title: "Precision mounting bracket", material: null, supplier: "Acme" },
};

describe("retrieval display helpers", () => {
  it("formats actual API percentages without inventing values", () => {
    expect(formatSimilarity(record.similarity_percentage)).toBe("92.8%");
  });

  it("uses real preferred metadata and omits unavailable fields", () => {
    expect(getDisplayName(record)).toBe("Precision mounting bracket");
    expect(metadataEntries(record)).toEqual([
      { key: "part_title", label: "Part title", value: "Precision mounting bracket" },
      { key: "supplier", label: "Supplier", value: "Acme" },
    ]);
  });
});
