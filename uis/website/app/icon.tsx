import { ImageResponse } from "next/og";

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

export default function Icon() {
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
          borderRadius: 8,
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            width: 4,
            height: 20,
            background: "#FFFFFF",
            borderRadius: 2,
          }}
        />
        <div
          style={{
            position: "absolute",
            width: 20,
            height: 4,
            background: "#FFFFFF",
            borderRadius: 2,
          }}
        />
        <div
          style={{
            position: "absolute",
            width: 28,
            height: 28,
            borderRadius: "50%",
            border: "2px solid #67E8F9",
          }}
        />
      </div>
    ),
    { ...size },
  );
}
