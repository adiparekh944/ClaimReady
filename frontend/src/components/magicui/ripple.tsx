import React, { ComponentPropsWithoutRef, CSSProperties, useEffect, useState } from "react";

import { cn } from "@/lib/utils";

interface RippleProps extends ComponentPropsWithoutRef<"div"> {
  mainCircleSize?: number;
  mainCircleOpacity?: number;
  numCircles?: number;
  /** seconds between bob triggers of the main circle */
  bobIntervalSec?: number;
  /** how long the main circle stays lifted (ms) */
  bobLiftMs?: number;
  /** base delay (in seconds) before ripples start after the bob */
  rippleBaseDelaySec?: number;
}

export const Ripple = React.memo(function Ripple({
  mainCircleSize = 310,
  mainCircleOpacity = .8,
  numCircles = 20,
  className,
  bobIntervalSec = 10,
  bobLiftMs = 600,
  rippleBaseDelaySec = 0.6,
  ...props
}: RippleProps) {
  const [bobKey, setBobKey] = useState(0);
  const [lifted, setLifted] = useState(false);

  useEffect(() => {
    // trigger a lift every bobIntervalSec seconds
    const interval = setInterval(() => {
      setLifted(true);
      // drop back down after bobLiftMs
      const t = setTimeout(() => setLifted(false), bobLiftMs);
      // bump a key so CSS animations (if any) can restart on other rings if needed later
      setBobKey(k => k + 1);
      return () => clearTimeout(t);
    }, bobIntervalSec * 1000);

    return () => clearInterval(interval);
  }, [bobIntervalSec, bobLiftMs]);

  return (
    <div
      className={cn(
        "pointer-events-none absolute inset-0 select-none [mask-image:linear-gradient(to_bottom,white,transparent)]",
        className,
      )}
      {...props}
    >
      {Array.from({ length: numCircles }, (_, i) => {
        const size = mainCircleSize + i * 110;
        const opacity = mainCircleOpacity - i * 0.04;
        // Stagger the ripple rings to start after the bob; the main circle won't use this
        const animationDelay = `${(rippleBaseDelaySec + i * 0.06).toFixed(2)}s`;
        const borderStyle = "solid";

        const baseStyle: CSSProperties = {
          "--i": i as unknown as number,
          width: `${size}px`,
          height: `${size}px`,
          opacity,
          borderStyle,
          borderWidth: "1px",
          borderColor: `var(--foreground)`,
          top: "50%",
          left: "50%",
          transform: `translate(-50%, -50%) scale(1)`,
        };

        if (i === 0) {
          // MAIN CIRCLE: bob only, no ripple animation
          return (
            <div
              key={`main-${bobKey}`}
              className={`absolute rounded-full border bg-foreground/25 shadow-xl`}
              style={{
                ...baseStyle,
                transition: "transform 600ms ease-in-out",
                transform: `translate(-50%, -50%) translateY(${lifted ? "-10px" : "0px"}) scale(1)`,
              }}
            />
          );
        }

        // RIPPLE RINGS: keep existing ripple animation and stagger after the bob
        return (
          <div
            key={i}
            className={`absolute animate-ripple rounded-full border bg-foreground/25 shadow-xl`}
            style={{
              ...baseStyle,
              animationDelay,
            }}
          />
        );
      })}
    </div>
  );
});

Ripple.displayName = "Ripple";
