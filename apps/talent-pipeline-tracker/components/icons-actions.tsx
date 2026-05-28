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

export const EyeIcon = (props: IconProps) => (
  <svg {...baseProps} {...props}><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6Z" /><circle cx="12" cy="12" r="2.8" /></svg>
);

export const EditIcon = (props: IconProps) => (
  <svg {...baseProps} {...props}><path d="m14 4 6 6" /><path d="M4 20h4l11-11a2.8 2.8 0 0 0-4-4L4 16v4Z" /></svg>
);

export const NoteIcon = (props: IconProps) => (
  <svg {...baseProps} {...props}><path d="M7 17h10a3 3 0 0 0 3-3V7a3 3 0 0 0-3-3H7a3 3 0 0 0-3 3v7a3 3 0 0 0 3 3Z" /><path d="M8 21v-4" /><path d="M9 10h6" /><path d="M9 13h4" /></svg>
);

export const TrashIcon = (props: IconProps) => (
  <svg {...baseProps} {...props}><path d="M3 6h18" /><path d="M8 6V4h8v2" /><path d="M6 6l1 14h10l1-14" /></svg>
);

export const PlusIcon = (props: IconProps) => (
  <svg {...baseProps} {...props}><path d="M12 5v14" /><path d="M5 12h14" /></svg>
);

export const ExternalLinkIcon = (props: IconProps) => (
  <svg {...baseProps} {...props}><path d="M13 5h6v6" /><path d="m19 5-9 9" /><path d="M5 9v10h10" /></svg>
);

export const SaveIcon = (props: IconProps) => (
  <svg {...baseProps} {...props}><path d="M5 4h11l3 3v13H5z" /><path d="M9 4v6h6V4" /><path d="M9 20v-6h6v6" /></svg>
);