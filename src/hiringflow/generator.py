from __future__ import annotations

import argparse
import hashlib
import json
import random
import sqlite3
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

SEED_DEFAULT = 20261022
ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output"

FIRST_NAMES = ["Aarav", "Aditi", "Akash", "Ananya", "Arjun", "Divya", "Isha", "Kiran", "Meera", "Neha", "Nikhil", "Priya", "Rahul", "Riya", "Sana", "Sanjay", "Sowmya", "Varun", "Vikram", "Zoya"]
LAST_NAMES = ["Rao", "Sharma", "Reddy", "Patel", "Kumar", "Singh", "Gupta", "Nair", "Das", "Joshi", "Iyer", "Verma", "Naidu", "Khan", "Mishra"]
ROLES = ["Software Engineer", "Data Engineer", "Cloud Engineer", "AI Engineer", "DevOps Engineer", "QA Engineer", "Product Analyst", "Technical Support Engineer"]
DEPARTMENTS = ["Engineering", "Data", "Cloud Operations", "AI Platform", "Quality", "Product", "Customer Operations"]
LOCATIONS = ["Hyderabad", "Bengaluru", "Pune", "Chennai", "Mumbai", "Remote"]
SKILLS_BY_ROLE = {
    "Software Engineer": ["Python", "SQL", "REST APIs", "Git", "Testing"],
    "Data Engineer": ["Python", "SQL", "ETL", "Data Modeling", "Cloud"],
    "Cloud Engineer": ["AWS", "Linux", "Networking", "IAM", "Monitoring"],
    "AI Engineer": ["Python", "Machine Learning", "Data Preparation", "APIs", "Evaluation"],
    "DevOps Engineer": ["Linux", "CI/CD", "Docker", "Cloud", "Monitoring"],
    "QA Engineer": ["Test Design", "API Testing", "SQL", "Automation", "Defect Tracking"],
    "Product Analyst": ["SQL", "Metrics", "Communication", "Experiment Design", "Dashboards"],
    "Technical Support Engineer": ["Troubleshooting", "Linux", "Networking", "Documentation", "Communication"],
}
STAGES = ["APPLIED", "SCREENING", "TECHNICAL", "FINAL", "OFFER", "HIRED", "REJECTED", "WITHDRAWN"]
STAGE_ORDER = {"APPLIED": 0, "SCREENING": 1, "TECHNICAL": 2, "FINAL": 3, "OFFER": 4, "HIRED": 5}


def iso_day(value: date) -> str:
    return value.isoformat()


def stable_id(prefix: str, number: int, width: int = 6) -> str:
    return f"{prefix}{number:0{width}d}"


def build_dataset(scale: str = "starter", seed: int = SEED_DEFAULT) -> dict[str, pd.DataFrame]:
    """Create valid source records, derive outcomes, then inject labelled anomalies."""
    rng = random.Random(seed)
    sizes = {"starter": (12, 120, 190, 60), "full": (200, 5000, 8000, 2000)}
    if scale not in sizes:
        raise ValueError("scale must be 'starter' or 'full'")
    n_req, n_candidates, n_apps, n_interviews = sizes[scale]
    base_day = date(2026, 1, 1)

    managers = []
    for i in range(1, max(8, n_req // 4) + 1):
        managers.append({"manager_id": stable_id("MGR-", i), "manager_name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}", "email": f"manager{i}@example.test", "department": rng.choice(DEPARTMENTS), "active": True})

    requisitions = []
    skills = []
    for i in range(1, n_req + 1):
        role = rng.choice(ROLES)
        low = rng.randrange(450000, 1000000, 25000)
        high = low + rng.randrange(150000, 500001, 25000)
        created = base_day + timedelta(days=rng.randrange(0, 180))
        requisitions.append({"requisition_id": f"REQ-2026-{i:06d}", "title": role, "department": rng.choice(DEPARTMENTS), "location": rng.choice(LOCATIONS), "hiring_manager_id": rng.choice(managers)["manager_id"], "status": "APPROVED", "opened_date": iso_day(created), "target_close_date": iso_day(created + timedelta(days=rng.randrange(30, 91))), "salary_min_inr": low, "salary_max_inr": high, "headcount": rng.choice([1, 1, 1, 2, 3])})
        for rank, skill in enumerate(SKILLS_BY_ROLE[role], start=1):
            skills.append({"skill_requirement_id": f"SKILL-{i:06d}-{rank:02d}", "requisition_id": f"REQ-2026-{i:06d}", "skill_name": skill, "minimum_level": rng.choice([2, 3, 3, 4]), "is_mandatory": rank <= 3})

    candidates = []
    for i in range(1, n_candidates + 1):
        candidates.append({"candidate_id": stable_id("CAND-", i), "full_name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}", "email": f"candidate{i}@example.test", "experience_years": round(rng.uniform(0, 14), 1), "current_location": rng.choice(LOCATIONS), "profile_created_date": iso_day(base_day + timedelta(days=rng.randrange(0, 240))), "source": rng.choice(["Referral", "Careers Site", "Recruiter", "Job Board", "Campus"]), "consent_recorded": True})

    # Create application pairs without duplicates; all IDs point to existing parent rows.
    pairs = set()
    applications = []
    max_pairs = n_candidates * n_req
    while len(applications) < n_apps and len(pairs) < max_pairs:
        ci = rng.randrange(1, n_candidates + 1)
        ri = rng.randrange(1, n_req + 1)
        if (ci, ri) in pairs:
            continue
        pairs.add((ci, ri))
        app_id = f"APP-CAND-{ci:06d}-REQ-2026-{ri:06d}"
        applied = base_day + timedelta(days=rng.randrange(0, 240))
        # Most records follow the gate sequence; a few are labelled later as negative cases.
        stage = rng.choices(STAGES, weights=[15, 20, 22, 15, 8, 5, 10, 5])[0]
        applications.append({"application_id": app_id, "candidate_id": stable_id("CAND-", ci), "requisition_id": f"REQ-2026-{ri:06d}", "applied_date": iso_day(applied), "current_stage": stage, "status": "ACTIVE" if stage not in ("REJECTED", "WITHDRAWN", "HIRED") else stage, "last_updated_date": iso_day(applied + timedelta(days=rng.randrange(0, 40))), "issue_type": "NONE"})

    # Interviewers and their availability windows.
    interviewers = []
    for i in range(1, max(15, min(80, n_interviews // 10 + 1)) + 1):
        interviewers.append({"interviewer_id": stable_id("INTV-", i), "full_name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}", "department": rng.choice(DEPARTMENTS), "active": True})
    panels = []
    availability = []
    for i in range(1, max(10, n_req // 2) + 1):
        panel_id = stable_id("PANEL-", i)
        panels.append({"panel_id": panel_id, "requisition_id": f"REQ-2026-{rng.randrange(1, n_req + 1):06d}", "panel_name": f"Hiring Panel {i:03d}", "panel_type": rng.choice(["Technical", "Manager", "Cross-functional"]), "active": True})
        for interviewer in rng.sample(interviewers, k=min(3, len(interviewers))):
            start_hour = rng.choice([9, 10, 11, 13, 14, 15])
            end_hour = start_hour + rng.choice([1, 2])
            availability.append({"availability_id": f"AVL-{len(availability)+1:07d}", "interviewer_id": interviewer["interviewer_id"], "available_date": iso_day(base_day + timedelta(days=rng.randrange(30, 300))), "start_time": f"{start_hour:02d}:00", "end_time": f"{end_hour:02d}:00", "timezone": "Asia/Kolkata"})

    # Create scheduled interviews, avoiding interviewer/time overlaps by construction.
    interviews = []
    assigned_slots = set()
    app_lookup = applications
    for i in range(1, n_interviews + 1):
        app = app_lookup[(i - 1) % len(app_lookup)]
        day = base_day + timedelta(days=30 + (i % 180))
        start_hour = 9 + (i % 8)
        start = f"{start_hour:02d}:00"
        end = f"{start_hour + 1:02d}:00"
        interviewer = interviewers[(i * 7) % len(interviewers)]
        # Find a free interviewer slot deterministically.
        attempt = 0
        while (interviewer["interviewer_id"], iso_day(day), start) in assigned_slots and attempt < 40:
            interviewer = interviewers[(interviewers.index(interviewer) + 1) % len(interviewers)]
            day += timedelta(days=1)
            attempt += 1
        slot_key = (interviewer["interviewer_id"], iso_day(day), start)
        assigned_slots.add(slot_key)
        interviews.append({"interview_id": f"INT-2026-{i:06d}", "application_id": app["application_id"], "panel_id": panels[(i - 1) % len(panels)]["panel_id"], "interviewer_id": interviewer["interviewer_id"], "scheduled_date": iso_day(day), "start_time": start, "end_time": end, "status": rng.choice(["COMPLETED", "COMPLETED", "SCHEDULED", "RESCHEDULED", "CANCELLED"]), "rescheduled_from_interview_id": None, "issue_type": "NONE"})

    # Structured scorecards use role-relevant rubric items, with computed overall score.
    scorecards = []
    rubric = ["Role Knowledge", "Problem Solving", "Communication", "Collaboration"]
    for interview in interviews:
        if interview["status"] != "COMPLETED" and rng.random() < 0.75:
            continue
        reviewer = interview["interviewer_id"]
        scores = [rng.randint(1, 5) for _ in rubric]
        scorecards.append({"scorecard_id": f"SCORE-{interview['interview_id']}-{reviewer}", "interview_id": interview["interview_id"], "reviewer_id": reviewer, "role_relevant_criteria": "|".join(rubric), "role_knowledge_score": scores[0], "problem_solving_score": scores[1], "communication_score": scores[2], "collaboration_score": scores[3], "overall_score": round(sum(scores) / len(scores), 2), "submitted": True, "submitted_date": interview["scheduled_date"]})

    offers = []
    approvals = []
    offer_candidates = [a for a in applications if a["current_stage"] in ("OFFER", "HIRED")]
    for i, app in enumerate(offer_candidates[:max(1, min(len(offer_candidates), n_req))], start=1):
        req = requisitions[int(app["requisition_id"].split("-")[-1]) - 1]
        proposed = rng.randrange(req["salary_min_inr"], req["salary_max_inr"] + 1, 5000)
        offer_id = f"OFF-2026-{i:06d}"
        offers.append({"offer_id": offer_id, "application_id": app["application_id"], "proposed_salary_inr": proposed, "salary_min_inr": req["salary_min_inr"], "salary_max_inr": req["salary_max_inr"], "offer_status": rng.choice(["DRAFT", "PENDING_APPROVAL", "APPROVED", "DECLINED"]), "created_date": app["last_updated_date"], "issue_type": "NONE"})
        approvals.append({"approval_id": f"APR-{i:06d}", "offer_id": offer_id, "approver_id": req["hiring_manager_id"], "decision": "APPROVED" if req["salary_min_inr"] <= proposed <= req["salary_max_inr"] else "REJECTED", "decision_date": app["last_updated_date"], "comments": "Within approved band" if req["salary_min_inr"] <= proposed <= req["salary_max_inr"] else "Outside approved band"})

    # Explicit append-only history for application stage changes.
    stage_history = []
    for app in applications:
        stage_history.append({"event_id": f"EVT-{len(stage_history)+1:08d}", "application_id": app["application_id"], "from_stage": None, "to_stage": "APPLIED", "event_date": app["applied_date"], "actor_type": "SYSTEM", "reason": "Application created"})
        if app["current_stage"] != "APPLIED":
            stage_history.append({"event_id": f"EVT-{len(stage_history)+1:08d}", "application_id": app["application_id"], "from_stage": "APPLIED", "to_stage": app["current_stage"], "event_date": app["last_updated_date"], "actor_type": "RECRUITER", "reason": "Synthetic stage progression"})

    tables = {
        "hiring_managers": pd.DataFrame(managers), "requisitions": pd.DataFrame(requisitions),
        "candidates": pd.DataFrame(candidates), "skill_requirements": pd.DataFrame(skills),
        "applications": pd.DataFrame(applications), "interviewers": pd.DataFrame(interviewers),
        "interview_panels": pd.DataFrame(panels), "availability": pd.DataFrame(availability),
        "interviews": pd.DataFrame(interviews), "scorecards": pd.DataFrame(scorecards),
        "offers": pd.DataFrame(offers), "approvals": pd.DataFrame(approvals),
        "application_stage_history": pd.DataFrame(stage_history),
    }
    inject_edge_cases(tables, seed)
    return tables


def inject_edge_cases(tables: dict[str, pd.DataFrame], seed: int) -> None:
    """Add a small, labelled set of deliberate negative cases without hiding the issue."""
    apps = tables["applications"]
    interviews = tables["interviews"]
    scorecards = tables["scorecards"]
    offers = tables["offers"]
    truth = []

    # 1: candidate advanced to technical stage without a submitted screening review.
    if len(apps):
        idx = apps.index[0]
        apps.loc[idx, "current_stage"] = "TECHNICAL"
        apps.loc[idx, "issue_type"] = "ADVANCED_WITHOUT_REQUIRED_REVIEW"
        truth.append({"case_id": "GT-001", "entity_type": "Application", "entity_id": apps.loc[idx, "application_id"], "issue_type": "ADVANCED_WITHOUT_REQUIRED_REVIEW", "expected_decision": "FLAG_FOR_REVIEW", "rule": "Technical stage requires a completed screening scorecard", "severity": "HIGH"})

    # 2: intentionally duplicate an interviewer slot, preserving the issue label.
    if len(interviews) >= 2:
        interviews.loc[1, "interviewer_id"] = interviews.loc[0, "interviewer_id"]
        interviews.loc[1, "scheduled_date"] = interviews.loc[0, "scheduled_date"]
        interviews.loc[1, "start_time"] = interviews.loc[0, "start_time"]
        interviews.loc[1, "end_time"] = interviews.loc[0, "end_time"]
        interviews.loc[1, "issue_type"] = "INTERVIEWER_DOUBLE_BOOKED"
        truth.append({"case_id": "GT-002", "entity_type": "Interview", "entity_id": interviews.loc[1, "interview_id"], "issue_type": "INTERVIEWER_DOUBLE_BOOKED", "expected_decision": "BLOCK_OR_RESCHEDULE", "rule": "An interviewer cannot attend overlapping interviews", "severity": "HIGH"})

    # 3: offer amount above approved band; it must not be auto-approved.
    if len(offers):
        idx = offers.index[0]
        offers.loc[idx, "proposed_salary_inr"] = int(offers.loc[idx, "salary_max_inr"]) + 100000
        offers.loc[idx, "offer_status"] = "PENDING_APPROVAL"
        offers.loc[idx, "issue_type"] = "OFFER_EXCEEDS_BAND"
        approval_rows = tables["approvals"].index[tables["approvals"]["offer_id"] == offers.loc[idx, "offer_id"]]
        if len(approval_rows):
            tables["approvals"].loc[approval_rows[0], "decision"] = "REJECTED"
            tables["approvals"].loc[approval_rows[0], "comments"] = "Rejected by synthetic rule: proposed salary exceeds approved band"
        truth.append({"case_id": "GT-003", "entity_type": "Offer", "entity_id": offers.loc[idx, "offer_id"], "issue_type": "OFFER_EXCEEDS_BAND", "expected_decision": "REJECT_OR_ESCALATE", "rule": "Proposed salary must be within the requisition's approved range", "severity": "HIGH"})

    # 4: withdrawn application still has a scheduled interview.
    withdrawn = apps.index[apps["current_stage"] == "WITHDRAWN"]
    scheduled = interviews.index[interviews["status"].isin(["SCHEDULED", "RESCHEDULED"])]
    if len(withdrawn) and len(scheduled):
        app_idx, interview_idx = int(withdrawn[0]), int(scheduled[0])
        interviews.loc[interview_idx, "application_id"] = apps.loc[app_idx, "application_id"]
        interviews.loc[interview_idx, "issue_type"] = "WITHDRAWN_CANDIDATE_STILL_SCHEDULED"
        truth.append({"case_id": "GT-004", "entity_type": "Interview", "entity_id": interviews.loc[interview_idx, "interview_id"], "issue_type": "WITHDRAWN_CANDIDATE_STILL_SCHEDULED", "expected_decision": "CANCEL_INTERVIEW", "rule": "Withdrawn applications must not have active scheduled interviews", "severity": "MEDIUM"})

    # 5: irrelevant criterion added to a scorecard.
    if len(scorecards):
        idx = scorecards.index[0]
        scorecards.loc[idx, "role_relevant_criteria"] += "|Favorite_Color"
        scorecards.loc[idx, "issue_type"] = "IRRELEVANT_EVALUATION_CRITERION"
        truth.append({"case_id": "GT-005", "entity_type": "Scorecard", "entity_id": scorecards.loc[idx, "scorecard_id"], "issue_type": "IRRELEVANT_EVALUATION_CRITERION", "expected_decision": "REMOVE_CRITERION_AND_REVIEW", "rule": "Scorecards may use only documented job-related rubric criteria", "severity": "MEDIUM"})

    tables["ground_truth"] = pd.DataFrame(truth, columns=["case_id", "entity_type", "entity_id", "issue_type", "expected_decision", "rule", "severity"])


def validate_dataset(tables: dict[str, pd.DataFrame]) -> list[dict]:
    issues: list[dict] = []
    def check_pk(table: str, column: str) -> None:
        df = tables[table]
        duplicate = df[column].duplicated(keep=False)
        if duplicate.any():
            issues.append({"check": "PRIMARY_KEY_UNIQUENESS", "table": table, "count": int(duplicate.sum()), "status": "FAIL", "details": f"Duplicate values in {column}"})
        else:
            issues.append({"check": "PRIMARY_KEY_UNIQUENESS", "table": table, "count": 0, "status": "PASS", "details": column})
    def check_fk(child: str, column: str, parent: str, parent_col: str) -> None:
        valid = set(tables[parent][parent_col].dropna().astype(str))
        bad = ~tables[child][column].astype(str).isin(valid)
        # Ground-truth anomaly is allowed only for labelled operational issue types, not broken IDs.
        issues.append({"check": "FOREIGN_KEY_INTEGRITY", "table": child, "count": int(bad.sum()), "status": "FAIL" if bad.any() else "PASS", "details": f"{column} -> {parent}.{parent_col}"})

    pk_map = {"hiring_managers":"manager_id", "requisitions":"requisition_id", "candidates":"candidate_id", "skill_requirements":"skill_requirement_id", "applications":"application_id", "interviewers":"interviewer_id", "interview_panels":"panel_id", "availability":"availability_id", "interviews":"interview_id", "scorecards":"scorecard_id", "offers":"offer_id", "approvals":"approval_id", "application_stage_history":"event_id"}
    for table, col in pk_map.items(): check_pk(table, col)
    for args in [
        ("requisitions","hiring_manager_id","hiring_managers","manager_id"),
        ("skill_requirements","requisition_id","requisitions","requisition_id"),
        ("applications","candidate_id","candidates","candidate_id"),
        ("applications","requisition_id","requisitions","requisition_id"),
        ("interview_panels","requisition_id","requisitions","requisition_id"),
        ("availability","interviewer_id","interviewers","interviewer_id"),
        ("interviews","application_id","applications","application_id"),
        ("interviews","panel_id","interview_panels","panel_id"),
        ("interviews","interviewer_id","interviewers","interviewer_id"),
        ("scorecards","interview_id","interviews","interview_id"),
        ("scorecards","reviewer_id","interviewers","interviewer_id"),
        ("offers","application_id","applications","application_id"),
        ("approvals","offer_id","offers","offer_id"),
        ("application_stage_history","application_id","applications","application_id"),
    ]: check_fk(*args)

    req = tables["requisitions"]
    bad_band = req["salary_min_inr"] > req["salary_max_inr"]
    issues.append({"check":"COMPENSATION_BAND_ARITHMETIC", "table":"requisitions", "count":int(bad_band.sum()), "status":"FAIL" if bad_band.any() else "PASS", "details":"salary_min_inr must be <= salary_max_inr"})
    score = tables["scorecards"]
    if len(score):
        expected = ((score["role_knowledge_score"] + score["problem_solving_score"] + score["communication_score"] + score["collaboration_score"]) / 4).round(2)
        mismatch = expected != score["overall_score"]
    else:
        mismatch = pd.Series(dtype=bool)
    issues.append({"check":"SCORE_RECONCILIATION", "table":"scorecards", "count":int(mismatch.sum()), "status":"FAIL" if mismatch.any() else "PASS", "details":"overall_score must equal the mean of four rubric scores"})
    allowed_stages = set(STAGES)
    invalid_stage = ~tables["applications"]["current_stage"].isin(allowed_stages)
    issues.append({"check":"ALLOWED_STAGE_ENUM", "table":"applications", "count":int(invalid_stage.sum()), "status":"FAIL" if invalid_stage.any() else "PASS", "details":"current_stage must be a documented stage"})

    # Deliberate business exceptions are counted separately from structural integrity failures.
    gt = tables.get("ground_truth", pd.DataFrame())
    issues.append({"check":"LABELLED_EDGE_CASE_COVERAGE", "table":"ground_truth", "count":len(gt), "status":"PASS" if len(gt) >= 3 else "WARN", "details":"Known anomalies are stored separately from operational input tables"})

    # Business-rule findings are expected in this challenge because the generator
    # deliberately injects five labelled exception cases after creating valid records.
    app_by_id = tables["applications"].set_index("application_id")
    completed_app_ids = set(tables["interviews"].loc[tables["interviews"]["status"] == "COMPLETED", "application_id"].astype(str))
    gate_rows = tables["applications"].loc[tables["applications"]["current_stage"] == "TECHNICAL"]
    gate_count = sum(1 for app_id in gate_rows["application_id"].astype(str) if app_id not in completed_app_ids)
    issues.append({"check":"STAGE_GATE_EXCEPTIONS", "table":"applications", "count":gate_count, "status":"FLAGGED" if gate_count else "PASS", "details":"Technical-stage applications without a completed prior review need investigation; simplified prototype gate check"})

    active_interviews = tables["interviews"].loc[tables["interviews"]["status"].isin(["SCHEDULED", "RESCHEDULED"])]
    conflicts = active_interviews.duplicated(subset=["interviewer_id", "scheduled_date", "start_time"], keep=False)
    issues.append({"check":"ACTIVE_INTERVIEWER_CONFLICTS", "table":"interviews", "count":int(conflicts.sum()), "status":"FLAGGED" if conflicts.any() else "PASS", "details":"Same interviewer/date/start slot used by multiple active interviews"})

    withdrawn_ids = set(tables["applications"].loc[tables["applications"]["current_stage"] == "WITHDRAWN", "application_id"].astype(str))
    withdrawn_scheduled = active_interviews[active_interviews["application_id"].astype(str).isin(withdrawn_ids)]
    issues.append({"check":"WITHDRAWN_APPLICATION_ACTIVE_INTERVIEWS", "table":"interviews", "count":len(withdrawn_scheduled), "status":"FLAGGED" if len(withdrawn_scheduled) else "PASS", "details":"Withdrawn applications should not have scheduled or rescheduled interviews"})

    offers = tables["offers"]
    out_of_band = (offers["proposed_salary_inr"] < offers["salary_min_inr"]) | (offers["proposed_salary_inr"] > offers["salary_max_inr"])
    issues.append({"check":"OFFERS_OUTSIDE_COMPENSATION_BAND", "table":"offers", "count":int(out_of_band.sum()), "status":"FLAGGED" if out_of_band.any() else "PASS", "details":"Out-of-band offers must be rejected or escalated"})
    irrelevant = tables["scorecards"]["role_relevant_criteria"].astype(str).str.contains("Favorite_Color", regex=False)
    issues.append({"check":"IRRELEVANT_SCORECARD_CRITERIA", "table":"scorecards", "count":int(irrelevant.sum()), "status":"FLAGGED" if irrelevant.any() else "PASS", "details":"Only documented job-related rubric criteria should be used"})
    return issues


def write_outputs(tables: dict[str, pd.DataFrame], output_dir: Path, seed: int, scale: str) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_dir = output_dir / "csv"
    json_dir = output_dir / "json"
    csv_dir.mkdir(exist_ok=True)
    json_dir.mkdir(exist_ok=True)
    for name, df in tables.items():
        df.to_csv(csv_dir / f"{name}.csv", index=False)
        df.to_json(json_dir / f"{name}.json", orient="records", indent=2)

    db_path = output_dir / "hiringflow.sqlite"
    if db_path.exists(): db_path.unlink()
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        for name, df in tables.items():
            df.to_sql(name, conn, if_exists="replace", index=False)
        conn.executescript("""
        CREATE INDEX idx_app_candidate ON applications(candidate_id);
        CREATE INDEX idx_app_requisition ON applications(requisition_id);
        CREATE INDEX idx_interview_date ON interviews(scheduled_date);
        CREATE INDEX idx_interview_interviewer ON interviews(interviewer_id, scheduled_date, start_time);
        CREATE INDEX idx_offer_application ON offers(application_id);
        """)

    validation = validate_dataset(tables)
    validation_df = pd.DataFrame(validation)
    validation_df.to_csv(output_dir / "validation_summary.csv", index=False)
    validation_df.to_json(output_dir / "validation_summary.json", orient="records", indent=2)
    row_counts = {name: int(len(df)) for name, df in tables.items()}
    checksums = {}
    for path in sorted(csv_dir.glob("*.csv")):
        checksums[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {"project":"HiringFlow", "scale":scale, "seed":seed, "generated_at_utc":"intentionally_omitted_for_reproducibility", "row_counts":row_counts, "sha256_csv":checksums, "validation_checks":len(validation), "validation_failures":int((validation_df["status"] == "FAIL").sum()), "notes":"Ground-truth anomaly cases are deliberate. Structural ID and relationship checks should pass."}
    (output_dir / "source_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    write_sql_schema(output_dir / "schema.sql")
    return manifest


def write_sql_schema(path: Path) -> None:
    path.write_text("""-- Logical relational schema for HiringFlow. Export tables are materialized by the generator.
CREATE TABLE hiring_managers (manager_id TEXT PRIMARY KEY, manager_name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, department TEXT NOT NULL, active BOOLEAN NOT NULL);
CREATE TABLE requisitions (requisition_id TEXT PRIMARY KEY, title TEXT NOT NULL, department TEXT NOT NULL, location TEXT NOT NULL, hiring_manager_id TEXT NOT NULL REFERENCES hiring_managers(manager_id), status TEXT NOT NULL CHECK(status IN ('APPROVED','ON_HOLD','CLOSED')), opened_date TEXT NOT NULL, target_close_date TEXT NOT NULL, salary_min_inr INTEGER NOT NULL, salary_max_inr INTEGER NOT NULL, headcount INTEGER NOT NULL CHECK(headcount > 0), CHECK(salary_min_inr <= salary_max_inr));
CREATE TABLE candidates (candidate_id TEXT PRIMARY KEY, full_name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, experience_years REAL NOT NULL CHECK(experience_years >= 0), current_location TEXT NOT NULL, profile_created_date TEXT NOT NULL, source TEXT NOT NULL, consent_recorded BOOLEAN NOT NULL);
CREATE TABLE skill_requirements (skill_requirement_id TEXT PRIMARY KEY, requisition_id TEXT NOT NULL REFERENCES requisitions(requisition_id), skill_name TEXT NOT NULL, minimum_level INTEGER NOT NULL CHECK(minimum_level BETWEEN 1 AND 5), is_mandatory BOOLEAN NOT NULL);
CREATE TABLE applications (application_id TEXT PRIMARY KEY, candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id), requisition_id TEXT NOT NULL REFERENCES requisitions(requisition_id), applied_date TEXT NOT NULL, current_stage TEXT NOT NULL, status TEXT NOT NULL, last_updated_date TEXT NOT NULL, issue_type TEXT NOT NULL DEFAULT 'NONE', UNIQUE(candidate_id, requisition_id));
CREATE TABLE interviewers (interviewer_id TEXT PRIMARY KEY, full_name TEXT NOT NULL, department TEXT NOT NULL, active BOOLEAN NOT NULL);
CREATE TABLE interview_panels (panel_id TEXT PRIMARY KEY, requisition_id TEXT NOT NULL REFERENCES requisitions(requisition_id), panel_name TEXT NOT NULL, panel_type TEXT NOT NULL, active BOOLEAN NOT NULL);
CREATE TABLE availability (availability_id TEXT PRIMARY KEY, interviewer_id TEXT NOT NULL REFERENCES interviewers(interviewer_id), available_date TEXT NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL, timezone TEXT NOT NULL);
CREATE TABLE interviews (interview_id TEXT PRIMARY KEY, application_id TEXT NOT NULL REFERENCES applications(application_id), panel_id TEXT NOT NULL REFERENCES interview_panels(panel_id), interviewer_id TEXT NOT NULL REFERENCES interviewers(interviewer_id), scheduled_date TEXT NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL, status TEXT NOT NULL, rescheduled_from_interview_id TEXT, issue_type TEXT NOT NULL DEFAULT 'NONE');
CREATE TABLE scorecards (scorecard_id TEXT PRIMARY KEY, interview_id TEXT NOT NULL REFERENCES interviews(interview_id), reviewer_id TEXT NOT NULL REFERENCES interviewers(interviewer_id), role_relevant_criteria TEXT NOT NULL, role_knowledge_score INTEGER NOT NULL, problem_solving_score INTEGER NOT NULL, communication_score INTEGER NOT NULL, collaboration_score INTEGER NOT NULL, overall_score REAL NOT NULL, submitted BOOLEAN NOT NULL, submitted_date TEXT NOT NULL, issue_type TEXT NOT NULL DEFAULT 'NONE');
CREATE TABLE offers (offer_id TEXT PRIMARY KEY, application_id TEXT NOT NULL REFERENCES applications(application_id), proposed_salary_inr INTEGER NOT NULL, salary_min_inr INTEGER NOT NULL, salary_max_inr INTEGER NOT NULL, offer_status TEXT NOT NULL, created_date TEXT NOT NULL, issue_type TEXT NOT NULL DEFAULT 'NONE');
CREATE TABLE approvals (approval_id TEXT PRIMARY KEY, offer_id TEXT NOT NULL REFERENCES offers(offer_id), approver_id TEXT NOT NULL REFERENCES hiring_managers(manager_id), decision TEXT NOT NULL, decision_date TEXT NOT NULL, comments TEXT NOT NULL);
CREATE TABLE application_stage_history (event_id TEXT PRIMARY KEY, application_id TEXT NOT NULL REFERENCES applications(application_id), from_stage TEXT, to_stage TEXT NOT NULL, event_date TEXT NOT NULL, actor_type TEXT NOT NULL, reason TEXT NOT NULL);
-- ground_truth is a separate evaluation-only table and must not be used as a model/input feature.
""", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate HiringFlow synthetic hiring data")
    parser.add_argument("--scale", choices=["starter", "full"], default="starter", help="starter for quick local run; full for assignment volumes")
    parser.add_argument("--seed", type=int, default=SEED_DEFAULT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    tables = build_dataset(args.scale, args.seed)
    manifest = write_outputs(tables, args.output, args.seed, args.scale)
    print("\nHiringFlow generation complete")
    print(f"Output folder: {args.output.resolve()}")
    print(f"Seed: {args.seed}")
    print("Row counts:")
    for table, count in manifest["row_counts"].items(): print(f"  {table:28} {count:>7}")
    print(f"Validation failures: {manifest['validation_failures']}")
    print("See validation_summary.csv and source_manifest.json for details.")

if __name__ == "__main__":
    main()
