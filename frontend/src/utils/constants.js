// Statuses, categories, priorities and their display labels/colours (mirror the backend enums).

export const STATUS = {
  OPEN: { label: "Open", className: "bg-sky-100 text-sky-800 ring-sky-200" },
  IN_PROGRESS: { label: "In Progress", className: "bg-amber-100 text-amber-800 ring-amber-200" },
  RESOLVED: { label: "Resolved", className: "bg-emerald-100 text-emerald-800 ring-emerald-200" },
  CLOSED: { label: "Closed", className: "bg-slate-100 text-slate-600 ring-slate-200" },
};

export const PRIORITY = {
  CRITICAL: { label: "Critical", className: "bg-red-600 text-white ring-red-600" },
  HIGH: { label: "High", className: "bg-orange-100 text-orange-800 ring-orange-200" },
  MEDIUM: { label: "Medium", className: "bg-yellow-50 text-yellow-800 ring-yellow-200" },
  LOW: { label: "Low", className: "bg-slate-100 text-slate-600 ring-slate-200" },
};

export const CATEGORY = {
  ROYALTY_PAYMENTS: { label: "Royalty & Payments", className: "bg-violet-50 text-violet-700 ring-violet-200" },
  ISBN_METADATA: { label: "ISBN & Metadata", className: "bg-fuchsia-50 text-fuchsia-700 ring-fuchsia-200" },
  PRINTING_QUALITY: { label: "Printing & Quality", className: "bg-rose-50 text-rose-700 ring-rose-200" },
  DISTRIBUTION: { label: "Distribution", className: "bg-cyan-50 text-cyan-700 ring-cyan-200" },
  PRODUCTION_STATUS: { label: "Production Status", className: "bg-teal-50 text-teal-700 ring-teal-200" },
  GENERAL: { label: "General Inquiry", className: "bg-slate-50 text-slate-700 ring-slate-200" },
};

export const CLASSIFIED_BY = { RULES: "Keyword rules", AI: "AI", ADMIN: "Admin override" };

export const PRODUCTION_STAGES = [
  "Manuscript Received",
  "Editing",
  "Cover Design",
  "Typesetting",
  "Proofreading",
  "ISBN Assignment",
  "Printing",
  "Distribution Setup",
  "Published & Live",
];

// How often each screen refreshes itself (milliseconds), so updates appear without reloading.
export const POLL_MS = { authorTickets: 5000, adminQueue: 10000, adminTicket: 8000 };
