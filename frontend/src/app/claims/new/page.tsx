"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClaim } from "@/lib/api";
import Link from "next/link";

export default function NewClaimPage() {
  const router = useRouter();
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    claimant: "",
    date: "",
    category: "",
    amount: "",
    currency: "INR",
    description: "",
    receipt_available: false,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      
      const payload = {
        ...formData,
        amount: parseFloat(formData.amount) || 0,
      };

      const result = await createClaim(payload);
      router.push(`/claims/${result.claim.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create claim");
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    if (type === "checkbox") {
      const checked = (e.target as HTMLInputElement).checked;
      setFormData(prev => ({ ...prev, [name]: checked }));
    } else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-10 pb-20">
      <header className="space-y-4">
        <Link href="/claims" className="text-[11px] font-mono tracking-widest text-[#6B7280] hover:text-[#111111] uppercase transition-colors">
          &larr; Back to queue
        </Link>
        <div>
          <h1 className="text-2xl font-semibold text-[#111111] tracking-tight">New expense claim</h1>
          <p className="mt-1 text-sm text-[#6B7280]">Submit an expense for policy review.</p>
        </div>
      </header>

      {error && (
        <div className="py-3 px-4 bg-[#FEF2F2] border border-[#FECACA] rounded-md">
          <p className="text-sm text-[#B91C1C]">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-8">
        
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-6">
          <div className="space-y-1.5">
            <label htmlFor="claimant" className="block text-[13px] font-medium text-[#111111]">Claimant</label>
            <input
              type="text"
              name="claimant"
              id="claimant"
              required
              value={formData.claimant}
              onChange={handleChange}
              className="block w-full rounded-lg border-[#D1D5DB] bg-white text-[#111111] text-[14px] px-3 py-2 focus:ring-1 focus:ring-[#2563EB] focus:border-[#2563EB] outline-none border transition-colors"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="date" className="block text-[13px] font-medium text-[#111111]">Date</label>
            <input
              type="date"
              name="date"
              id="date"
              required
              value={formData.date}
              onChange={handleChange}
              className="block w-full rounded-lg border-[#D1D5DB] bg-white text-[#111111] text-[14px] px-3 py-2 focus:ring-1 focus:ring-[#2563EB] focus:border-[#2563EB] outline-none border transition-colors"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="category" className="block text-[13px] font-medium text-[#111111]">Category</label>
            <select
              name="category"
              id="category"
              required
              value={formData.category}
              onChange={handleChange}
              className="block w-full rounded-lg border-[#D1D5DB] bg-white text-[#111111] text-[14px] px-3 py-2 focus:ring-1 focus:ring-[#2563EB] focus:border-[#2563EB] outline-none border transition-colors"
            >
              <option value="">Select...</option>
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

          <div className="space-y-1.5">
            <label htmlFor="amount" className="block text-[13px] font-medium text-[#111111]">Amount</label>
            <div className="flex">
              <input
                type="number"
                name="amount"
                id="amount"
                step="0.01"
                min="0"
                required
                value={formData.amount}
                onChange={handleChange}
                className="block w-full rounded-l-lg border-[#D1D5DB] bg-white text-[#111111] text-[14px] px-3 py-2 focus:ring-1 focus:ring-[#2563EB] focus:border-[#2563EB] outline-none border border-r-0 transition-colors"
              />
              <select
                name="currency"
                value={formData.currency}
                onChange={handleChange}
                className="rounded-r-lg border border-[#D1D5DB] bg-[#FAFAF8] px-3 text-[14px] text-[#6B7280] outline-none focus:ring-1 focus:ring-[#2563EB] focus:border-[#2563EB] transition-colors"
              >
                <option value="INR">INR</option>
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
                <option value="GBP">GBP</option>
              </select>
            </div>
          </div>

          <div className="sm:col-span-2 space-y-1.5">
            <label htmlFor="description" className="block text-[13px] font-medium text-[#111111]">Description</label>
            <textarea
              id="description"
              name="description"
              rows={4}
              required
              value={formData.description}
              onChange={handleChange}
              placeholder="Provide a clear description of the expense..."
              className="block w-full rounded-lg border-[#D1D5DB] bg-white text-[#111111] placeholder-[#9CA3AF] text-[14px] px-3 py-2.5 focus:ring-1 focus:ring-[#2563EB] focus:border-[#2563EB] outline-none border transition-colors resize-none"
            />
          </div>

          <div className="sm:col-span-2 pt-2">
            <label className="flex items-start gap-3 cursor-pointer group">
              <div className="flex items-center h-5">
                <input
                  id="receipt_available"
                  name="receipt_available"
                  type="checkbox"
                  checked={formData.receipt_available}
                  onChange={handleChange}
                  className="w-4 h-4 rounded border-[#D1D5DB] text-[#2563EB] focus:ring-[#2563EB] cursor-pointer"
                />
              </div>
              <div className="text-[13px]">
                <span className="font-medium text-[#111111] block group-hover:text-black">Receipt Available</span>
                <span className="text-[#6B7280]">I have a valid receipt for this expense.</span>
              </div>
            </label>
          </div>
        </div>

        <div className="pt-4 border-t border-[#E5E7EB]">
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2.5 bg-[#2563EB] hover:bg-blue-700 text-white text-[13px] font-medium rounded-lg transition-colors disabled:bg-[#9CA3AF]"
          >
            {loading ? "Submitting..." : "Submit for review \u2192"}
          </button>
        </div>
      </form>
    </div>
  );
}
