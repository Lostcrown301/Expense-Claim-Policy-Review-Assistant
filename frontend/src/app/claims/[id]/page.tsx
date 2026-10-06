"use client";

import { useEffect, useState, use, useCallback } from "react";
import { getClaim, makeDecision, getClaimHistory } from "@/lib/api";
import { ClaimDetailResponse, DecisionResponse } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";
import Link from "next/link";
import { Check, X, AlertTriangle } from "lucide-react";

export default function ClaimDetail({ params }: { params: Promise<{ id: string }> }) {
  const unwrappedParams = use(params);
  const { id } = unwrappedParams;

  const [claimData, setClaimData] = useState<ClaimDetailResponse | null>(null);
  const [history, setHistory] = useState<DecisionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [actionModal, setActionModal] = useState<"approve" | "reject" | "request_clarification" | "override_category" | null>(null);
  const [actionReason, setActionReason] = useState("");
  const [actionCategory, setActionCategory] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const data = await getClaim(id);
      setClaimData(data);
      const hData = await getClaimHistory(id);
      setHistory(hData.history || []);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load claim details");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadData();
  }, [loadData]);

  const handleAction = async () => {
    if (!actionModal) return;
    
    // Validate
    if (actionModal === "reject" && !actionReason.trim()) {
      setActionError("Reason is required for rejection");
      return;
    }
    if (actionModal === "override_category" && (!actionCategory.trim() || !actionReason.trim())) {
      setActionError("Both new category and reason are required");
      return;
    }
    if (actionModal === "request_clarification" && !actionReason.trim()) {
      setActionError("Information requested reason is required");
      return;
    }

    try {
      setActionLoading(true);
      setActionError(null);
      await makeDecision(id, {
        action: actionModal,
        reason: actionReason.trim() || undefined,
        category: actionModal === "override_category" ? actionCategory.trim() : undefined,
      });
      
      await loadData();
      closeModal();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to submit decision");
    } finally {
      setActionLoading(false);
    }
  };

  const closeModal = () => {
    setActionModal(null);
    setActionReason("");
    setActionCategory("");
    setActionError(null);
  };

  if (loading) {
    return (
      <div className="space-y-8 animate-pulse max-w-4xl">
        <div className="h-4 w-24 bg-gray-200 rounded"></div>
        <div className="space-y-4">
          <div className="h-3 w-16 bg-gray-100 rounded"></div>
          <div className="h-8 w-2/3 bg-gray-200 rounded"></div>
          <div className="h-4 w-1/3 bg-gray-100 rounded"></div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-12 mt-12">
          <div className="lg:col-span-2 space-y-12">
            <div className="h-32 bg-gray-100 rounded"></div>
            <div className="h-48 bg-gray-100 rounded"></div>
          </div>
          <div className="space-y-6">
            <div className="h-40 bg-gray-100 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !claimData) {
    return (
      <div className="py-4 px-5 bg-red-50/50 border border-red-100 rounded-md">
        <h3 className="text-sm font-medium text-red-800">Error loading claim</h3>
        <p className="mt-1 text-sm text-red-600">{error || "Claim not found"}</p>
        <Link href="/claims" className="mt-3 inline-block text-xs font-semibold text-red-700 hover:text-red-800 uppercase tracking-wide">
          &larr; Back to queue
        </Link>
      </div>
    );
  }

  const { claim, validation, ai_review } = claimData;

  return (
    <div className="space-y-12 pb-24">
      {/* Header */}
      <header className="space-y-6">
        <Link href="/claims" className="text-[11px] font-mono tracking-widest text-[#6B7280] hover:text-[#111111] uppercase transition-colors">
          &larr; Back to queue
        </Link>
        <div className="space-y-4 max-w-2xl">
          <div className="text-[11px] font-mono tracking-widest text-[#6B7280] uppercase">
            Claim {claim.id.toString().padStart(2, '0')}
          </div>
          <h1 className="text-3xl font-semibold text-[#111111] tracking-tight leading-tight">
            {claim.description}
          </h1>
          <div className="text-sm text-[#6B7280] flex flex-wrap items-center gap-x-3 gap-y-2">
            <span className="font-medium text-[#111111]">{claim.claimant}</span>
            <span className="text-[#E5E7EB]">&middot;</span>
            <span>{claim.date}</span>
            <span className="text-[#E5E7EB]">&middot;</span>
            <span>{claim.currency} {claim.amount?.toLocaleString()}</span>
            <span className="text-[#E5E7EB]">&middot;</span>
            <span>{claim.category}</span>
            <span className="text-[#E5E7EB]">&middot;</span>
            <span className="flex items-center gap-1">
              {claim.receipt_available ? (
                <><Check className="w-3.5 h-3.5 text-[#6B7280]"/> Receipt provided</>
              ) : (
                <><X className="w-3.5 h-3.5 text-[#6B7280]"/> No receipt</>
              )}
            </span>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-start border-t border-[#E5E7EB] pt-12">
        
        {/* Left Column: Review Workspace */}
        <div className="lg:col-span-8 space-y-16">
          
          {/* Validation */}
          <section className="space-y-4">
            <h2 className="text-[11px] font-mono tracking-widest text-[#111111] uppercase">Validation</h2>
            <div className="space-y-2 text-[13px]">
              {!validation ? (
                <p className="text-gray-400 italic">No validation results</p>
              ) : (
                <>
                  {validation.errors.map((err, i) => (
                    <div key={`err-${i}`} className="flex items-start text-[#111111]">
                      <X className="w-4 h-4 mr-2.5 mt-0.5 text-[#B91C1C] shrink-0" />
                      <span><span className="font-medium">{err.check}:</span> {err.detail}</span>
                    </div>
                  ))}
                  {validation.warnings.map((warn, i) => (
                    <div key={`warn-${i}`} className="flex items-start text-[#111111]">
                      <AlertTriangle className="w-4 h-4 mr-2.5 mt-0.5 text-[#B45309] shrink-0" />
                      <span><span className="font-medium">{warn.check}:</span> {warn.detail}</span>
                    </div>
                  ))}
                  {validation.errors.length === 0 && validation.warnings.length === 0 && (
                    <div className="flex items-start text-[#111111]">
                      <Check className="w-4 h-4 mr-2.5 mt-0.5 text-[#15803D] shrink-0" />
                      <span>All deterministic checks passed.</span>
                    </div>
                  )}
                </>
              )}
            </div>
          </section>

          {/* AI Assessment */}
          <section className="space-y-5">
            <h2 className="text-[11px] font-mono tracking-widest text-[#111111] uppercase">AI Assessment</h2>
            {!ai_review ? (
              <p className="text-[13px] text-[#6B7280] italic">AI review not available.</p>
            ) : (
              <div className="space-y-6">
                <div className="flex flex-wrap gap-x-8 gap-y-4 text-[13px]">
                  <div>
                    <div className="text-[#6B7280] mb-1">Category</div>
                    <div className="font-medium text-[#111111]">{ai_review.category}</div>
                  </div>
                  <div>
                    <div className="text-[#6B7280] mb-1">Confidence</div>
                    <div className="font-medium text-[#111111] flex items-center gap-1.5">
                      {Math.round(ai_review.confidence * 100)}%
                      {ai_review.uncertain && <AlertTriangle className="w-3.5 h-3.5 text-[#B45309]"/>}
                    </div>
                  </div>
                  <div>
                    <div className="text-[#6B7280] mb-1">Assessment</div>
                    <div><StatusBadge status={ai_review.verdict} /></div>
                  </div>
                </div>

                {ai_review.uncertain && (
                  <div className="border-l-2 border-[#B45309] pl-4 space-y-2 py-1">
                    <div className="text-[13px] font-medium text-[#111111] flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-[#B45309]"/> Classification uncertain
                    </div>
                    <ul className="text-[13px] text-[#6B7280] space-y-1 list-disc pl-4">
                      {ai_review.uncertain_reasons?.map((reason, i) => (
                        <li key={i}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div>
                  <div className="text-[11px] font-mono tracking-widest text-[#6B7280] uppercase mb-2">Reasoning</div>
                  <p className="text-[14px] leading-relaxed text-[#111111]">{ai_review.reasoning}</p>
                </div>
              </div>
            )}
          </section>

          {/* Policy Evidence */}
          {/* Policy Evidence */}
          {ai_review?.citations && ai_review.citations.length > 0 && (
            <section className="space-y-4">
              <h2 className="text-[11px] font-mono tracking-widest text-[#111111] uppercase">Policy Evidence</h2>
              <div className="space-y-6">
                {ai_review.citations.map((cit, i) => (
                  <div key={i} className="space-y-2">
                    <div className="text-[13px] font-semibold text-[#111111]">
                      {cit.section}
                    </div>
                    <blockquote className="text-[15px] leading-relaxed text-[#6B7280] font-serif italic border-l-[3px] border-[#E5E7EB] pl-4 py-0.5">
                      &quot;{cit.quote}&quot;
                    </blockquote>
                    <div className="text-[11px] font-mono tracking-wide text-[#6B7280] flex items-center gap-1.5 uppercase">
                      {cit.quote_verified ? (
                        <><Check className="w-3.5 h-3.5 text-[#15803D]" /> Verified</>
                      ) : (
                        <><X className="w-3.5 h-3.5 text-[#B91C1C]" /> Unverified quote</>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Missing Information */}
          {ai_review?.missing_info && ai_review.missing_info.length > 0 && (
            <section className="space-y-4">
              <h2 className="text-[11px] font-mono tracking-widest text-[#111111] uppercase">Needs from claimant</h2>
              <ul className="text-[14px] text-[#111111] space-y-3">
                {ai_review.missing_info.map((info, i) => (
                  <li key={i} className="flex gap-4">
                    <span className="text-[11px] font-mono text-[#6B7280] pt-0.5">{(i + 1).toString().padStart(2, '0')}</span>
                    <span>{info}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

        </div>

        {/* Right Column: Actions & History */}
        <div className="lg:col-span-4 space-y-12">
          
          <section className="bg-white border border-[#E5E7EB] rounded-xl p-5 space-y-5 shadow-sm">
            <h2 className="text-[11px] font-mono tracking-widest text-[#6B7280] uppercase">Review Decision</h2>
            
            <div className="space-y-3">
              <button 
                onClick={() => setActionModal("approve")} 
                className="w-full flex items-center justify-center py-2 px-4 bg-[#2563EB] hover:bg-blue-700 text-white text-[13px] font-medium rounded-lg transition-colors"
              >
                Approve
              </button>
              
              <div className="pt-2 space-y-2">
                <button 
                  onClick={() => setActionModal("request_clarification")} 
                  className="w-full text-left px-3 py-2 text-[13px] font-medium text-[#111111] hover:text-[#2563EB] hover:bg-gray-50 rounded-md transition-colors"
                >
                  Request clarification
                </button>
                <button 
                  onClick={() => setActionModal("override_category")} 
                  className="w-full text-left px-3 py-2 text-[13px] font-medium text-[#111111] hover:text-[#2563EB] hover:bg-gray-50 rounded-md transition-colors"
                >
                  Override category
                </button>
                <button 
                  onClick={() => setActionModal("reject")} 
                  className="w-full text-left px-3 py-2 text-[13px] font-medium text-[#B91C1C] hover:text-[#991B1B] hover:bg-red-50 rounded-md transition-colors"
                >
                  Reject
                </button>
              </div>
            </div>
          </section>

          <section className="space-y-5">
            <h2 className="text-[11px] font-mono tracking-widest text-[#111111] uppercase">Decision History</h2>
            {history.length === 0 ? (
              <p className="text-[13px] text-[#9CA3AF] italic">No decisions yet.</p>
            ) : (
              <div className="space-y-6">
                {history.map((event, i) => (
                  <div key={event.id} className="relative">
                    {i !== history.length - 1 && (
                      <div className="absolute left-[3px] top-6 bottom-[-16px] w-[1px] bg-[#E5E7EB]" />
                    )}
                    <div className="space-y-1.5">
                      <div className="text-[11px] font-mono text-[#9CA3AF] flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-[#D1D5DB]" />
                        <time dateTime={event.created_at}>
                          {new Date(event.created_at).toLocaleString('en-US', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
                        </time>
                      </div>
                      <div className="pl-3.5">
                        <p className="text-[13px] font-medium text-[#111111] capitalize">
                          {event.action === "approve" ? "approved" : 
                           event.action === "reject" ? "rejected" : 
                           event.action.replace(/_/g, " ")}
                        </p>
                        {event.reason && (
                          <p className="mt-1 text-[13px] text-[#6B7280] leading-relaxed">
                            &quot;{event.reason}&quot;
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

        </div>
      </div>

      {/* Modals remain mostly the same structurally but styled to match minimal aesthetic */}
      {actionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#111111]/20 backdrop-blur-sm">
          <div className="w-full max-w-md bg-white rounded-2xl shadow-xl overflow-hidden border border-[#E5E7EB]">
            <div className="p-6 space-y-6">
              <h3 className="text-lg font-semibold text-[#111111] capitalize tracking-tight">
                {actionModal.replace(/_/g, " ")}
              </h3>
              
              {actionError && (
                <div className="text-[13px] text-[#B91C1C] bg-[#FEF2F2] px-3 py-2 rounded border border-[#FECACA]">
                  {actionError}
                </div>
              )}

              <div className="space-y-4">
                {actionModal === "override_category" && (
                  <div className="space-y-1.5">
                    <label className="block text-[13px] font-medium text-[#111111]">New Category <span className="text-[#B91C1C]">*</span></label>
                    <select
                      className="w-full rounded-lg border-[#D1D5DB] bg-white text-[14px] text-[#111111] px-3 py-2.5 focus:bg-white focus:ring-1 focus:ring-[#2563EB] focus:border-[#2563EB] transition-colors outline-none border"
                      value={actionCategory}
                      onChange={(e) => setActionCategory(e.target.value)}
                    >
                      <option value="">Select category...</option>
                      <option value="Meals">Meals</option>
                      <option value="Travel Local">Travel Local</option>
                      <option value="Travel International">Travel International</option>
                      <option value="Accommodation">Accommodation</option>
                      <option value="Equipment">Equipment</option>
                      <option value="Training">Training</option>
                      <option value="Software">Software</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>
                )}

                <div className="space-y-1.5">
                  <label className="block text-[13px] font-medium text-[#111111]">
                    {actionModal === "approve" ? "Optional Reason" : <>Reason <span className="text-[#B91C1C]">*</span></>}
                  </label>
                  <textarea
                    className="w-full rounded-lg border-[#D1D5DB] bg-white text-[14px] text-[#111111] px-3 py-2.5 focus:bg-white focus:ring-1 focus:ring-[#2563EB] focus:border-[#2563EB] placeholder-[#9CA3AF] transition-colors outline-none border min-h-[100px] resize-none"
                    placeholder={actionModal === "request_clarification" ? "What information is needed?" : "Enter reason..."}
                    value={actionReason}
                    onChange={(e) => setActionReason(e.target.value)}
                  />
                </div>
              </div>
            </div>
            
            <div className="px-6 py-4 bg-[#FAFAF8] border-t border-[#E5E7EB] flex gap-3 justify-end">
              <button
                type="button"
                className="px-4 py-2 text-[13px] font-medium text-[#6B7280] hover:text-[#111111] transition-colors"
                onClick={closeModal}
                disabled={actionLoading}
              >
                Cancel
              </button>
              <button
                type="button"
                className={`px-4 py-2 text-[13px] font-medium text-white rounded-lg transition-colors ${
                  actionModal === "reject" ? "bg-[#DC2626] hover:bg-[#B91C1C]" :
                  actionModal === "approve" ? "bg-[#2563EB] hover:bg-blue-700" :
                  "bg-[#2563EB] hover:bg-blue-700"
                }`}
                onClick={handleAction}
                disabled={actionLoading}
              >
                {actionLoading ? "Submitting..." : `Confirm ${actionModal.split('_')[0]}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
