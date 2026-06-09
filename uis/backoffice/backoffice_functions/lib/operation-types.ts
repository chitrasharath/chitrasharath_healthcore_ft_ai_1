export interface OperationResult {
  label: string;
  value: unknown;
}

export type ParamInputType = "text" | "number" | "date" | "select" | "multiselect";
export type RawParamValue = string | string[];

export interface ParamOption {
  label: string;
  value: string;
}

export interface ParameterDefinition {
  key: string;
  label: string;
  type: ParamInputType;
  options?: ParamOption[];
  placeholder?: string;
  defaultValue?: string | string[];
}

export interface OperationDefinition {
  id: string;
  label: string;
  description: string;
  params: ParameterDefinition[];
  run: (params: Record<string, RawParamValue>) => unknown;
}
