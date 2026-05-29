import type { OperationDefinition, RawParamValue } from "@/lib/operation-types";

import { ParamField } from "./param-field";

type ParamControlsProps = {
  operation: OperationDefinition;
  values: Record<string, RawParamValue>;
  onChange: (key: string, value: RawParamValue) => void;
};

export function ParamControls({ operation, values, onChange }: ParamControlsProps) {
  if (operation.params.length === 0) {
    return (
      <p className="mt-4 text-sm text-slate-600">
        This function uses only the sample data and has no configurable parameters.
      </p>
    );
  }

  return (
    <div className="mt-4 grid gap-3 md:grid-cols-2">
      {operation.params.map((param) => (
        <ParamField
          key={param.key}
          operationId={operation.id}
          param={param}
          value={values[param.key]}
          onChange={onChange}
        />
      ))}
    </div>
  );
}
