import React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, VariantProps } from "class-variance-authority"
import { ArrowRight } from "lucide-react"

import { cn } from "@/lib/utils"

const rainbowButtonVariants = cva(
  cn(
    "relative cursor-pointer group transition-all animate-rainbow",
    // Removed gap-2 so we can tightly control the arrow spacing manually
    "inline-flex items-center justify-center shrink-0",
    "rounded-sm outline-none focus-visible:ring-[3px] aria-invalid:border-destructive",
    "font-medium whitespace-nowrap font-[family-name:var(--font-geist-sans)]",
    "disabled:pointer-events-none disabled:opacity-50",
    "[&_svg]:pointer-events-none [&_svg]:shrink-0"
  ),
  {
    variants: {
      variant: {
        default:
          "border-0 bg-[linear-gradient(#ffffff,#ffffff),linear-gradient(#121213_50%,rgba(18,18,19,0.6)_80%,rgba(18,18,19,0)),linear-gradient(90deg,#93c5fd,#3b82f6,#2563eb,#1d4ed8,#60a5fa)] bg-[length:200%] text-black [background-clip:padding-box,border-box,border-box] [background-origin:border-box] [border:calc(0.125rem)_solid_transparent] before:absolute before:bottom-[-20%] before:left-1/2 before:z-0 before:h-2/5 before:w-4/5 before:-translate-x-1/2 before:animate-rainbow before:bg-[linear-gradient(90deg,#93c5fd,#3b82f6,#2563eb,#1d4ed8,#60a5fa)] before:[filter:blur(0.75rem)] before:opacity-100 dark:bg-[linear-gradient(#fff,#fff),linear-gradient(#fff_50%,rgba(255,255,255,0.6)_80%,rgba(0,0,0,0)),linear-gradient(90deg,#93c5fd,#3b82f6,#2563eb,#1d4ed8,#60a5fa)]",
        outline:
          "border border-input border-b-transparent bg-[linear-gradient(#ffffff,#ffffff),linear-gradient(#ffffff_50%,rgba(18,18,19,0.6)_80%,rgba(18,18,19,0)),linear-gradient(90deg,#93c5fd,#3b82f6,#2563eb,#1d4ed8,#60a5fa)] bg-[length:200%] text-accent-foreground [background-clip:padding-box,border-box,border-box] [background-origin:border-box] before:absolute before:bottom-[-20%] before:left-1/2 before:z-0 before:h-2/5 before:w-4/5 before:-translate-x-1/2 before:animate-rainbow before:bg-[linear-gradient(90deg,#93c5fd,#3b82f6,#2563eb,#1d4ed8,#60a5fa)] before:[filter:blur(0.75rem)] before:opacity-100 dark:bg-[linear-gradient(#0a0a0a,#0a0a0a),linear-gradient(#0a0a0a_50%,rgba(255,255,255,0.6)_80%,rgba(0,0,0,0)),linear-gradient(90deg,#93c5fd,#3b82f6,#2563eb,#1d4ed8,#60a5fa)]",
      },
      size: {
        // Increased sizes across the board
        default: "h-12 px-8 py-3 text-base",
        sm: "h-10 rounded-xl px-4 text-sm",
        lg: "h-14 rounded-xl px-10 text-lg",
        icon: "size-12",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

interface RainbowButtonProps
  extends
    React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof rainbowButtonVariants> {
  asChild?: boolean
}

const RainbowButton = React.forwardRef<HTMLButtonElement, RainbowButtonProps>(
  ({ className, variant, size, asChild = false, children, ...props }, ref) => {
    
    // Radix Slot bypasses the standard button render
    if (asChild) {
      return (
        <Slot
          data-slot="button"
          className={cn(rainbowButtonVariants({ variant, size, className }))}
          ref={ref}
          {...props}
        >
          {children}
        </Slot>
      )
    }

    // Standard Render with embedded hover arrow
    return (
      <button
        data-slot="button"
        className={cn(rainbowButtonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      >
        <span className="flex items-center justify-center transition-transform duration-300 ease-out group-hover:-translate-x-1">
          {children}
        </span>
        <ArrowRight
          strokeWidth={2.5}
          className="w-0 -translate-x-2 opacity-0 transition-all duration-300 ease-out group-hover:w-5 group-hover:translate-x-0 group-hover:opacity-100 group-hover:ml-2"
        />
      </button>
    )
  }
)

RainbowButton.displayName = "RainbowButton"

export { RainbowButton, rainbowButtonVariants, type RainbowButtonProps }