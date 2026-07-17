type Props = {
  columns: string[];
  rows: Array<Record<string, string | number>>;
  emptyMessage?: string;
};

export const KpiTable = ({ columns, rows, emptyMessage = "No rows for this view." }: Props) => {
  if (rows.length === 0) {
    return <p className="text-sm text-slate-500">{emptyMessage}</p>;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
        <thead className="bg-slate-50">
          <tr>
            {columns.map((col) => (
              <th key={col} className="px-3 py-2 font-semibold text-slate-700">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {rows.map((row, index) => (
            <tr key={index}>
              {columns.map((col) => (
                <td key={col} className="whitespace-nowrap px-3 py-2 text-slate-800">
                  {row[col]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
