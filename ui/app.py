import os

import requests
import streamlit as st

API_URL = os.getenv("AGENT_API_URL", "http://localhost:8000")
_API_KEY = os.getenv("API_KEY", "")
_HEADERS = {"X-API-Key": _API_KEY} if _API_KEY else {}

st.set_page_config(
    page_title="K8s Troubleshooter",
    page_icon="⎈",
    layout="wide",
)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⎈ K8s Troubleshooter")
    st.caption("AI-powered Kubernetes diagnostics")
    st.divider()

    st.subheader("Target")
    namespace = st.text_input("Namespace", value="default")

    # Fetch pod list only when namespace changes or not yet loaded
    if st.session_state.get("last_namespace") != namespace or "pod_list" not in st.session_state:
        try:
            pod_resp = requests.get(
                f"{API_URL}/pods", params={"namespace": namespace}, headers=_HEADERS, timeout=5
            )
            if pod_resp.ok:
                st.session_state.pod_list = pod_resp.json().get("pods", [])
                st.session_state.pod_list_error = None
            else:
                st.session_state.pod_list = []
                st.session_state.pod_list_error = (
                    f"Failed to fetch pods: {pod_resp.status_code} {pod_resp.text}"
                )
        except Exception as e:
            st.session_state.pod_list = []
            st.session_state.pod_list_error = str(e)
        st.session_state.last_namespace = namespace

    pod_list = st.session_state.pod_list
    if st.session_state.get("pod_list_error"):
        st.warning(st.session_state.pod_list_error, icon="⚠️")
    pod_options = ["All"] + pod_list

    # Set default to All on initial load
    if "selected_pod" not in st.session_state:
        st.session_state.selected_pod = "All"

    st.selectbox("Select Pod", options=pod_options, key="selected_pod")

    st.divider()

    # Connection status
    try:
        requests.get(f"{API_URL}/docs", headers=_HEADERS, timeout=2)
        st.success("Agent online", icon="🟢")
    except requests.RequestException:
        st.error("Agent offline", icon="🔴")
        st.caption(f"Expected at {API_URL}")

    st.divider()

    st.subheader("Session History")
    if "messages" in st.session_state and st.session_state.messages:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                label = msg["content"][:45] + "…" if len(msg["content"]) > 45 else msg["content"]
                st.caption(f"• {label}")
    else:
        st.caption("No messages yet.")

    st.divider()
    if st.button("🗑 Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ── Main ─────────────────────────────────────────────────────────────────────
st.header("Kubernetes Diagnostic Agent")

_pod = st.session_state.get("selected_pod", "All")
pod_name = _pod if _pod != "All" else ""

# Notify in chat when pod selection changes
if st.session_state.get("last_selected_pod") != _pod:
    if "last_selected_pod" in st.session_state:
        label = f"pod **{_pod}**" if pod_name else "**all pods**"
        st.session_state.messages.append(
            {"role": "notification", "content": f"Switched to {label}"}
        )
        st.session_state.pop(f"context_sent_{_pod}", None)
    st.session_state.last_selected_pod = _pod

if pod_name:
    st.info(f"Diagnosing pod **{pod_name}** in namespace **{namespace}**", icon="🎯")
else:
    st.info(
        "Enter a pod name in the sidebar to enable pre-analysis, or ask a general question below.",
        icon="💡",
    )

# Init chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render chat history
for msg in st.session_state.messages:
    if msg["role"] == "notification":
        st.info(msg["content"])
    else:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Describe the issue or ask a question…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Diagnosing…"):
            try:
                context_sent_key = f"context_sent_{_pod}"
                include_context = not st.session_state.get(context_sent_key, False)
                payload = {"message": prompt, "include_context": include_context}
                if pod_name:
                    payload["pod_name"] = pod_name
                st.session_state[context_sent_key] = True
                resp = requests.post(f"{API_URL}/chat", json=payload, headers=_HEADERS, timeout=60)
                resp.raise_for_status()
                data = resp.json()
                summary = data.get("summary", "")
                answer = data.get("response", "")
            except requests.ConnectionError:
                summary = ""
                answer = "Could not reach the agent. Make sure the FastAPI server is running."
            except requests.HTTPError as e:
                summary = ""
                answer = f"Agent returned an error: {e}"
            except Exception as e:
                summary = ""
                answer = f"Unexpected error: {e}"

        st.markdown(summary)
        with st.expander("Full response"):
            st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
