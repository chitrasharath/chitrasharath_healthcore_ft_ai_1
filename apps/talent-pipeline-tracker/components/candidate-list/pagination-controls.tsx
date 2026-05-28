import { ChevronLeftIcon, ChevronRightIcon } from "@/components/icons";

type PaginationControlsProps = {
  page: number;
  totalPages: number;
  onPageChange: (nextPage: number) => void;
};

export const PaginationControls = ({
  page,
  totalPages,
  onPageChange,
}: PaginationControlsProps) => {
  return (
    <div className="flex items-center justify-between border-t border-[var(--hc-border)] px-4 py-3 text-sm">
      <span>
        Page {page} of {totalPages}
      </span>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="inline-flex items-center gap-1 rounded-md border border-[var(--hc-border)] px-3 py-1 disabled:opacity-50"
        >
          <ChevronLeftIcon className="h-4 w-4" />
          Prev
        </button>
        <button
          type="button"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          className="inline-flex items-center gap-1 rounded-md border border-[var(--hc-border)] px-3 py-1 disabled:opacity-50"
        >
          Next
          <ChevronRightIcon className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
};
