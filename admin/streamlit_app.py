"""Geshtu admin UI. Single-file Streamlit app — keep it dumb.

Talks to the API over HTTP using the admin's JWT (entered once per session).
Shows: projects, facts, decisions, users, tokens, recent digests.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import httpx
import pandas as pd
import streamlit as st

API_URL = os.environ.get("API_URL", "http://api:8000")

st.set_page_config(page_title="Geshtu Admin", page_icon=":ear:", layout="wide")


# ─── Auth ────────────────────────────────────────────────────────────


def _authed_client(token: str) -> httpx.Client:
    return httpx.Client(
        base_url=API_URL,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=30,
    )


def _login_panel() -> str | None:
    st.title("Geshtu — Admin")
    st.caption("Self-hosted shared memory for teams using LLMs")
    st.text_input(
        "Admin token",
        key="token",
        type="password",
        help="Run `docker compose exec api python -m geshtu.bootstrap` to issue one",
    )
    if not st.session_state.get("token"):
        st.info("Paste your admin token above to continue.")
        return None
    return st.session_state["token"]


def _check_token(token: str) -> dict | None:
    try:
        with _authed_client(token) as c:
            r = c.get("/users/me")
            r.raise_for_status()
            return r.json()
    except httpx.HTTPError as exc:
        st.error(f"Token rejected: {exc}")
        return None


# ─── Pages ───────────────────────────────────────────────────────────


def _page_overview(client: httpx.Client, me: dict) -> None:
    st.subheader("Overview")
    st.write(f"Signed in as **{me['display_name']}** ({me['email']}, role: `{me['role']}`).")

    cols = st.columns(3)
    try:
        projects = client.get("/projects").json()
    except httpx.HTTPError:
        projects = []
    cols[0].metric("Projects", len(projects))
    try:
        users = client.get("/users").json()
    except httpx.HTTPError:
        users = []
    cols[1].metric("Users", len(users) if isinstance(users, list) else "—")
    try:
        h = client.get("/health").json()
        cols[2].metric("API", h.get("status", "?"))
    except httpx.HTTPError:
        cols[2].metric("API", "down")


def _page_projects(client: httpx.Client) -> None:
    st.subheader("Projects")
    try:
        rows = client.get("/projects").json()
    except httpx.HTTPError as exc:
        st.error(str(exc))
        return
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No projects yet.")

    with st.expander("New project"):
        slug = st.text_input("Slug (lowercase, dashes)", key="new_proj_slug")
        name = st.text_input("Name", key="new_proj_name")
        desc = st.text_area("Description", key="new_proj_desc")
        if st.button("Create", key="new_proj_btn"):
            if not slug or not name:
                st.warning("slug + name required")
            else:
                r = client.post(
                    "/projects",
                    json={"slug": slug, "name": name, "description": desc or None},
                )
                if r.status_code >= 400:
                    st.error(r.text)
                else:
                    st.success(f"Created {slug}")
                    st.rerun()


def _page_facts(client: httpx.Client) -> None:
    st.subheader("Facts")
    projects = client.get("/projects").json()
    if not projects:
        st.info("No projects yet.")
        return
    slug = st.selectbox("Project", [p["slug"] for p in projects], key="facts_proj")
    q = st.text_input("Search query (leave empty to browse)", key="facts_q")
    if q.strip():
        r = client.get("/search", params={"project": slug, "q": q, "k": 25})
        if r.status_code >= 400:
            st.error(r.text)
            return
        data = r.json()
        st.write(f"**{len(data['facts'])}** facts, **{len(data['decisions'])}** decisions")
        if data["facts"]:
            st.dataframe(pd.DataFrame(data["facts"]), use_container_width=True, hide_index=True)
    else:
        st.caption("Type a query above to search this project's facts.")


def _page_decisions(client: httpx.Client) -> None:
    st.subheader("Decisions")
    projects = client.get("/projects").json()
    if not projects:
        st.info("No projects yet.")
        return
    slug = st.selectbox("Project", [p["slug"] for p in projects], key="dec_proj")
    limit = st.slider("Limit", 5, 200, 50, key="dec_lim")
    r = client.get("/decisions", params={"project": slug, "limit": limit})
    if r.status_code >= 400:
        st.error(r.text)
        return
    rows = r.json()
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No decisions yet.")


def _page_digests(client: httpx.Client) -> None:
    st.subheader("Digests")
    projects = client.get("/projects").json()
    if not projects:
        st.info("No projects yet.")
        return
    slug = st.selectbox("Project", [p["slug"] for p in projects], key="dig_proj")
    depth = st.radio("Depth", ["quick", "standard", "deep"], horizontal=True, key="dig_depth")
    since = st.date_input("Since (optional)", value=None, key="dig_since")
    use_cache = st.checkbox("Use cache (1 hour)", value=True, key="dig_cache")
    if st.button("Generate"):
        params: dict[str, Any] = {"project": slug, "depth": depth, "use_cache": use_cache}
        if since:
            params["since"] = since.isoformat() if isinstance(since, (datetime, type(since))) else str(since)
        with st.spinner("Calling Sonnet..."):
            r = client.get("/digest", params=params)
        if r.status_code >= 400:
            st.error(r.text)
        else:
            data = r.json()
            st.caption(
                f"{data['fact_count']} facts, {data['decision_count']} decisions"
                f" — {'cache hit' if data['cached'] else 'fresh'}"
            )
            st.markdown(data["content_md"])


def _page_users(client: httpx.Client) -> None:
    st.subheader("Users")
    rows = client.get("/users").json()
    if isinstance(rows, list):
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with st.expander("Add user"):
        email = st.text_input("Email", key="newuser_email")
        name = st.text_input("Display name", key="newuser_name")
        role = st.selectbox("Role", ["member", "admin"], key="newuser_role")
        if st.button("Create + issue token"):
            r = client.post(
                "/users",
                json={"email": email, "display_name": name, "role": role},
            )
            if r.status_code >= 400:
                st.error(r.text)
            else:
                data = r.json()
                st.success(f"Created. Token (shown ONCE):")
                st.code(data["token"], language="text")


def _page_tokens(client: httpx.Client) -> None:
    st.subheader("Tokens")
    users = client.get("/users").json()
    if not isinstance(users, list) or not users:
        st.info("No users yet.")
        return
    by_id = {u["id"]: u for u in users}
    pick = st.selectbox(
        "User",
        list(by_id.keys()),
        format_func=lambda uid: f"{by_id[uid]['display_name']} <{by_id[uid]['email']}>",
        key="tok_user",
    )
    rows = client.get(f"/users/{pick}/tokens").json()
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("No tokens for this user.")

    cols = st.columns(2)
    with cols[0]:
        label = st.text_input("Label for new token", key="tok_label")
        if st.button("Issue new token"):
            r = client.post(f"/users/{pick}/tokens", json={"label": label or None})
            if r.status_code >= 400:
                st.error(r.text)
            else:
                d = r.json()
                st.success("Token (shown ONCE):")
                st.code(d["token"], language="text")
    with cols[1]:
        if rows:
            tid = st.selectbox("Token to revoke", [t["id"] for t in rows if not t.get("revoked_at")], key="tok_revoke_id")
            if st.button("Revoke", type="primary"):
                r = client.post(f"/users/tokens/{tid}/revoke")
                if r.status_code >= 400:
                    st.error(r.text)
                else:
                    st.success("Revoked")
                    st.rerun()


# ─── Main ────────────────────────────────────────────────────────────


def main() -> None:
    token = _login_panel()
    if not token:
        return

    me = _check_token(token)
    if not me:
        return

    pages = {
        "Overview": _page_overview,
        "Projects": _page_projects,
        "Facts": _page_facts,
        "Decisions": _page_decisions,
        "Digests": _page_digests,
    }
    if me["role"] == "admin":
        pages["Users"] = _page_users
        pages["Tokens"] = _page_tokens

    page = st.sidebar.radio("Section", list(pages.keys()))
    st.sidebar.caption(f"Signed in: {me['email']}")
    st.sidebar.caption(f"API: {API_URL}")

    with _authed_client(token) as client:
        fn = pages[page]
        if page == "Overview":
            fn(client, me)
        else:
            fn(client)


if __name__ == "__main__":
    main()
