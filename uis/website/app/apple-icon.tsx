import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#0C4A6E",
          borderRadius: 36,
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            width: 16,
            height: 96,
            background: "#FFFFFF",
            borderRadius: 8,
          }}
        />
        <div
          style={{
            position: "absolute",
            width: 96,
            height: 16,
            background: "#FFFFFF",
            borderRadius: 8,
          }}
        />
        <div
          style={{
            position: "absolute",
            width: 132,
            height: 132,
            borderRadius: "50%",
            border: "8px solid #67E8F9",
          }}
        />
      </div>
    ),
    { ...size },
  );
}
