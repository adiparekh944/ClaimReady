"use client";

import { useState } from "react";
import { ArrowRight } from "lucide-react";
import GlassSurface from "./GlassSurface";
interface GlassButtonProps {
  label?: string;
  onClick?: () => void;
  href?: string;
  className?: string;
}

export default function GlassButton({
  label = "Try it now",
  onClick,
  href,
  className,
}: GlassButtonProps) {
  const [isButtonHovered, setIsButtonHovered] = useState(false);

  const inner = (
    <div
      onMouseEnter={() => setIsButtonHovered(true)}
      onMouseLeave={() => setIsButtonHovered(false)}
      style={{
        display: "inline-flex",
        cursor: "pointer",
        transform: isButtonHovered
          ? "scale(1.05) translateY(-1px)"
          : "scale(1) translateY(0)",
        transition: "transform 200ms ease",
      }}
      className={className}
    >
      <GlassSurface
        width="auto"
        height="auto"
        borderRadius={9999}
        style={{
          paddingTop: "0.4rem",
          paddingBottom: "0.4rem",
          paddingLeft: "1.9rem",
          paddingRight: isButtonHovered ? "3.9rem" : "1.9rem",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
          transition: "padding 180ms ease",
        }}
      >
        <span
          style={{
            color: "#ffffff",
            fontFamily: "var(--font-geist-sans)",
            fontSize: "1rem",
            fontWeight: 600,
            letterSpacing: "-0.01em",
            lineHeight: 1,
            textShadow: "0 1px 8px rgba(0,0,0,0.25)",
          }}
        >
          {label}
        </span>

        <span
          aria-hidden="true"
          style={{
            position: "absolute",
            right: "1.45rem",
            top: "50%",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#ffffff",
            transform: isButtonHovered
              ? "translateY(-50%) translateX(0) scale(1)"
              : "translateY(-50%) translateX(-6px) scale(0.92)",
            opacity: isButtonHovered ? 1 : 0,
            transition: "opacity 180ms ease, transform 180ms ease",
            pointerEvents: "none",
          }}
        >
          <ArrowRight size={18} strokeWidth={2.2} />
        </span>
      </GlassSurface>
    </div>
  );

  if (href) {
    return (
      <a href={href} style={{ display: "inline-flex", textDecoration: "none" }}>
        {inner}
      </a>
    );
  }

  return (
    <div
      onClick={onClick}
      style={{ display: "inline-flex", pointerEvents: "auto" }}
    >
      {inner}
    </div>
  );
}