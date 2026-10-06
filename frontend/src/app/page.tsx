"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [status, setStatus] = useState<"loading" | "connected" | "unreachable">("loading");

  useEffect(() => {
    async function checkHealth() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(`${apiUrl}/health`);
        if (res.ok) {
          setStatus("connected");
        } else {
          setStatus("unreachable");
        }
      } catch (error) {
        setStatus("unreachable");
      }
    }
    checkHealth();
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <h1 className="text-4xl font-bold mb-8">Expense Claim Policy Review Assistant</h1>
      
      <div className="text-xl">
        {status === "loading" && <span className="text-gray-500">Checking backend status...</span>}
        {status === "connected" && <span className="text-green-500 font-semibold">Backend: connected</span>}
        {status === "unreachable" && <span className="text-red-500 font-semibold">Backend: unreachable</span>}
      </div>
    </main>
  );
}
