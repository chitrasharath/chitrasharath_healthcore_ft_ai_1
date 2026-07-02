export type IncidentFormValues = {
  title: string;
  description: string;
  category: string;
  origin: string;
  branch: string;
};

export type IncidentFormField = keyof IncidentFormValues;

export type IncidentFormValidationError = {
  field: IncidentFormField;
  message: string;
};

const REQUIRED_MESSAGES: Record<IncidentFormField, string> = {
  title: "Title is required.",
  description: "Description is required.",
  category: "Category is required.",
  origin: "Origin is required.",
  branch: "Branch is required.",
};

export const validateIncidentForm = (
  form: IncidentFormValues,
): IncidentFormValidationError | null => {
  const title = form.title.trim();
  if (!title) {
    return {
      field: "title",
      message: form.title.length ? "Title cannot be empty." : REQUIRED_MESSAGES.title,
    };
  }

  const description = form.description.trim();
  if (!description) {
    return {
      field: "description",
      message: form.description.length
        ? "Description cannot be empty."
        : REQUIRED_MESSAGES.description,
    };
  }

  if (!form.category.trim()) {
    return { field: "category", message: REQUIRED_MESSAGES.category };
  }

  if (!form.origin.trim()) {
    return { field: "origin", message: REQUIRED_MESSAGES.origin };
  }

  if (!form.branch.trim()) {
    return { field: "branch", message: REQUIRED_MESSAGES.branch };
  }

  return null;
};
