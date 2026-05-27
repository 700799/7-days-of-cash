"use client";

import { useBillingStatus } from "@/lib/hooks";
import { getBillingPortalUrl } from "@/lib/api";

export function BillingBadge() {
  const { plan, isPro, loading } = useBillingStatus(true);

  if (loading) return null;

  async function handleManage() {
    try {
      const { url } = await getBillingPortalUrl();
      window.open(url, "_blank");
    } catch {
      window.location.href = "/#pricing";
    }
  }

  if (isPro) {
    return (
      <button
        type="button"
        onClick={handleManage}
        title="Manage your Pro subscription"
        className="text-[10px] uppercase px-2 py-0.5 border border-b7-green text-b7-green hover:bg-b7-green/10 transition rounded-sm"
      >
        ★ PRO
      </button>
    );
  }

  return (
    <a
      href="/#pricing"
      className="text-[10px] uppercase px-2 py-0.5 border border-b7-green-border text-b7-green-muted hover:text-b7-green hover:border-b7-green transition rounded-sm"
    >
      ↑ Upgrade
    </a>
  );
}
