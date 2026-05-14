"use client";

import { formatDistanceToNow, parseISO } from "date-fns";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import {
  updatePreferences,
  type DigestFrequency,
  type Preferences,
} from "@/lib/api";
import { usePreferences } from "@/lib/hooks";

function nextDigestLabel(freq: DigestFrequency): string {
  if (freq === "none") return "off";
  if (freq === "daily") return "tomorrow 9am ET";
  return "next Monday 9am ET";
}

function relativeTime(iso: string): string {
  try {
    const d = parseISO(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return `${formatDistanceToNow(d)} ago`;
  } catch {
    return iso;
  }
}

export function EmailDigestSettings() {
  const { user } = useAuth();
  const signedIn = !!user;
  const { preferences, mutate } = usePreferences(signedIn);

  const [frequency, setFrequency] = useState<DigestFrequency>("none");
  const [email, setEmail] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<Preferences | null>(null);
  const [showSaved, setShowSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const savedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync local state when preferences are fetched.
  useEffect(() => {
    if (preferences) {
      setFrequency(preferences.digest_frequency);
      setEmail(preferences.digest_email ?? "");
    }
  }, [preferences]);

  // Clean up "✓ Saved" auto-fade timer on unmount.
  useEffect(() => {
    return () => {
      if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
    };
  }, []);

  if (!signedIn) return null;

  async function handleSave() {
    setSaving(true);
    setError(null);
    setShowSaved(false);
    if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
    try {
      const body: { digest_frequency: DigestFrequency; digest_email?: string } = {
        digest_frequency: frequency,
      };
      const trimmed = email.trim();
      if (trimmed) body.digest_email = trimmed;
      const updated = await updatePreferences(body);
      setSavedAt(updated);
      setShowSaved(true);
      savedTimerRef.current = setTimeout(() => setShowSaved(false), 3000);
      await mutate(updated, { revalidate: false });
    } catch (err) {
      setError(err instanceof Error ? err.message : "save failed");
    } finally {
      setSaving(false);
    }
  }

  const options: { value: DigestFrequency; label: string }[] = [
    { value: "none", label: "Off" },
    { value: "daily", label: "Daily 9am ET" },
    { value: "weekly", label: "Weekly Mondays 9am ET" },
  ];

  return (
    <section
      className="border border-b7-green-border p-3 space-y-3"
      data-testid="email-digest-settings"
      aria-label="email digest settings"
    >
      <h2 className="text-b7-green uppercase text-sm">{`> EMAIL DIGEST`}</h2>

      <div
        role="radiogroup"
        aria-label="digest frequency"
        className="flex flex-col sm:flex-row gap-3 space-y-2 sm:space-y-0"
      >
        {options.map((opt) => (
          <label
            key={opt.value}
            className="inline-flex items-center gap-2 text-b7-green text-xs uppercase cursor-pointer"
          >
            <input
              type="radio"
              name="digest-frequency"
              value={opt.value}
              checked={frequency === opt.value}
              onChange={() => setFrequency(opt.value)}
              className="accent-b7-green"
              aria-label={opt.label}
            />
            <span>{`( ${frequency === opt.value ? "•" : " "} ) ${opt.label}`}</span>
          </label>
        ))}
      </div>

      <div className="flex flex-col sm:flex-row gap-2 items-start sm:items-center">
        <label
          htmlFor="digest-email"
          className="text-b7-green-muted uppercase text-xs"
        >
          email override
        </label>
        <input
          id="digest-email"
          aria-label="digest email override"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder={user?.email ?? "you@example.com"}
          className="bg-black border border-b7-green-border text-b7-green px-2 py-1 placeholder:text-green-700 focus:outline-none focus:ring-2 focus:ring-b7-green focus:border-b7-green flex-1 text-xs"
          maxLength={200}
          autoComplete="off"
        />
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="inline-flex items-center gap-2 px-3 py-1 border border-b7-green-border text-b7-green hover:bg-green-500/10 hover:text-b7-green-dim transition rounded-sm uppercase text-xs disabled:opacity-50"
        >
          {saving ? "saving…" : "[ SAVE ]"}
        </button>
      </div>

      {showSaved && savedAt && (
        <div
          role="status"
          data-testid="digest-saved"
          className="text-b7-green-dim text-xs uppercase transition-opacity"
        >
          {`✓ Saved. Next digest: ${nextDigestLabel(savedAt.digest_frequency)}`}
        </div>
      )}
      {error && (
        <div role="alert" className="text-red-400 text-xs uppercase">
          {`! ${error}`}
        </div>
      )}

      {preferences?.last_sent_at && (
        <div className="text-b7-green-muted text-xs uppercase">
          {`> Last sent ${relativeTime(preferences.last_sent_at)}`}
        </div>
      )}
    </section>
  );
}
