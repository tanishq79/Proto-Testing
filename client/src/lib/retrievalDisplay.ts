export type SearchResult = {
  rank: number;
  part_id: string;
  similarity: number;
  similarity_percentage: number;
  best_view: string;
  preview_image: string;
  available_views: Array<{ view: string; image_url: string }>;
  metadata: Record<string, string | number | boolean | null>;
};

export function formatSimilarity(score: number) {
  return `${score.toFixed(1)}%`;
}

export function getDisplayName(result: SearchResult) {
  const title = result.metadata.part_title || result.metadata.design || result.metadata.reference;
  return typeof title === "string" && title.trim() ? title : result.part_id;
}

export function metadataEntries(result: SearchResult) {
  const labels: Record<string, string> = {
    reference: "Reference",
    part_number: "Part number",
    supplier: "Supplier",
    material: "Material",
    part_title: "Part title",
    design: "Design",
    weight: "Weight",
    eclass: "Classification",
    rohs: "RoHS",
  };
  return Object.entries(result.metadata)
    .filter(([, value]) => value !== null && value !== "")
    .map(([key, value]) => ({ key, label: labels[key] || key.replace(/_/g, " "), value: String(value) }));
}
