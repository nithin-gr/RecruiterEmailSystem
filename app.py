import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

from config import config

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Recruiter Outreach",
    page_icon="✉️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session-state defaults ──────────────────────────────────────────────────────
_defaults = {
    "email_rows": [],        # list[dict] with keys: email, include
    "domain": "",
    "subject": "",
    "body": "",
    "send_results": [],
    "recruiter_name": "",
    "recruiter_title": "",
    "company": "",
    "role_applied": "",
    "generation_done": False,
    "composition_done": False,
    "send_done": False,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Sidebar – credentials ───────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Settings")

    st.subheader("Your details")
    sender_name = st.text_input("Your full name", placeholder="Jane Smith")
    gmail_address = st.text_input("Your Gmail address", placeholder="jane@gmail.com")
    gmail_app_password = st.text_input(
        "Gmail App Password",
        type="password",
        help="Generate at myaccount.google.com/apppasswords — NOT your normal password",
    )

    st.subheader("OpenAI")
    openai_key = st.text_input("OpenAI API key", type="password", placeholder="sk-…")

    st.divider()
    st.caption(
        "Gmail App Password: enable 2-Step Verification, then generate an App Password "
        "at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)."
    )

    creds_ok = bool(sender_name and gmail_address and gmail_app_password and openai_key)
    if not creds_ok:
        st.warning("Fill in all credentials to get started.")


def _apply_creds():
    """Push sidebar credentials into the shared config object."""
    config.openai_api_key = openai_key
    config.gmail_address = gmail_address
    config.gmail_app_password = gmail_app_password


# ── Tabs ────────────────────────────────────────────────────────────────────────
tab_send, tab_bounces, tab_records = st.tabs(["✉️ Send Outreach", "↩️ Check Bounces", "📊 Records"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 – SEND OUTREACH
# ══════════════════════════════════════════════════════════════════════════════
with tab_send:

    # ── STEP 1 – Recruiter info ─────────────────────────────────────────────
    st.header("Step 1 — Recruiter details")
    col1, col2 = st.columns(2)
    with col1:
        recruiter_name = st.text_input("Recruiter / Hiring Manager name", placeholder="John Doe")
        recruiter_title = st.text_input("Their title", placeholder="Senior Technical Recruiter")
    with col2:
        company = st.text_input("Company", placeholder="Acme Corp")
        company_domain = st.text_input(
            "Company email domain (optional)",
            placeholder="acme.com – leave blank to auto-detect",
        )
    role_applied = st.text_input("Role you're applying for", placeholder="Senior Software Engineer")

    generate_btn = st.button(
        "🔍 Generate Email Combinations",
        disabled=not (creds_ok and recruiter_name and company and role_applied),
        use_container_width=True,
    )

    if generate_btn:
        _apply_creds()
        # Reset downstream state
        for k in ("email_rows", "subject", "body", "send_results",
                  "generation_done", "composition_done", "send_done"):
            st.session_state[k] = _defaults[k]

        st.session_state.recruiter_name = recruiter_name
        st.session_state.recruiter_title = recruiter_title
        st.session_state.company = company
        st.session_state.role_applied = role_applied

        with st.status("Generating email combinations…", expanded=True) as status:
            st.write("Asking GPT-4o to infer domain and common address formats…")
            from email_generator import generate_email_combinations
            result = generate_email_combinations(
                recruiter_name, company, company_domain or None
            )
            st.write(f"Domain identified: **{result['domain']}**")
            st.write(f"GPT reasoning: _{result['gpt_reasoning']}_")
            st.write(f"Building deterministic pattern variants…")
            time.sleep(0.3)
            emails = result["emails"]
            st.write(f"✅ {len(emails)} unique candidate addresses assembled.")
            status.update(label="Email combinations ready!", state="complete")

        st.session_state.domain = result["domain"]
        st.session_state.email_rows = [{"include": True, "email": e} for e in emails]
        st.session_state.generation_done = True

    # ── STEP 2 – Review emails + compose ───────────────────────────────────
    if st.session_state.generation_done:
        st.divider()
        st.header("Step 2 — Review addresses & compose email")

        st.caption(
            f"Uncheck any addresses you want to skip. "
            f"Domain: **{st.session_state.domain}**"
        )

        edited = st.data_editor(
            pd.DataFrame(st.session_state.email_rows),
            column_config={
                "include": st.column_config.CheckboxColumn("Send?", default=True),
                "email": st.column_config.TextColumn("Email address", width="large"),
            },
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key="email_editor",
        )
        # Persist edits back to session state on next run
        st.session_state.email_rows = edited.to_dict("records")

        selected_count = int(edited["include"].sum()) if "include" in edited.columns else 0
        st.caption(f"{selected_count} address(es) selected for sending.")

        st.subheader("Job description & resume")
        job_description = st.text_area(
            "Job description",
            height=200,
            placeholder="Paste the full job description here…",
        )
        resume_text = st.text_area(
            "Your resume (plain text)",
            height=200,
            placeholder="Paste your resume here…",
        )

        compose_btn = st.button(
            "✍️ Compose Email with GPT-4o",
            disabled=not (job_description and resume_text and selected_count > 0),
            use_container_width=True,
        )

        if compose_btn:
            _apply_creds()
            with st.status("Composing outreach email…", expanded=True) as status:
                st.write("Sending resume + JD to GPT-4o…")
                from email_composer import compose_email
                composed = compose_email(
                    recruiter_name=st.session_state.recruiter_name,
                    recruiter_title=st.session_state.recruiter_title,
                    company=st.session_state.company,
                    role_title=st.session_state.role_applied,
                    job_description=job_description,
                    resume_text=resume_text,
                    sender_name=sender_name,
                )
                st.write("✅ Email drafted.")
                status.update(label="Email composed!", state="complete")

            st.session_state.subject = composed["subject"]
            st.session_state.body = composed["body"]
            st.session_state.composition_done = True
            # Save JD/resume in state for Excel notes
            st.session_state.job_description = job_description

    # ── STEP 3 – Edit & send ────────────────────────────────────────────────
    if st.session_state.composition_done:
        st.divider()
        st.header("Step 3 — Review, edit & send")

        subject_input = st.text_input("Subject", value=st.session_state.subject, key="subject_edit")
        body_input = st.text_area("Email body", value=st.session_state.body, height=280, key="body_edit")

        selected_emails = [
            row["email"]
            for row in st.session_state.email_rows
            if row.get("include") and row.get("email")
        ]

        with st.expander(f"📋 Will send to {len(selected_emails)} address(es)"):
            for e in selected_emails:
                st.code(e)

        col_send, col_reset = st.columns([3, 1])
        with col_send:
            send_btn = st.button(
                f"🚀 Send to {len(selected_emails)} address(es)",
                disabled=not (selected_emails and subject_input and body_input),
                use_container_width=True,
                type="primary",
            )
        with col_reset:
            if st.button("🔄 Start over", use_container_width=True):
                for k, v in _defaults.items():
                    st.session_state[k] = v
                st.rerun()

        if send_btn:
            _apply_creds()
            from gmail_client import send_email
            from excel_tracker import save_outreach_attempt

            results = []
            progress = st.progress(0, text="Sending…")
            status_placeholder = st.empty()

            for i, addr in enumerate(selected_emails):
                status_placeholder.info(f"Sending to `{addr}` …")
                res = send_email(addr, subject_input, body_input)
                res["to"] = addr
                results.append(res)

                save_outreach_attempt(
                    recruiter_name=st.session_state.recruiter_name,
                    recruiter_title=st.session_state.recruiter_title,
                    company=st.session_state.company,
                    role_applied=st.session_state.role_applied,
                    email_address=addr,
                    sent=res["success"],
                    sent_at=res.get("sent_at"),
                    subject=subject_input,
                    notes=res.get("error") or "",
                )

                progress.progress((i + 1) / len(selected_emails), text=f"{i+1}/{len(selected_emails)} sent")
                time.sleep(config.send_delay_seconds)

            status_placeholder.empty()
            st.session_state.send_results = results
            st.session_state.send_done = True

        if st.session_state.send_done and st.session_state.send_results:
            results_df = pd.DataFrame(st.session_state.send_results)[["to", "success", "error", "sent_at"]]
            results_df.columns = ["Email", "Sent", "Error", "Sent At"]
            results_df["Sent"] = results_df["Sent"].map({True: "✅", False: "❌"})

            ok = results_df["Sent"].str.contains("✅").sum()
            fail = len(results_df) - ok
            st.success(f"Done! {ok} sent, {fail} failed.")
            st.dataframe(results_df, use_container_width=True, hide_index=True)
            st.info(
                "Switch to the **↩️ Check Bounces** tab a few hours from now to detect "
                "which addresses are invalid — this helps confirm the real email."
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 – CHECK BOUNCES
# ══════════════════════════════════════════════════════════════════════════════
with tab_bounces:
    st.header("↩️ Check for bounce notifications")
    st.write(
        "Gmail will deliver \"Mail Delivery Subsystem\" failure messages back to your inbox "
        "when an address doesn't exist. Run this a few hours after sending."
    )

    hours_back = st.slider("Scan inbox from how many hours ago?", 1, 72, 24)

    check_btn = st.button(
        "🔎 Scan Gmail inbox for bounces",
        disabled=not creds_ok,
        use_container_width=True,
    )

    if check_btn:
        _apply_creds()
        since = datetime.now(timezone.utc) - timedelta(hours=hours_back)

        with st.status(f"Scanning inbox since {since.strftime('%Y-%m-%d %H:%M UTC')}…", expanded=True) as status:
            from gmail_client import check_bounces
            from excel_tracker import apply_bounce_results, print_confirmed_emails
            import io, contextlib

            bounced = check_bounces(since_datetime=since)
            st.write(f"Found **{len(bounced)}** bounce notification(s).")

            if bounced:
                for addr in bounced:
                    st.write(f"  ↩ `{addr}`")
                apply_bounce_results(bounced)
                st.write("Excel updated.")

            status.update(label="Bounce check complete!", state="complete")

        if bounced:
            st.warning(f"{len(bounced)} address(es) bounced. Excel updated — check the Records tab.")
        else:
            st.success("No bounces detected in that window.")

    st.divider()
    st.subheader("Inferred confirmed emails")
    st.caption("An address is marked confirmed when all other addresses for that recruiter have bounced.")

    if st.button("📋 Refresh confirmed emails", use_container_width=True):
        import os
        if os.path.exists(config.excel_file):
            df = pd.read_excel(config.excel_file, engine="openpyxl")
            confirmed = (
                df[df["Confirmed Email"].notna() & (df["Confirmed Email"] != "")]
                [["Recruiter Name", "Company", "Role Applied", "Confirmed Email"]]
                .drop_duplicates()
            )
            if confirmed.empty:
                st.info("No confirmed emails yet — run a bounce check first.")
            else:
                st.dataframe(confirmed, use_container_width=True, hide_index=True)
        else:
            st.info("No records file yet — send some emails first.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 – RECORDS
# ══════════════════════════════════════════════════════════════════════════════
with tab_records:
    st.header("📊 Outreach records")

    col_refresh, col_download = st.columns([1, 1])

    with col_refresh:
        refresh = st.button("🔄 Load / refresh records", use_container_width=True)

    if refresh:
        import os
        if os.path.exists(config.excel_file):
            df = pd.read_excel(config.excel_file, engine="openpyxl")
            st.session_state["records_df"] = df
        else:
            st.session_state["records_df"] = None

    if "records_df" in st.session_state and st.session_state["records_df"] is not None:
        df: pd.DataFrame = st.session_state["records_df"]

        # Summary metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total attempts", len(df))
        m2.metric("Sent", (df["Sent"] == "Yes").sum() if "Sent" in df.columns else 0)
        m3.metric("Bounced", (df["Bounced"] == "Yes").sum() if "Bounced" in df.columns else 0)
        confirmed_count = (
            df["Confirmed Email"].notna() & (df["Confirmed Email"] != "")
        ).sum() if "Confirmed Email" in df.columns else 0
        m4.metric("Confirmed", confirmed_count)

        st.divider()

        # Filters
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            companies = ["All"] + sorted(df["Company"].dropna().unique().tolist()) if "Company" in df.columns else ["All"]
            company_filter = st.selectbox("Filter by company", companies)
        with col_f2:
            statuses = ["All", "Sent", "Not sent", "Bounced", "Confirmed"]
            status_filter = st.selectbox("Filter by status", statuses)

        filtered = df.copy()
        if company_filter != "All":
            filtered = filtered[filtered["Company"] == company_filter]
        if status_filter == "Sent":
            filtered = filtered[filtered["Sent"] == "Yes"]
        elif status_filter == "Not sent":
            filtered = filtered[filtered["Sent"] != "Yes"]
        elif status_filter == "Bounced":
            filtered = filtered[filtered["Bounced"] == "Yes"]
        elif status_filter == "Confirmed":
            filtered = filtered[filtered["Confirmed Email"].notna() & (filtered["Confirmed Email"] != "")]

        st.dataframe(filtered, use_container_width=True, hide_index=True)

        # Download button
        import io
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        st.download_button(
            "⬇️ Download Excel",
            data=buf.getvalue(),
            file_name="recruiter_outreach.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info("Click **Load / refresh records** to view your outreach history.")
