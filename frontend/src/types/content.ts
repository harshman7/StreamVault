export interface Rendition {
  id: string;
  resolution: string;
  bitrate_kbps: number;
  s3_manifest_key: string;
  created_at?: string | null;
}

export interface ContentItem {
  id: string;
  title: string;
  description?: string | null;
  thumbnail_url?: string | null;
  duration_seconds?: number | null;
  created_at?: string | null;
  renditions: Rendition[];
}

export interface ContentListResponse {
  items: ContentItem[];
}
