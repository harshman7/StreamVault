#!/bin/bash
# Usage: ./transcode.sh input.mp4 output_dir content_id
set -euo pipefail

INPUT="${1:?Usage: transcode.sh input.mp4 output_dir content_id}"
OUTPUT_DIR="${2:?output_dir required}"
CONTENT_ID="${3:?content_id required}"

mkdir -p "$OUTPUT_DIR"

openssl rand 16 > "$OUTPUT_DIR/enc.key"
KEY_HEX=$(xxd -p -c 256 "$OUTPUT_DIR/enc.key" | tr -d '\n')
IV_HEX=$(openssl rand -hex 16)

# Key URI must be reachable by the player (browser)
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
echo "${BACKEND_URL}/drm/key/${CONTENT_ID}" > "$OUTPUT_DIR/enc.keyinfo"
echo "$OUTPUT_DIR/enc.key" >> "$OUTPUT_DIR/enc.keyinfo"
echo "$IV_HEX" >> "$OUTPUT_DIR/enc.keyinfo"

ffmpeg -y -i "$INPUT" \
  -filter_complex "[0:v]split=3[v1][v2][v3];[0:a]asplit=3[a1][a2][a3]" \
  -map "[v1]" -map "[a1]" -c:v libx264 -b:v 5000k -maxrate 5000k -bufsize 10000k -s 1920x1080 \
    -c:a aac -b:a 192k \
    -hls_time 6 -hls_playlist_type vod -hls_key_info_file "$OUTPUT_DIR/enc.keyinfo" \
    -hls_segment_filename "$OUTPUT_DIR/1080p_%03d.ts" \
    "$OUTPUT_DIR/1080p.m3u8" \
  -map "[v2]" -map "[a2]" -c:v libx264 -b:v 3000k -maxrate 3000k -bufsize 6000k -s 1280x720 \
    -c:a aac -b:a 128k \
    -hls_time 6 -hls_playlist_type vod -hls_key_info_file "$OUTPUT_DIR/enc.keyinfo" \
    -hls_segment_filename "$OUTPUT_DIR/720p_%03d.ts" \
    "$OUTPUT_DIR/720p.m3u8" \
  -map "[v3]" -map "[a3]" -c:v libx264 -b:v 1500k -maxrate 1500k -bufsize 3000k -s 854x480 \
    -c:a aac -b:a 96k \
    -hls_time 6 -hls_playlist_type vod -hls_key_info_file "$OUTPUT_DIR/enc.keyinfo" \
    -hls_segment_filename "$OUTPUT_DIR/480p_%03d.ts" \
    "$OUTPUT_DIR/480p.m3u8"

cat > "$OUTPUT_DIR/master.m3u8" << EOF
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=5000000,RESOLUTION=1920x1080
1080p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=3000000,RESOLUTION=1280x720
720p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=1500000,RESOLUTION=854x480
480p.m3u8
EOF

printf '{"content_id":"%s","key_hex":"%s","iv_hex":"%s"}\n' "$CONTENT_ID" "$KEY_HEX" "$IV_HEX" > "$OUTPUT_DIR/streamvault_meta.json"

echo "✅ Done. Key hex: $KEY_HEX | IV hex: $IV_HEX"
echo "👉 Metadata: $OUTPUT_DIR/streamvault_meta.json"
echo "👉 Register drm_key + DB rows, then upload with segment_uploader.py"
