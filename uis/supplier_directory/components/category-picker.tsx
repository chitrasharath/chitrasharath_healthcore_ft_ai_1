import { CATEGORY_LABELS, VALID_CATEGORIES } from "@/lib/categories";

type CategoryPickerProps = {
  selected: string[];
  onToggle: (category: string) => void;
};

export const CategoryPicker = ({ selected, onToggle }: CategoryPickerProps) => (
  <fieldset className="text-sm">
    <legend className="mb-2 font-medium text-slate-700">Categories</legend>
    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {VALID_CATEGORIES.map((category) => (
        <label key={category} className="flex items-center gap-2 text-slate-700">
          <input
            type="checkbox"
            checked={selected.includes(category)}
            onChange={() => onToggle(category)}
          />
          {CATEGORY_LABELS[category]}
        </label>
      ))}
    </div>
  </fieldset>
);
