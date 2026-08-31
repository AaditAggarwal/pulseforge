# AWS_COST_CONTROL

Spend guardrails, kill switches, and an honest record of anything ever left running.

## Status

No resources exist, no spend has occurred, no billing alarm is configured.

## Guardrails required before Phase 11 creates anything

1. Billing alarm at a low threshold. This is the first Terraform resource, before anything else.
2. AWS Budgets monthly budget with an email action.
3. Cost Explorer enabled so daily spend is visible.
4. Verify credit balance and expiry in the Billing console and record the real numbers here.

## The two things most likely to cost real money quietly

- **NAT Gateway** — roughly $32/month plus data processing, billed whether or not traffic flows.
  If a NAT Gateway ever appears in a `terraform plan`, it gets flagged explicitly before apply.
- **Idle load balancers** — roughly $16/month each, billed while idle.

Neither is free tier under any plan. If the architecture appears to need either, that is a design
question first and a cost question second.

## Kill switch

`terraform destroy` in `infra/`, followed by manual console verification that the resources are
actually gone. Terraform state can drift; the console is the source of truth for whether something is
still billing.

## Log of things left running

| Date | Resource | Hours running | Estimated cost | How it was noticed |
|---|---|---|---|---|
| — | — | — | — | — |

This table is filled in honestly, including the embarrassing entries. That is its entire purpose.
