// Coloured pills for status / priority / category.
import { CATEGORY, PRIORITY, STATUS } from "../../utils/constants";

export function Badge({ className = "", children, title }) {
  return (
    <span
      title={title}
      className={`inline-flex items-center whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${className}`}
    >
      {children}
    </span>
  );
}

const make = (map) =>
  function MappedBadge({ value, title }) {
    const item = map[value] ?? { label: value, className: "bg-slate-100 text-slate-700 ring-slate-200" };
    return (
      <Badge className={item.className} title={title}>
        {item.label}
      </Badge>
    );
  };

export const StatusBadge = make(STATUS);
export const PriorityBadge = make(PRIORITY);
export const CategoryBadge = make(CATEGORY);
