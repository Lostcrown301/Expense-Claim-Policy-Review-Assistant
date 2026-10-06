"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getClaims } from "@/lib/api";
import { ClaimListItem } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";
import { AlertTriangle } from "lucide-react";

type FilterType = "all" | "needs_review" | "needs_clarification" | "complies";

export default function ClaimsPage() {
  const [claims, setClaims] = useState<ClaimListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<FilterType>("all");

  useEffect(() => {
    async function loadClaims() {
      try {
        const data = await getClaims();
        setClaims(data);
        setError(null);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load claims");
      } finally {
        setLoading(false);
      }
    }
    loadClaims();
  }, []);

  if (loading) {
    return (
      <div className="space-y-8 animate-pulse" role="status" aria-live="polite">
        <header className="flex items-center gap-3">
          <svg className="animate-spin h-5 w-5 text-[#2563EB]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <div>
            <h1 className="text-2xl font-semibold text-[#111111] tracking-tight">Loading review queue...</h1>
            <p className="mt-2 text-sm text-[#6B7280]">Fetching cases from the backend</p>
          </div>
        </header>

        <div className="border-b border-[#E5E7EB]">
          <div className="h-6 w-64 bg-[#E5E7EB]/50 rounded mb-3"></div>
        </div>

        <div className="flex flex-col">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="py-5 border-b border-[#E5E7EB] -mx-4 px-4">
              <div className="grid grid-cols-1 sm:grid-cols-12 gap-4 items-start">
                <div className="sm:col-span-8 space-y-2.5">
                  <div className="h-4 w-1/3 bg-[#D1D5DB]/50 rounded"></div>
                  <div className="h-3 w-1/2 bg-[#E5E7EB]/60 rounded"></div>
                </div>
                <div className="sm:col-span-4 flex justify-end">
                  <div className="h-5 w-20 bg-[#E5E7EB]/50 rounded"></div>
                </div>
              </div>
            </div>
          ))}
        </div>
        <span className="sr-only">Loading...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-4 px-5 bg-red-50/50 border border-red-100 rounded-md">
        <h3 className="text-sm font-medium text-red-800">Unable to load claims</h3>
        <p className="mt-1 text-sm text-red-600">{error}</p>
        <button 
          onClick={() => window.location.reload()}
          className="mt-3 text-xs font-semibold text-red-700 hover:text-red-800 uppercase tracking-wide"
        >
          Retry &rarr;
        </button>
      </div>
    );
  }

  const openClaimsCount = claims.filter(c => !c.latest_decision).length;

  // Derive filtered claims
  const filteredClaims = claims.filter(claim => {
    if (activeFilter === "all") return true;
    if (activeFilter === "needs_review") return claim.overall_status === "needs_review";
    if (activeFilter === "needs_clarification") return claim.overall_status === "needs_clarification";
    if (activeFilter === "complies") return claim.overall_status === "complies";
    return true;
  });

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-[#111111] tracking-tight">Review queue</h1>
        <p className="mt-2 text-sm text-[#6B7280]">
          {openClaimsCount} {openClaimsCount === 1 ? 'claim' : 'claims'} requiring attention
        </p>
      </header>

      <div className="border-b border-[#E5E7EB]">
        <nav className="-mb-px flex space-x-8 text-[13px] font-medium" aria-label="Claims filters">
          <button
            onClick={() => setActiveFilter("all")}
            aria-pressed={activeFilter === "all"}
            className={`pb-3 border-b-[2px] transition-colors cursor-pointer ${
              activeFilter === "all"
                ? "border-[#2563EB] text-[#111111]"
                : "border-transparent text-[#6B7280] hover:text-[#111111]"
            }`}
          >
            All
          </button>
          <button
            onClick={() => setActiveFilter("needs_review")}
            aria-pressed={activeFilter === "needs_review"}
            className={`pb-3 border-b-[2px] transition-colors cursor-pointer ${
              activeFilter === "needs_review"
                ? "border-[#2563EB] text-[#111111]"
                : "border-transparent text-[#6B7280] hover:text-[#111111]"
            }`}
          >
            Needs Review
          </button>
          <button
            onClick={() => setActiveFilter("needs_clarification")}
            aria-pressed={activeFilter === "needs_clarification"}
            className={`pb-3 border-b-[2px] transition-colors cursor-pointer ${
              activeFilter === "needs_clarification"
                ? "border-[#2563EB] text-[#111111]"
                : "border-transparent text-[#6B7280] hover:text-[#111111]"
            }`}
          >
            Clarification
          </button>
          <button
            onClick={() => setActiveFilter("complies")}
            aria-pressed={activeFilter === "complies"}
            className={`pb-3 border-b-[2px] transition-colors cursor-pointer ${
              activeFilter === "complies"
                ? "border-[#2563EB] text-[#111111]"
                : "border-transparent text-[#6B7280] hover:text-[#111111]"
            }`}
          >
            Complies
          </button>
        </nav>
      </div>

      <div className="flex flex-col">
        {claims.length === 0 ? (
          <div className="py-12">
            <h2 className="text-xl font-semibold text-[#111111] tracking-tight">No claims to review.</h2>
            <p className="mt-2 text-sm text-[#6B7280]">All caught up.</p>
            <Link
              href="/claims/new"
              className="mt-6 inline-flex text-sm font-medium text-[#111111] hover:text-[#6B7280] transition-colors"
            >
              Submit a claim &rarr;
            </Link>
          </div>
        ) : filteredClaims.length === 0 ? (
          <div className="py-12 border-b border-[#E5E7EB]">
            <p className="text-sm text-[#6B7280]">No claims in this category.</p>
          </div>
        ) : (
          filteredClaims.map((claim) => (
            <Link 
              key={claim.id} 
              href={`/claims/${claim.id}`} 
              className="group block py-5 border-b border-[#E5E7EB] hover:border-[#D1D5DB] bg-transparent hover:bg-[#F5F5F2] transition-colors duration-150 -mx-4 px-4 cursor-pointer rounded-lg sm:rounded-none"
            >
              <div className="grid grid-cols-1 sm:grid-cols-12 gap-4 items-start relative">
                
                {/* Left Column: Description & Metadata */}
                <div className="sm:col-span-8 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-[#111111]">{claim.claimant}</span>
                    <span className="text-[#E5E7EB]">&middot;</span>
                    <span className="text-[#111111] text-sm truncate">{claim.description || "No description provided"}</span>
                  </div>
                  <div className="text-[13px] text-[#6B7280] flex items-center gap-2">
                    <span>{claim.category}</span>
                    <span className="text-[#E5E7EB]">&middot;</span>
                    <span>{claim.currency} {claim.amount?.toLocaleString()}</span>
                    <span className="text-[#E5E7EB]">&middot;</span>
                    <span>{claim.date}</span>
                  </div>
                </div>

                {/* Right Column: Status & Verdict */}
                <div className="sm:col-span-4 flex sm:flex-col items-center sm:items-end justify-between sm:justify-start gap-2 sm:gap-1.5">
                  <div className="flex items-center gap-2 group-hover:opacity-90 transition-opacity">
                    {claim.latest_decision ? (
                      <StatusBadge status={claim.latest_decision} />
                    ) : claim.overall_status ? (
                      <StatusBadge status={claim.overall_status} />
                    ) : (
                      <span className="text-[11px] font-medium tracking-wide uppercase text-[#6B7280]">Pending</span>
                    )}
                  </div>
                  
                  {claim.ai_verdict && !claim.latest_decision && (
                    <div className={`flex items-center gap-1.5 text-[11px] font-mono tracking-tight ${claim.ai_uncertain ? 'text-[#B45309]' : 'text-[#6B7280]'}`}>
                      {claim.ai_uncertain && (
                        <AlertTriangle className="w-3 h-3" />
                      )}
                      <span>
                        {claim.ai_uncertain ? "UNCERTAIN" : "AI REVIEW"}
                      </span>
                    </div>
                  )}
                </div>

              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
