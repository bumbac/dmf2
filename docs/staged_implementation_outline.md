Staged Implementation Outline

Title: Staged Implementation Outline for Requested Deliverable

Purpose
- Provide a clear, actionable, staged implementation plan for delivering the requested work.

Scope
- Produce a staged plan covering Discover, Design, Execute, Validate, and Deliver.
- Specify deliverables, artifacts, success criteria, estimated time, dependencies, and risks.

Constraints and Assumptions
- Assumes access to project repository and ability to create files under docs/.
- Estimates are high-level and should be refined with stakeholders.

Stages

1) Discover (Goals: clarify requirements and constraints)
- Activities:
  - Review request and any existing artifacts in repo.
  - Gather clarifying questions from stakeholders.
  - Identify dependencies, data inputs, and constraints.
- Outputs / Deliverables:
  - Requirements summary (docs/discover_requirements.md)
  - Clarifying questions list (docs/discover_questions.md)
- Estimated duration: 0.5 - 1 day
- Validation criteria: Stakeholders confirm requirements or answer clarifying questions.

2) Design (Goals: produce a detailed plan and design decisions)
- Activities:
  - Create architecture/approach outline.
  - Define internal milestones, success metrics, and test plan.
  - Select libraries, tools, and tech stack choices if applicable.
- Outputs / Deliverables:
  - Design document (docs/design_doc.md)
  - Implementation checklist and timeline (docs/design_timeline.md)
- Estimated duration: 0.5 - 2 days
- Validation criteria: Design doc approved by a reviewer or stakeholder.

3) Execute (Goals: implement deliverables)
- Activities:
  - Implement features, scripts, and artifacts according to design.
  - Create reproducible artifacts and write tests.
  - Commit changes with clear messages and create release notes.
- Outputs / Deliverables:
  - Implementation files (src/ or scripts/)
  - Unit or integration tests (tests/)
  - Execution README and usage instructions (docs/usage.md)
- Estimated duration: 1 - 5 days (depends on scope)
- Validation criteria: All tests pass locally and artifacts match acceptance criteria.

4) Validate (Goals: verify correctness, quality, and readiness)
- Activities:
  - Run tests and QA checks.
  - Perform reviews and incorporate feedback.
  - Generate final summary and deployment instructions.
- Outputs / Deliverables:
  - Test reports (reports/test_report.md)
  - Review feedback log (docs/review_feedback.md)
  - Final readiness checklist (docs/readiness_checklist.md)
- Estimated duration: 0.5 - 2 days
- Validation criteria: Stakeholders sign off; readiness checklist complete.

5) Deliver (Goals: handoff and archive)
- Activities:
  - Package deliverables and artifacts.
  - Provide final documentation and pointers for maintenance.
  - Archive decisions and rationale.
- Outputs / Deliverables:
  - Delivery bundle (deliverables/)
  - Final artifact summary (docs/final_artifact_summary.md)
- Estimated duration: 0.5 - 1 day
- Validation criteria: Delivery accepted by stakeholder; files available in repo.

Cross-cutting concerns
- Version control: use Git with clear commit messages and tags.
- Documentation: every artifact must include purpose, usage, and owner.
- Testing: include tests where applicable; include instructions to reproduce.
- Communication: track decisions and open questions in docs/ and progress updates.

Risks and Mitigations
- Ambiguous requirements: mitigate via early clarifying questions and sign-off.
- Missing dependencies: identify early in Discover and add to procurement list.
- Time underestimation: add buffer and prioritize minimum viable deliverable.

Deliverable artifacts created by this stage
- docs/staged_implementation_outline.md (this file)

Next actions
1. Stakeholder review: share this outline and collect feedback.
2. Run Discover tasks: create docs/discover_requirements.md and docs/discover_questions.md.
3. Proceed to Design after requirements are confirmed.

Contact / Ownership
- Produced by: execution agent (builder)
- Recommended reviewers: project stakeholder(s) and technical lead
