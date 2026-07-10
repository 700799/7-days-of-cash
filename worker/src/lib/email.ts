// Email via Resend REST API. SMTP is not possible from Workers (no raw TCP),
// so Resend is the only provider — send_email is a no-op returning false when
// RESEND_API_KEY is unset.

import type { Env } from "../types";

const RESEND_URL = "https://api.resend.com/emails";
const DEFAULT_FROM = "Best7DaysMula <onboarding@resend.dev>";

export async function sendEmail(
  env: Env,
  to: string,
  subject: string,
  html: string,
  text: string,
): Promise<boolean> {
  if (!env.RESEND_API_KEY) {
    console.warn("sendEmail skipped: RESEND_API_KEY not configured");
    return false;
  }
  try {
    const res = await fetch(RESEND_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.RESEND_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: env.EMAIL_FROM || DEFAULT_FROM,
        to: [to],
        subject,
        html,
        text,
      }),
    });
    if (!res.ok) {
      console.warn(`Resend error ${res.status}: ${await res.text()}`);
      return false;
    }
    return true;
  } catch (e) {
    console.warn(`Resend request failed: ${e}`);
    return false;
  }
}
