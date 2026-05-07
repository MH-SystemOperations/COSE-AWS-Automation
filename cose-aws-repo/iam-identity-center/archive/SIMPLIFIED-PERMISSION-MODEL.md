# Simplified 4-Tier Permission Model

## High-Level Design

```
MH-Admin       → Full admin, all environments
MH-Security    → Security services, all environments
MH-PowerUser   → Admin-ish, EXCEPT prod + NO networking
MH-Developer   → Read-only prod, full dev/qa/staging
```

---

## Tier 1: MH-Admin

**Who**: VPs, CTO, Platform Leads (2-3 people)  
**Access**: Full `AdministratorAccess` everywhere  
**Restrictions**: None (emergency break-glass)

```yaml
ManagedPolicies:
  - arn:aws:iam::aws:policy/AdministratorAccess
```

**Use case**: "Production is down, need to fix NOW"

---

## Tier 2: MH-Security

**Who**: Security team (1-2 people)  
**Access**: Security services, all environments  
**Restrictions**: Cannot modify compute/networking outside security scope

**Can do**:
- GuardDuty, Security Hub, Config, Inspector, Macie
- Security groups, NACLs, WAF (security remediation)
- IAM access key disable, password reset
- SSM to any instance (forensics)
- CloudTrail, Flow Logs

**Cannot do**:
- Create/delete EC2, RDS, Lambda
- Modify VPC routing, Transit Gateway
- Billing changes

---

## Tier 3: MH-PowerUser

**Who**: Directors, Managers, Team Leads (10-15 people)  
**Access**: Near-admin, EXCEPT production + networking  
**Restrictions**: No prod writes, no VPC/routing changes

**Can do in dev/qa/staging**:
- Create/modify/delete EC2, RDS, Lambda, ECS
- Manage S3, DynamoDB, Secrets Manager
- Deploy applications
- Modify security groups (within reason)
- CloudWatch, Cost Explorer

**Can do in prod**:
- Read everything (debugging)
- Restart services (ECS, Lambda)
- Read logs

**Cannot do**:
- Write to prod resources (S3, RDS, Secrets)
- Terminate prod instances
- Modify VPC: routes, Transit Gateway, VPC peering, NAT Gateways
- Modify networking: Direct Connect, VPN, Internet Gateways

**Tag-based conditions**:
```json
"Condition": {
  "StringNotEquals": {
    "aws:ResourceTag/mh:environment": ["prod", "production"]
  }
}
```

---

## Tier 4: MH-Developer

**Who**: Engineers, Analysts (30-50 people)  
**Access**: Read-only prod, full dev/qa/staging  
**Restrictions**: No prod writes, no resource deletion in any env

**Can do in dev/qa/staging**:
- Develop applications (code, test, deploy)
- Read/write S3, Secrets, Parameters
- Connect to EC2, RDS, run queries
- Invoke Lambda, manage ECS tasks
- Read/write logs

**Can do in prod**:
- Read logs (debugging)
- Read resource metadata (describe, list, get)
- Connect to RDS read-only (if DB permissions allow)

**Cannot do**:
- Write to prod S3
- Modify prod resources
- Delete resources anywhere (even dev)
- Access PHI S3 buckets (even in dev)

---

## Networking Restrictions (PowerUser + Developer)

### What Is "Networking" (Restricted)

**Core network infrastructure**:
- VPC: Routes, route tables, Internet Gateways, NAT Gateways
- Transit Gateway attachments, route tables
- VPC peering connections
- Direct Connect, VPN connections
- VPC endpoints (Interface/Gateway)

**Why restricted**: Breaking routes = outage across multiple applications

### What Is "Security Networking" (Allowed for Security, PowerUser in dev/qa)

**Application-level security**:
- Security groups (allow/deny ports)
- Network ACLs (IP blocking)
- WAF rules

**Why allowed**: Needed for security remediation and app development

### PowerUser Networking Policy

```json
{
  "Sid": "DenyNetworkingInfrastructure",
  "Effect": "Deny",
  "Action": [
    "ec2:CreateRoute",
    "ec2:DeleteRoute",
    "ec2:ReplaceRoute",
    "ec2:CreateRouteTable",
    "ec2:DeleteRouteTable",
    "ec2:CreateInternetGateway",
    "ec2:DeleteInternetGateway",
    "ec2:AttachInternetGateway",
    "ec2:DetachInternetGateway",
    "ec2:CreateNatGateway",
    "ec2:DeleteNatGateway",
    "ec2:CreateTransitGateway*",
    "ec2:DeleteTransitGateway*",
    "ec2:ModifyTransitGateway*",
    "ec2:CreateVpcPeeringConnection",
    "ec2:DeleteVpcPeeringConnection",
    "ec2:AcceptVpcPeeringConnection",
    "ec2:CreateVpnConnection",
    "ec2:DeleteVpnConnection"
  ],
  "Resource": "*"
}
```

---

## Consolidation Summary

**From**: 54 permission sets → **To**: 4 permission sets

| Old | New | Count | Reasoning |
|-----|-----|-------|-----------|
| Administrator, VP* (4) | MH-Admin | 4 → 1 | All need same emergency access |
| SecurityTeam (1) | MH-Security | 1 → 1 | Enhanced, but same role |
| Lead*, Senior*, Dir*, Mgr*, Manager*, Principal* (24) | MH-PowerUser | 24 → 1 | All need elevated dev/qa access |
| All other engineer/analyst roles (16) | MH-Developer | 16 → 1 | Standard development access |
| Contractor*, *Temp (3) | MH-Developer | 3 → 0 | Same as Developer, time-limited |
| Service roles (2) | Keep separate | - | Not human users |
| Special projects (3) | Evaluate case-by-case | - | May consolidate to Developer |

**Result**: **93% reduction** (54 → 4)

---

## Assignment Matrix (Simplified)

```yaml
MH-Admin:
  who: VPs, Platform Leads
  count: 2-3 users
  accounts: all (13)
  restrictions: none

MH-Security:
  who: Security team
  count: 1-2 users
  accounts: all (13)
  restrictions: no compute/networking changes

MH-PowerUser:
  who: Directors, Managers, Team Leads
  count: 10-15 users
  accounts: all (13)
  restrictions:
    - no prod writes (tag-based)
    - no networking infrastructure (policy-based)

MH-Developer:
  who: Engineers, Analysts
  count: 30-50 users
  accounts: all (13)
  restrictions:
    - read-only prod (tag-based)
    - no deletions (policy-based)
```

---

## Decision Points

### Q1: Where does "restart prod service" belong?
- PowerUser can restart (ECS update-service, Lambda restart)
- Developer cannot

### Q2: Who can access prod Secrets Manager?
- Admin: Yes
- Security: Yes (incident response)
- PowerUser: Read-only
- Developer: No

### Q3: Who can manage CloudWatch alarms?
- Admin: Yes
- Security: Yes (create security alerts)
- PowerUser: Yes in dev/qa, read-only prod
- Developer: Yes in dev/qa, read-only prod

### Q4: Who can manage Cost Explorer?
- Admin: Yes
- Security: Read-only (anomaly detection)
- PowerUser: Read-only
- Developer: Read-only
- **Add**: MH-Billing (Finance team)

---

## Final Structure (5 Permission Sets)

```
1. MH-Admin          (2-3 users, all accounts)
2. MH-Security       (1-2 users, all accounts)
3. MH-PowerUser      (10-15 users, all accounts, tag restrictions)
4. MH-Developer      (30-50 users, all accounts, tag restrictions)
5. MH-Billing        (1-2 users, management account only)
```

**93% reduction**: 54 → 5 permission sets
