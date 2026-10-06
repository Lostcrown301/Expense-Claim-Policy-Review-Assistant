export function StatusBadge({ status, type = "default" }: { status: string; type?: "default" | "success" | "warning" | "error" }) {
  let bgColor = "bg-gray-100";
  let textColor = "text-gray-600";
  let indicator = "●";

  if (type === "success") {
    bgColor = "bg-[#F0FDF4]";
    textColor = "text-[#15803D]";
    indicator = "✓";
  } else if (type === "warning") {
    bgColor = "bg-[#FFFBEB]";
    textColor = "text-[#B45309]";
  } else if (type === "error") {
    bgColor = "bg-[#FEF2F2]";
    textColor = "text-[#B91C1C]";
  }

  if (type === "default") {
    const s = status.toLowerCase();
    if (s.includes("complies") || s === "approve" || s === "pass") {
      bgColor = "bg-[#F0FDF4]";
      textColor = "text-[#15803D]";
      indicator = "✓";
    } else if (s.includes("review") || s.includes("fail") || s.includes("error") || s.includes("reject")) {
      bgColor = "bg-[#FEF2F2]";
      textColor = "text-[#B91C1C]";
    } else if (s.includes("clarification") || s.includes("warn")) {
      bgColor = "bg-[#FFFBEB]";
      textColor = "text-[#B45309]";
    }
  }

  let formattedStatus = status.replace(/_/g, " ");
  if (formattedStatus.toLowerCase() === "approve") formattedStatus = "approved";
  if (formattedStatus.toLowerCase() === "reject") formattedStatus = "rejected";

  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium tracking-wide uppercase ${bgColor} ${textColor}`}>
      <span aria-hidden="true">{indicator}</span>
      {formattedStatus}
    </span>
  );
}
