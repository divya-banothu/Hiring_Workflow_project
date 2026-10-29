# Data Dictionary — HiringFlow

All dates use ISO `YYYY-MM-DD`; times use 24-hour `HH:MM`; compensation is INR per year. `example.test` email addresses are synthetic. IDs are deterministic and immutable within a generated dataset.

| Entity/table | Primary key | Important fields and validation | Relationships / cardinality |
|---|---|---|---|
| HiringManager | `manager_id` | `email` unique; `active` boolean; department from synthetic department list | One manager can own many requisitions (1:N) |
| Requisition | `requisition_id` | approved status for generated baseline; close date after opening; `salary_min_inr <= salary_max_inr`; headcount > 0 | Many requisitions belong to one manager (N:1); one requisition has many skills, applications, and panels |
| Candidate | `candidate_id` | unique email; experience >= 0; synthetic source and location | One candidate can submit many applications (1:N) |
| Application | `application_id` | unique candidate/requisition pair; stage from documented lifecycle values; `issue_type` marks labelled exceptions | Many applications link to one candidate and one requisition (N:1 each) |
| SkillRequirement | `skill_requirement_id` | skill name required; minimum level 1–5; mandatory boolean | One requisition has many requirements (1:N) |
| Interviewer | `interviewer_id` | synthetic identity; active boolean | One interviewer can have many availability slots, interviews, and scorecards (1:N) |
| InterviewPanel | `panel_id` | type: Technical, Manager, Cross-functional | One requisition can have multiple panels (1:N); each interview links to one panel |
| Availability | `availability_id` | interviewer, date, start/end time, timezone; intended as availability slot | Many slots belong to one interviewer (N:1) |
| Interview | `interview_id` | status: COMPLETED, SCHEDULED, RESCHEDULED, CANCELLED; start before end; `issue_type` for exceptions | Many interviews can belong to one application; each interview references one panel and interviewer |
| Scorecard | `scorecard_id` | four rubric scores from 1–5; overall score is the arithmetic mean; criteria must be role-relevant | An interview may have zero or more scorecards (1:N) |
| Offer | `offer_id` | proposed salary, copied band limits, status; proposed salary should be within band | An application may have an offer; each offer has approval record(s) (1:N) |
| Approval | `approval_id` | decision and comments; approval must be traceable to offer and approver | Many approval records may relate to one offer (N:1) |
| ApplicationStageHistory | `event_id` | append-only event; from/to stage, date, actor, reason | One application has many history events (1:N) |
| GroundTruth | `case_id` | anomaly type, affected entity ID, expected decision, rule, severity | Evaluation-only labels; deliberately separate from operational features |

## Lifecycle rules

- Application stages: `APPLIED → SCREENING → TECHNICAL → FINAL → OFFER → HIRED`; `REJECTED` and `WITHDRAWN` are terminal outcomes.
- Stage movement should be supported by required prior reviews. A technical-stage application without a completed screening review is an exception.
- Active interviews should not overlap for the same interviewer.
- Withdrawn applications should not retain scheduled/rescheduled interviews.
- Offer amounts outside the requisition compensation band require rejection or escalation, never silent approval.
- Scorecards use job-related criteria only. Overall score is calculated from rubric values, not generated independently.
- Application stage history records transitions separately from the current application state.

## Ground-truth edge cases

| Case | Issue | Expected action | Severity |
|---|---|---|---|
| GT-001 | Candidate advanced without required review | Flag for review | High |
| GT-002 | Interviewer double-booked | Block or reschedule | High |
| GT-003 | Offer exceeds approved band | Reject or escalate | High |
| GT-004 | Withdrawn candidate still scheduled | Cancel interview | Medium |
| GT-005 | Irrelevant evaluation criterion | Remove criterion and review | Medium |

## Field-level definitions

`Required` means every generated row has a non-null value unless explicitly marked optional. Types are logical types before CSV serialization.

| Table | Field | Type | Required / uniqueness | Allowed values or validation |
|---|---|---|---|---|
| hiring_managers | manager_id | string | Required, PK | `MGR-` plus zero-padded counter |
| hiring_managers | manager_name | string | Required | Synthetic first and last name |
| hiring_managers | email | string | Required, unique | `managerN@example.test` |
| hiring_managers | department | string | Required | Synthetic department list |
| hiring_managers | active | boolean | Required | true/false |
| requisitions | requisition_id | string | Required, PK | `REQ-2026-` plus six-digit counter |
| requisitions | title | string | Required | One of the documented synthetic role titles |
| requisitions | department | string | Required | Synthetic department list |
| requisitions | location | string | Required | Hyderabad, Bengaluru, Pune, Chennai, Mumbai, Remote |
| requisitions | hiring_manager_id | string | Required, FK | Must exist in hiring_managers.manager_id |
| requisitions | status | string | Required | Baseline generated as APPROVED |
| requisitions | opened_date / target_close_date | date string | Required | ISO dates; target close date must not precede opening |
| requisitions | salary_min_inr / salary_max_inr | integer | Required | Annual INR; minimum must be <= maximum |
| requisitions | headcount | integer | Required | Positive integer |
| candidates | candidate_id | string | Required, PK | `CAND-` plus six-digit counter |
| candidates | full_name | string | Required | Synthetic name |
| candidates | email | string | Required, unique | `candidateN@example.test` |
| candidates | experience_years | decimal | Required | Non-negative years |
| candidates | current_location | string | Required | Synthetic location list |
| candidates | profile_created_date | date string | Required | ISO date |
| candidates | source | string | Required | Referral, Careers Site, Recruiter, Job Board, Campus |
| candidates | consent_recorded | boolean | Required | true/false; generated as true |
| skill_requirements | skill_requirement_id | string | Required, PK | `SKILL-<requisition-counter>-<rank>` |
| skill_requirements | requisition_id | string | Required, FK | Existing requisition |
| skill_requirements | skill_name | string | Required | Role-specific skills from SKILLS_BY_ROLE |
| skill_requirements | minimum_level | integer | Required | 1–5 |
| skill_requirements | is_mandatory | boolean | Required | true/false |
| applications | application_id | string | Required, PK | `APP-<candidate-id>-<req-id>` |
| applications | candidate_id / requisition_id | string | Required, FK | Must exist in parent tables; pair is unique |
| applications | applied_date / last_updated_date | date string | Required | ISO dates; update date generated after applied date |
| applications | current_stage | string | Required | APPLIED, SCREENING, TECHNICAL, FINAL, OFFER, HIRED, REJECTED, WITHDRAWN |
| applications | status | string | Required | ACTIVE or terminal status REJECTED/WITHDRAWN/HIRED |
| applications | issue_type | string | Required | NONE or documented anomaly type |
| interviewers | interviewer_id | string | Required, PK | `INTV-` plus six-digit counter |
| interviewers | full_name | string | Required | Synthetic name |
| interviewers | department | string | Required | Synthetic department list |
| interviewers | active | boolean | Required | true/false |
| interview_panels | panel_id | string | Required, PK | `PANEL-` plus six-digit counter |
| interview_panels | requisition_id | string | Required, FK | Existing requisition |
| interview_panels | panel_name | string | Required | Human-readable panel label |
| interview_panels | panel_type | string | Required | Technical, Manager, Cross-functional |
| interview_panels | active | boolean | Required | true/false |
| availability | availability_id | string | Required, PK | `AVL-` plus seven-digit counter |
| availability | interviewer_id | string | Required, FK | Existing interviewer |
| availability | available_date | date string | Required | ISO date |
| availability | start_time / end_time | time string | Required | 24-hour time; end must follow start |
| availability | timezone | string | Required | IANA-style timezone label; generated as Asia/Kolkata |
| interviews | interview_id | string | Required, PK | `INT-2026-` plus six-digit counter |
| interviews | application_id / panel_id / interviewer_id | string | Required, FK | Existing application, panel, and interviewer |
| interviews | scheduled_date | date string | Required | ISO date |
| interviews | start_time / end_time | time string | Required | 24-hour time; end follows start |
| interviews | status | string | Required | COMPLETED, SCHEDULED, RESCHEDULED, CANCELLED |
| interviews | rescheduled_from_interview_id | string | Optional | Prior interview ID when rescheduling; otherwise null |
| interviews | issue_type | string | Required | NONE or documented anomaly type |
| scorecards | scorecard_id | string | Required, PK | `SCORE-<interview-id>-<reviewer-id>` |
| scorecards | interview_id / reviewer_id | string | Required, FK | Existing interview and interviewer |
| scorecards | role_relevant_criteria | string | Required | Pipe-delimited rubric; only job-related criteria allowed |
| scorecards | four rubric score fields | integer | Required | Each score from 1–5 |
| scorecards | overall_score | decimal | Required, derived | Arithmetic mean of four rubric scores, rounded to 2 decimals |
| scorecards | submitted | boolean | Required | true/false |
| scorecards | submitted_date | date string | Required | ISO date |
| scorecards | issue_type | string | Required | NONE or documented anomaly type |
| offers | offer_id | string | Required, PK | `OFF-2026-` plus six-digit counter |
| offers | application_id | string | Required, FK | Existing application |
| offers | proposed_salary_inr / salary_min_inr / salary_max_inr | integer | Required | Annual INR; proposed salary should fall within min/max band |
| offers | offer_status | string | Required | DRAFT, PENDING_APPROVAL, APPROVED, DECLINED |
| offers | created_date | date string | Required | ISO date |
| offers | issue_type | string | Required | NONE or documented anomaly type |
| approvals | approval_id | string | Required, PK | `APR-` plus six-digit counter |
| approvals | offer_id | string | Required, FK | Existing offer |
| approvals | approver_id | string | Required, FK | Existing hiring manager |
| approvals | decision | string | Required | APPROVED or REJECTED in generated data |
| approvals | decision_date | date string | Required | ISO date |
| approvals | comments | string | Required | Explanation for decision |
| application_stage_history | event_id | string | Required, PK | `EVT-` plus eight-digit counter |
| application_stage_history | application_id | string | Required, FK | Existing application |
| application_stage_history | from_stage | string | Optional | Null for first event; otherwise previous stage |
| application_stage_history | to_stage | string | Required | Documented lifecycle stage |
| application_stage_history | event_date | date string | Required | ISO date |
| application_stage_history | actor_type | string | Required | SYSTEM or RECRUITER in generated data |
| application_stage_history | reason | string | Required | Short event explanation |
| ground_truth | case_id | string | Required, PK | GT-001 through GT-005 in current generator |
| ground_truth | entity_type / entity_id | string | Required | Type and ID of affected record |
| ground_truth | issue_type | string | Required | One of the five documented exception types |
| ground_truth | expected_decision | string | Required | Rule-derived expected action |
| ground_truth | rule | string | Required | Human-readable rule explanation |
| ground_truth | severity | string | Required | HIGH or MEDIUM |

## Important implementation distinction

The generator creates synthetic records and injects five intentional, labelled exceptions for evaluation. The validation report separates structural validation failures from expected business-rule findings. The stage-gate validation is intentionally a prototype heuristic; a production implementation should model review records and transition prerequisites explicitly and validate each transition against those records.
