import { ClaimIn, DecisionCreate, ClaimDetailResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI(endpoint: string, options: RequestInit = {}) {
  const res = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  if (!res.ok) {
    let message = "API request failed";
    try {
      const data = await res.json();
      if (data.detail) {
        message = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // ignored
    }
    throw new Error(message);
  }
  return res.json();
}

export async function getClaims() {
  return fetchAPI("/claims");
}

export async function getClaim(id: string | number) {
  return fetchAPI(`/claims/${id}`);
}

export async function getClaimHistory(id: string | number) {
  return fetchAPI(`/claims/${id}/history`);
}

export async function createClaim(data: ClaimIn): Promise<ClaimDetailResponse> {
  return fetchAPI("/claims", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function makeDecision(id: string | number, data: DecisionCreate) {
  return fetchAPI(`/claims/${id}/decision`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}
