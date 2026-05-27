"""Stripe billing routes: checkout, customer portal, webhooks, status.

Checkout flow:
  1. Frontend calls POST /api/billing/checkout → gets {url}
  2. Redirect user to Stripe's hosted page
  3. Stripe calls POST /api/billing/webhook on subscription events
  4. Webhook updates subscriptions table
  5. GET /api/billing/status returns current plan for UI badge

Requires env vars:
    STRIPE_SECRET_KEY      sk_live_... or sk_test_...
    STRIPE_PUBLISHABLE_KEY pk_live_... (returned to frontend, not secret)
    STRIPE_PRO_PRICE_ID    price_...
    STRIPE_WEBHOOK_SECRET  whsec_... (from `stripe listen` or Stripe dashboard)
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response

from ..auth import get_current_user, get_current_user_optional
from ..db import get_conn
from ..models import User

router = APIRouter(prefix="/api/billing", tags=["billing"])
log = logging.getLogger(__name__)


def _stripe():
    """Lazy import + init stripe — avoids import error when key is absent in tests."""
    import stripe as _s
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="Billing not configured (STRIPE_SECRET_KEY missing)")
    _s.api_key = key
    return _s


def _upsert_subscription(
    user_id: str,
    *,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    plan: str = "free",
    status: str = "active",
    current_period_end: Optional[datetime] = None,
) -> None:
    """Write (or update) a row in the subscriptions table."""
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """INSERT INTO subscriptions
                       (user_id, stripe_customer_id, stripe_subscription_id,
                        plan, status, current_period_end, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, now())
                   ON CONFLICT (user_id) DO UPDATE SET
                       stripe_customer_id    = COALESCE(EXCLUDED.stripe_customer_id, subscriptions.stripe_customer_id),
                       stripe_subscription_id = COALESCE(EXCLUDED.stripe_subscription_id, subscriptions.stripe_subscription_id),
                       plan                  = EXCLUDED.plan,
                       status                = EXCLUDED.status,
                       current_period_end    = EXCLUDED.current_period_end,
                       updated_at            = now()""",
                [
                    user_id,
                    stripe_customer_id,
                    stripe_subscription_id,
                    plan,
                    status,
                    current_period_end,
                ],
            )


def _user_id_from_customer(customer_id: str) -> Optional[str]:
    """Look up user_id by Stripe customer ID."""
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                "SELECT user_id FROM subscriptions WHERE stripe_customer_id = %s",
                [customer_id],
            )
            row = cur.fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# POST /api/billing/checkout
# ---------------------------------------------------------------------------

@router.post("/checkout")
def create_checkout(
    user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """Create a Stripe Checkout session and return the hosted URL.

    Frontend redirects the user to this URL. On completion Stripe webhooks
    back to /api/billing/webhook which updates the DB.
    """
    stripe = _stripe()
    price_id = os.environ.get("STRIPE_PRO_PRICE_ID", "")
    if not price_id:
        raise HTTPException(status_code=503, detail="Billing not configured (STRIPE_PRO_PRICE_ID missing)")

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")

    # Look up or create Stripe customer tied to this user
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                "SELECT stripe_customer_id FROM subscriptions WHERE user_id = %s",
                [user.id],
            )
            row = cur.fetchone()
    existing_customer_id = row[0] if row else None

    customer_kwargs: Dict[str, Any] = {}
    if existing_customer_id:
        customer_kwargs["customer"] = existing_customer_id
    else:
        customer_kwargs["customer_email"] = user.email

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{frontend_url}/?checkout=success",
            cancel_url=f"{frontend_url}/pricing?checkout=canceled",
            metadata={"user_id": user.id},
            **customer_kwargs,
        )
    except Exception as e:
        log.exception("Stripe checkout creation failed")
        raise HTTPException(status_code=502, detail=f"Stripe error: {e}")

    return {"url": session.url}


# ---------------------------------------------------------------------------
# GET /api/billing/portal
# ---------------------------------------------------------------------------

@router.get("/portal")
def billing_portal(
    user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """Create a Stripe Customer Portal session for the authenticated user.

    The portal lets users manage/cancel their subscription without us
    handling the UI ourselves.
    """
    stripe = _stripe()

    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                "SELECT stripe_customer_id FROM subscriptions WHERE user_id = %s",
                [user.id],
            )
            row = cur.fetchone()

    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="No Stripe customer found. Subscribe first.")

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")

    try:
        session = stripe.billing_portal.Session.create(
            customer=row[0],
            return_url=f"{frontend_url}/?portal=return",
        )
    except Exception as e:
        log.exception("Stripe portal creation failed")
        raise HTTPException(status_code=502, detail=f"Stripe error: {e}")

    return {"url": session.url}


# ---------------------------------------------------------------------------
# GET /api/billing/status
# ---------------------------------------------------------------------------

@router.get("/status")
def billing_status(
    user: Optional[User] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    """Return the current billing state for the authenticated user.

    Anonymous → {plan: "free", status: "none"}
    No subscription row → {plan: "free", status: "none"}
    """
    if user is None:
        return {"plan": "free", "status": "none", "period_end": None}

    try:
        with get_conn() as c:
            with c.cursor() as cur:
                cur.execute(
                    """SELECT plan, status, current_period_end
                       FROM subscriptions WHERE user_id = %s""",
                    [user.id],
                )
                row = cur.fetchone()
    except Exception:
        return {"plan": "free", "status": "none", "period_end": None}

    if not row:
        return {"plan": "free", "status": "none", "period_end": None}

    plan, sub_status, period_end = row
    # past_due / canceled → downgrade to free in the response
    effective_plan = "pro" if (plan == "pro" and sub_status in ("active", "trialing")) else "free"

    return {
        "plan": effective_plan,
        "status": sub_status or "none",
        "period_end": period_end.isoformat() if period_end else None,
        "publishable_key": os.environ.get("STRIPE_PUBLISHABLE_KEY", ""),
    }


# ---------------------------------------------------------------------------
# POST /api/billing/webhook
# ---------------------------------------------------------------------------

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(default=None, alias="stripe-signature"),
) -> Dict[str, str]:
    """Receive Stripe webhook events and update subscriptions table.

    Vercel forwards the raw body unchanged. We verify the signature using
    the STRIPE_WEBHOOK_SECRET env var before touching the DB.
    """
    stripe = _stripe()
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    payload = await request.body()

    if webhook_secret:
        try:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, webhook_secret
            )
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid Stripe signature")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Webhook parse error: {e}")
    else:
        # Dev mode: no signature check (never reached in prod with STRIPE_WEBHOOK_SECRET set)
        try:
            event = json.loads(payload)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = event.get("type", event.get("type", ""))
    data_obj = event.get("data", {}).get("object", {})
    log.info("Stripe webhook: %s", event_type)

    try:
        if event_type == "checkout.session.completed":
            # Link user → Stripe customer after first checkout
            user_id = (data_obj.get("metadata") or {}).get("user_id")
            customer_id = data_obj.get("customer")
            if user_id and customer_id:
                _upsert_subscription(
                    user_id,
                    stripe_customer_id=customer_id,
                    stripe_subscription_id=data_obj.get("subscription"),
                    plan="pro",
                    status="active",
                )

        elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
            customer_id = data_obj.get("customer")
            user_id = _user_id_from_customer(customer_id)
            if user_id:
                sub_status = data_obj.get("status", "active")
                plan = "pro" if sub_status in ("active", "trialing") else "free"
                period_end_ts = data_obj.get("current_period_end")
                period_end = (
                    datetime.fromtimestamp(period_end_ts, tz=timezone.utc)
                    if period_end_ts
                    else None
                )
                _upsert_subscription(
                    user_id,
                    stripe_customer_id=customer_id,
                    stripe_subscription_id=data_obj.get("id"),
                    plan=plan,
                    status=sub_status,
                    current_period_end=period_end,
                )

        elif event_type == "customer.subscription.deleted":
            customer_id = data_obj.get("customer")
            user_id = _user_id_from_customer(customer_id)
            if user_id:
                _upsert_subscription(
                    user_id,
                    stripe_customer_id=customer_id,
                    plan="free",
                    status="canceled",
                )

        elif event_type == "invoice.payment_failed":
            customer_id = data_obj.get("customer")
            user_id = _user_id_from_customer(customer_id)
            if user_id:
                _upsert_subscription(
                    user_id,
                    stripe_customer_id=customer_id,
                    plan="pro",
                    status="past_due",
                )

    except Exception as e:
        log.exception("Failed to process Stripe event %s", event_type)
        # Return 200 so Stripe doesn't retry — log is enough; DB state will
        # be reconciled on the next subscription update event.
        return {"ok": False, "error": str(e)}

    return {"ok": True, "event": event_type}
