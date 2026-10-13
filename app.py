"""Streamlit UI for the AI Opportunity Intake Assistant.

    pip install -r requirements.txt
    streamlit run app.py
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from intake_assistant import UseCaseInput, assess, rank_portfolio
from intake_assistant.llm import grounded_answer, llm_available
from intake_assistant.phi_guard import redact
from intake_assistant.report import intake_brief
from intake_assistant.retrieval import BM25Index, load_chunks

ROOT = Path(__file__).parent
SAMPLES = json.loads((ROOT / "data" / "sample_use_cases.json").read_text())

st.set_page_config(page_title="AI Opportunity Intake Assistant", page_icon="🩺", layout="wide")
st.title("🩺 AI Opportunity Intake Assistant")
st.caption("Healthcare provider & claims workflows · discovery → scored use case → responsible AI review")
st.sidebar.markdown(f"**LLM narrative:** {'🟢 Claude API' if llm_available() else '⚪ offline templates'}")
st.sidebar.info("Demo uses synthetic data only. Never paste real PHI.")

tab_intake, tab_portfolio, tab_kb, tab_redact = st.tabs(
    ["📝 New intake", "📊 Portfolio", "📚 Policy Q&A (RAG)", "🔒 PHI redaction"]
)

with tab_intake:
    pick = st.selectbox("Start from a sample", ["(blank)"] + [s["title"] for s in SAMPLES])
    base = next((s for s in SAMPLES if s["title"] == pick), {})
    with st.form("intake"):
        c1, c2 = st.columns(2)
        title = c1.text_input("Opportunity title", base.get("title", ""))
        area = c2.text_input("Business area", base.get("business_area", ""))
        problem = st.text_area("Problem statement (stakeholder's words)", base.get("problem_statement", ""))
        current = st.text_area("Current process", base.get("current_process", ""))
        outcome = st.text_area("Desired outcome", base.get("desired_outcome", ""))
        c3, c4, c5 = st.columns(3)
        volume = c3.number_input("Monthly volume", 0, 10_000_000, base.get("monthly_volume", 0))
        minutes = c4.number_input("Minutes per item", 0.0, 600.0, float(base.get("minutes_per_item", 0)))
        sponsor = c5.text_input("Sponsor", base.get("sponsor", ""))
        sources = st.text_input("Data sources (comma-separated)", ", ".join(base.get("data_sources", [])))
        stakeholders = st.text_input("Stakeholder groups (comma-separated)", ", ".join(base.get("stakeholders", [])))
        c6, c7, c8 = st.columns(3)
        structured = c6.selectbox("Data structured?", ["Unknown", "Yes", "No"],
                                  index={None: 0, True: 1, False: 2}[base.get("data_is_structured")])
        phi = c7.checkbox("Involves PHI", base.get("involves_phi", True))
        impact = c8.checkbox("Affects member/provider decision", base.get("decision_impacts_member_or_provider", False))
        submitted = st.form_submit_button("Assess opportunity", type="primary")

    if submitted and title and problem:
        uc = UseCaseInput(
            title=title, business_area=area, problem_statement=problem, current_process=current,
            desired_outcome=outcome, monthly_volume=int(volume), minutes_per_item=minutes,
            data_sources=[s.strip() for s in sources.split(",") if s.strip()],
            data_is_structured={"Unknown": None, "Yes": True, "No": False}[structured],
            involves_phi=phi, decision_impacts_member_or_provider=impact,
            stakeholders=[s.strip() for s in stakeholders.split(",") if s.strip()], sponsor=sponsor,
        )
        with st.spinner("Assessing…"):
            a = assess(uc)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Priority", f"{a.priority_score}/100")
        m2.metric("Quadrant", a.quadrant)
        m3.metric("Hrs saved / month", f"{a.estimated_hours_saved_per_month:,.0f}")
        m4.metric("FTE equivalent", a.estimated_fte_equivalent)
        if any(f.escalate for f in a.responsible_ai_flags):
            st.warning("⚠️ Escalate to AI governance before build — see Responsible AI review.")
        brief = intake_brief(a)
        st.markdown(brief)
        st.download_button("Download intake brief (.md)", brief, file_name=f"{title}.md")

with tab_portfolio:
    results = rank_portfolio([UseCaseInput(**s) for s in SAMPLES])
    df = pd.DataFrame([{
        "Opportunity": r.use_case.title, "Domain": r.workflow_domain, "Priority": r.priority_score,
        "Quadrant": r.quadrant, "Hrs/mo": r.estimated_hours_saved_per_month,
        "Value": r.score("Business Value"),
        "Ease": (r.score("Feasibility") + r.score("Data Readiness")) / 2,
        "Risk": r.score("Risk"),
    } for r in results])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.subheader("Value vs. ease (bubble = hours saved)")
    st.scatter_chart(df, x="Ease", y="Value", size="Hrs/mo", color="Quadrant")

with tab_kb:
    st.write("Ask the sample responsible-AI playbook and claims glossary. Answers cite their source.")
    q = st.text_input("Question", "Can AI deny a prior authorization on its own?")
    if q:
        hits = BM25Index(load_chunks(ROOT / "data" / "knowledge_base")).search(q)
        st.markdown(grounded_answer(q, hits))
        with st.expander("Retrieved passages"):
            for h in hits:
                st.markdown(f"**{h.chunk.source} › {h.chunk.heading}** (score {h.score})\n\n{h.chunk.text}")

with tab_redact:
    txt = st.text_area("Text", "Provider NPI 1234567893 called about Medicaid ID: GA12345678, DOB 04/12/1980, from 512-555-0100.")
    res = redact(txt)
    st.code(res.text)
    st.json(res.counts)
