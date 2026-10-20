export type Proposal = {
  id: number;
  external_id: string;
  reference_code: string | null;
  slug: string;
  official_title: string;
  display_title: string;
  summary: string | null;
  category: string;
  lifecycle_status: string;
  record_kind: 'demo' | 'official';
  submitted_at: string | null;
  official_url: string | null;
  updated_at: string;
};
export type ListResponse = { data: Proposal[]; pagination: { page: number; limit: number; total: number } };
export type DetailResponse = {
  proposal: Proposal;
  versions: { id: number; version_label: string; source_checksum: string; detected_at: string; document_url: string | null }[];
  documents: { id: number; title: string; source_url: string | null; section_label: string | null; retrieved_at: string }[];
  explanation: null | {
    id: number; version_number: number; short_text: string; detailed_text: string;
    model_provider: string; model_id: string; prompt_version: string;
    generated_at: string; review_status: string;
  };
};
