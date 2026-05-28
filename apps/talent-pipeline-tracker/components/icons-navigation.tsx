import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

const baseProps = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
} as const;

export const ArrowLeftIcon = (props: IconProps) => (
  <svg {...baseProps} {...props}><path d="m11 5-7 7 7 7" /><path d="M4 12h16" /></svg>
);

export const ChevronLeftIcon = (props: IconProps) => (
  <svg {...baseProps} {...props}><path d="m15 18-6-6 6-6" /></svg>
);

export const ChevronRightIcon = (props: IconProps) => (
  <svg {...baseProps} {...props}><path d="m9 6 6 6-6 6" /></svg>
);

export const MenuIcon = (props: IconProps) => (
  <svg {...baseProps} {...props}><path d="M4 7h16" /><path d="M4 12h16" /><path d="M4 17h16" /></svg>
);