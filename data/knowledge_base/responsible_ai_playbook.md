# Responsible AI Playbook (sample, illustrative)

This sample playbook is written for this portfolio project. It is not any company's actual policy.

## Human oversight
Every AI suggestion that could affect a member or provider (a claim denial, a payment amount, an enrollment or prior authorization decision) requires human review. The AI recommends; a qualified person decides and documents the reason. Fully automated adverse decisions are not permitted.

## Protected Health Information (PHI)
Only send PHI to AI services covered by a Business Associate Agreement (BAA) and approved by Security and Compliance. Apply the HIPAA minimum necessary standard: include only the data elements the use case actually needs. Redact identifiers from prompts, logs and test data whenever possible.

## Escalation criteria
Escalate to the AI governance council when a use case affects eligibility, payment or medical necessity decisions, uses a new external AI vendor, processes data from more than one state program, or cannot meet the acceptance thresholds during the pilot.

## Accuracy and hallucination controls
Generative answers must be grounded in approved source documents and show citations. When the assistant is not confident or no source matches, it must say it does not know and route to a subject matter expert. Every release is tested against a golden question set with agreed pass thresholds.

## Bias and fairness monitoring
Prioritization and risk models are tested for uneven outcomes across provider type, geography, language and program. Results are reviewed quarterly and after any model or data change.

## Audit logging
Log the input, output, model version, timestamp, user and reviewer action for every AI-assisted decision. Retain logs according to the contract's record retention schedule.

## Pilot and scale gates
Start with one team and a measured baseline. Move to scale only when accuracy, adoption and time-saved targets are met for at least four consecutive weeks and change management, training and support are in place.
