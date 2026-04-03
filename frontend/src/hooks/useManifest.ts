import { useMemo } from "react";
import { getBackendOrigin } from "../api/client";

/**
 * Absolute URL for the HLS master manifest served by the StreamVault API.
 */
export function useManifestUrl(contentId: string | undefined): string | null {
  return useMemo(() => {
    if (!contentId) return null;
    const base = getBackendOrigin();
    return `${base}/manifest/${contentId}`;
  }, [contentId]);
}
