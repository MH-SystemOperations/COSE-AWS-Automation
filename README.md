# COSE AWS Automation

**Cloud Ops & Systems Engineering** - Org-level AWS automation and governance

## Purpose

Automated guardrails for AWS resource lifecycle management. Built on COSE governance principles:
- **Guardrails over approvals** - Automated enforcement, not manual reviews
- **Destructibility = Reliability** - Can destroy and recreate deterministically
- **Modular and reusable** - CloudFormation templates for org-wide deployment

## Structure

Resources organized by AWS service (not by purpose):

```
workspaces/          # All WorkSpaces automation
  └── lifecycle/     # Automated unused WorkSpace detection and deletion
cloudwatch/          # (Future) CloudWatch automation
ec2/                 # (Future) EC2 automation
```

Folders emerge as automations are built - no pre-created scaffolding.

## Principles

**Safety first:**
- DRY_RUN mode by default
- Multiple verification checks
- Audit trails in DynamoDB
- Backup images before deletion

**CloudFormation preferred:**
- Free (no state management)
- StackSets for org-level deployment
- Cross-account IAM roles
- AWS-native

**Terraform when needed:**
- Account-specific infrastructure
- When cross-team collaboration requires it

## Repository Conventions

- **Branch strategy:** `main` branch (protected)
- **Naming:** kebab-case for files/folders
- **Testing:** Dry-run mode + progressive rollout before production
- **Documentation:** Each automation has its own README

## Current Automations

### WorkSpaces Lifecycle Management
**Path:** `/workspaces/lifecycle/`  
**Purpose:** Automatically detect and delete unused WorkSpaces after 90 days zero usage  
**Status:** In development

- Scans all accounts weekly
- Sends warning emails (14-day notice)
- Re-verifies usage before deletion
- Creates backup images (90-day retention)
- DynamoDB audit trail

**Savings:** Prevents $1,500-2,000/mo waste from forgotten WorkSpaces

## Getting Started

Each automation includes:
- CloudFormation templates in `/cfn`
- Lambda code in `/lambda`
- Testing instructions in README
- Deployment guide

Start with dry-run mode, test in single account, then roll out org-wide.

## Contributing

Follow COSE Platform Governance Principles:
1. Guardrails over approvals
2. Automation over manual process
3. Modular and reusable
4. Test-driven (dry-run first)
5. Simple and obvious

See: `CloudOps/Gov Principles R0.md` for full principles.

## Ownership

**Team:** Cloud Ops & Systems Engineering (COSE)  
**Repo:** https://github.com/MH-SystemOperations/COSE-AWS-Automation
