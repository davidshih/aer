# Internal Mini-MSR Review Details

| Field | Value |
|---|---|
| Platform | Power Platform |
| Estimated Tier | Tier 2 — Medium Risk |
| Decision | Approved with Conditions |
| Progress | 8/44 reviewed (18%) |
| Attention Items | 1 |
| Reviewer Notes |  |

## Control Results

| # | Group | Control | Required | Severity | Status | Details |
|---:|---|---|---|---|---|---|
| 1 | Data Access & Classification | Data Classification | Required | High | Partial | Data sources: FIS daily report email attachment; Classification: financial data; Regulated data type: N/A |
| 2 | Data Access & Classification | Data Source Inventory | Required | High | Pass | Source systems: FIS daily report email attachment; Destination systems: on-prem EDW database; Intermediate storage: N/A; Owner: sv-official-check-recon-prod |
| 3 | Data Access & Classification | Least-Privilege Data Access | Required | High | Pass | Data source: download email; Access type: powerplatform connector; Role / group: EDW-prod-file AD Group; Justification: service account with pre assigned access  |
| 4 | Data Access & Classification | Production Write / Delete / Approval Capability | Required | Critical | Pass | Write actions: delegated permission on the service account; Delete actions: N/A; Approval actions: N/A; Rollback method: N/A; Business owner approval: CHGxxxxx |
| 5 | Data Access & Classification | Sensitive Data in Logs / Run History | Required | High | N/A | Log source: power automate log; Sensitive fields checked: N/A; Redaction method: N/A; Sample reviewed: N/A |
| 6 | Data Access & Classification | Data Retention and Cleanup | Required | Medium | N/A |  |
| 7 | Data Access & Classification | Data Export / Download / File Transfer Control | Required | High | Pass | Export method: power automate file connector; Destination: EDW file; Triggering user/identity: sv-xxxxx; Data type: csv recordss |
| 8 | Data Access & Classification | Cross-Environment Data Movement | Required | High | N/A | Source environment: power platform - AB-prod; Destination environment: power platform - AB-prod |
| 9 | Identity & Authorization | Owner and Support Model | Required | Medium | Not Reviewed |  |
| 10 | Identity & Authorization | User Access Scope | Required | High | Not Reviewed |  |
| 11 | Identity & Authorization | Privileged Owner / Admin / Co-owner Access | Required | High | Not Reviewed |  |
| 12 | Identity & Authorization | Service Account / Robot Account / Execution Role | Required | High | Not Reviewed |  |
| 13 | Identity & Authorization | External User / Guest Access Review | Required | Critical | Not Reviewed |  |
| 14 | Identity & Authorization | Access Removal / Joiner-Mover-Leaver Process | Required | Medium | Not Reviewed |  |
| 15 | Secrets & Credential Management | No Hardcoded Secrets | Required | Critical | Not Reviewed |  |
| 16 | Secrets & Credential Management | Approved Secret Store | Required | High | Not Reviewed |  |
| 17 | Secrets & Credential Management | Credential Rotation | Required | High | Not Reviewed |  |
| 18 | Secrets & Credential Management | Secret Exposure in Logs / Screenshots / Run History | Required | High | Not Reviewed |  |
| 19 | API / Connector / Integration | Integration Inventory | Required | High | Not Reviewed |  |
| 20 | API / Connector / Integration | External Endpoint Approval | Required | High | Not Reviewed |  |
| 21 | API / Connector / Integration | Authentication Method and Permission Scope | Required | High | Not Reviewed |  |
| 22 | API / Connector / Integration | External Data Transfer Minimization | Required | Critical | Not Reviewed |  |
| 23 | API / Connector / Integration | Retry / Rate Limit / Duplicate Handling | Required | Medium | Not Reviewed |  |
| 24 | SDLC / Change Management | Source Control | Required | High | Not Reviewed |  |
| 25 | SDLC / Change Management | DEV / TEST / PROD Separation | Required | High | Not Reviewed |  |
| 26 | SDLC / Change Management | Peer Review / Pull Request / Change Ticket | Required | High | Not Reviewed |  |
| 27 | SDLC / Change Management | Security Scan Evidence | Required | Medium | Not Reviewed |  |
| 28 | SDLC / Change Management | Rollback / Disable / Kill Switch | Required | Medium | Not Reviewed |  |
| 29 | SDLC / Change Management | Material Change Re-review Trigger | Required | Medium | Not Reviewed |  |
| 30 | Logging / Monitoring / Response | Audit Trail Availability | Required | High | Not Reviewed |  |
| 31 | Logging / Monitoring / Response | Failure Alerting | Required | High | Not Reviewed |  |
| 32 | Logging / Monitoring / Response | Incident Contact and Runbook | Required | Medium | Not Reviewed |  |
| 33 | Logging / Monitoring / Response | Business Reconciliation / Output Validation | Required | Medium | Not Reviewed |  |
| 34 | Power Platform Environment & DLP | Environment Identification | Required | High | Not Reviewed |  |
| 35 | Power Platform Environment & DLP | DLP Policy Applied | Required | High | Not Reviewed |  |
| 36 | Power Platform Environment & DLP | Business / Non-Business / Blocked Connector Review | Required | High | Not Reviewed |  |
| 37 | Power Platform Environment & DLP | HTTP / Custom / Premium Connector Review | Required | Critical | Not Reviewed |  |
| 38 | Power Platform Environment & DLP | Default Environment Production Use | Required | High | Not Reviewed |  |
| 39 | Power Apps / Flows / Agents | App / Flow / Agent Ownership | Required | Medium | Not Reviewed |  |
| 40 | Power Apps / Flows / Agents | Sharing Scope and Co-owner Review | Required | High | Not Reviewed |  |
| 41 | Power Apps / Flows / Agents | Flow Trigger Type | Required | High | Not Reviewed |  |
| 42 | Power Apps / Flows / Agents | Power Automate Run History Data Exposure | Required | High | Not Reviewed |  |
| 43 | Power Apps / Flows / Agents | Copilot Studio Knowledge Sources | Required | High | Not Reviewed |  |
| 44 | Power Apps / Flows / Agents | Copilot Studio Actions / Plugins | Required | Critical | Not Reviewed |  |