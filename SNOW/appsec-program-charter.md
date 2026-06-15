# Application Security Program Charter and Production Review Operating Model

> **INTERNAL USE ONLY**  
> Regional Bank - Internal Published Document Draft  
> Version 0.9 Draft | For CISO, Technology, Change Management, Platform Owner, and Risk Review

> **Publication intent**
>
> This document is drafted as a charter and operating model for internal publication. It defines governance expectations, production AppSec review requirements, tiering criteria, and required Information Security approval for CAB. It is not intended to replace detailed platform SOPs, secure coding standards, PCI procedures, change management procedures, or legal/compliance interpretations.

| **Field**          | **Value**                                                                                                                                                             |
|--------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Document owner     | Information Security / Application Security                                                                                                                           |
| Primary audience   | Technology leadership, application owners, platform owners, makers/developers, Change Advisory Board (CAB), Risk, Compliance, Internal Audit                          |
| Approval authority | CISO and Head of Technology, or delegated governance body                                                                                                             |
| Effective date     | [To be assigned upon approval]                                                                                                                                      |
| Review cycle       | At least annually, or upon material changes to technology platforms, regulatory expectations, data classification, risk appetite, or SDLC/change management processes |
| Confidentiality    | Internal Use Only                                                                                                                                                     |

## Table of Contents

- [1. Executive Summary](#1-executive-summary)
- [2. Purpose, Scope, and Applicability](#2-purpose-scope-and-applicability)
- [3. Core Policy Statements](#3-core-policy-statements)
- [4. Governance and Accountability](#4-governance-and-accountability)
- [5. AppSec Review as a Production Gate](#5-appsec-review-as-a-production-gate)
- [6. AppSec Tiering Model](#6-appsec-tiering-model)
- [7. Power Platform Review Model](#7-power-platform-review-model)
- [8. Approved Platform Review Focus](#8-approved-platform-review-focus)
- [9. AppSec Service Catalog](#9-appsec-service-catalog)
- [10. Production Review Workflow](#10-production-review-workflow)
- [11. Findings, Conditions, Exceptions, and Risk Acceptance](#11-findings-conditions-exceptions-and-risk-acceptance)
- [12. Evidence and Records](#12-evidence-and-records)
- [13. Metrics and Reporting](#13-metrics-and-reporting)
- [14. Program Maintenance and Continuous Improvement](#14-program-maintenance-and-continuous-improvement)
- [Appendix A. Minimum Review Requirements by Tier](#appendix-a-minimum-review-requirements-by-tier)
- [Appendix B. AppSec Intake Questions](#appendix-b-appsec-intake-questions)
- [Appendix C. CAB Evidence Checklist](#appendix-c-cab-evidence-checklist)
- [Appendix D. Evidence Matrix](#appendix-d-evidence-matrix)
- [Appendix E. Glossary](#appendix-e-glossary)
- [Appendix F. References](#appendix-f-references)

## 1. Executive Summary

This Application Security Program Charter and Production Review Operating Model defines how the Bank governs application security risk across internally developed applications, platform-based solutions, integrations, workflow automations, and low-code/no-code applications. The document is intended to be internally published and used by Information Security, Technology, platform owners, application owners, makers/developers, Change Management, Risk, Compliance, and Internal Audit.

The Bank is transitioning from traditional on-premises application and data processing patterns toward approved enterprise platforms, including Snowflake on AWS and Microsoft Power Platform. As more production applications, workflows, integrations, and reporting/automation capabilities are built on these platforms, application security review must focus not only on source code, but also on data flows, connectors, platform RBAC, service/non-human identities, environment separation, credentials, encryption, logging, and the production change approval path.

> **Key operating principle**
>
> All production-bound applications, workflows, automations, platform-based solutions, and integrations must undergo AppSec tiering. Information Security approval of the AppSec review is required as part of CAB production approval. An approved platform does not automatically make every solution built on that platform approved for production use.

The model uses three review tiers. Tier 1 is a quick review for self-run, single-user, non-sensitive solutions. Tier 2 is a platform and configuration-focused review for solutions built on approved platforms or shared workflows that may process sensitive data, use external connectors, or rely on platform-specific RBAC and credentials. Tier 3 is a full boundary review for tenant-wide or broadly shared solutions, PCI-impacting data flows, privileged access, non-human identities, complex external connectors, file transfers, secrets, or cross-environment production risks.

## 2. Purpose, Scope, and Applicability

### 2.1 Purpose

- Define the Bank's AppSec governance model and production review expectations.

- Establish AppSec tiering as the starting point for production-bound application, workflow, automation, and integration reviews.

- Require Information Security approval of the AppSec review before CAB production approval.

- Clarify how approved platforms such as Snowflake on AWS and Microsoft Power Platform are reviewed at the application/configuration level.

- Provide a repeatable, risk-based model that can be evidenced for internal audit, regulatory examination, PCI assessment, and management oversight.

### 2.2 In-Scope Solutions

- Internally developed applications, APIs, services, scripts, and integrations used in production or production-like business processes.

- Platform-based applications or data products built on approved enterprise platforms, including Snowflake on AWS and Microsoft Power Platform.

- Power Apps, Power Automate cloud flows, desktop-flow orchestration patterns, custom connectors, HTTP/API/SFTP integrations, and Dataverse-connected solutions.

- Applications, workflows, automations, or reports that process, transmit, transform, store, or expose sensitive data, customer information, nonpublic information, employee information, confidential business information, or PCI data.

- Backend bots, scheduled jobs, service/non-human identities, and automated workflows that perform production actions or move production data.

- Externally developed, outsourced, vendor-built, or SaaS-integrated applications where the Bank configures, operates, integrates, or relies on the solution as part of a business process.

### 2.3 Out of Scope or Limited Scope

- Purely personal productivity files or prototypes that do not process sensitive data, do not connect to production systems, are not broadly shared, and are not used for production business decisions.

- Vendor-managed SaaS capabilities with no Bank-developed configuration, no custom connector, no production data movement, and no material integration may be routed primarily through third-party risk management, but may still require AppSec input if integrated into a critical business process.

- Detailed secure coding rules, platform-specific implementation SOPs, PCI technical procedures, and change-management procedures are maintained separately. This charter defines the governance and review model, not every implementation step.

### 2.4 Relationship to Other Control Processes

The AppSec review does not replace architecture review, technology risk review, data governance review, privacy review, third-party risk review, PCI scope validation, SOX change control, IAM/PAM review, QA/UAT, or CAB. The AppSec review provides a security assessment and approval decision that is required before production CAB approval. When other control processes identify higher risk, the AppSec tier may be escalated.

## 3. Core Policy Statements

| **ID** | **Policy Statement**                                 | **Requirement**                                                                                                                                                                                                           |
|--------|------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| PS-01  | Production AppSec tiering is required                | All production-bound applications, workflows, automations, platform-based solutions, and integrations must undergo AppSec tiering before production deployment or material change.                                        |
| PS-02  | Information Security approval is required for CAB    | Information Security approval of the AppSec review is a required CAB production approval item. CAB must confirm the AppSec approval, approval with conditions, or approved exception/risk acceptance before go-live.      |
| PS-03  | Approved platform does not mean approved application | Solutions built on approved platforms such as Snowflake or Power Platform still require review of data flow, connectors, access, credentials, environment separation, secrets, logging, and applicable regulatory impact. |
| PS-04  | Highest applicable tier governs                      | When multiple tier criteria apply, the highest applicable tier governs unless Information Security documents an approved rationale for a lower tier. PCI-impacting solutions are Tier 3 by default.                       |
| PS-05  | No missing approval by silence                       | A missing, incomplete, or pending AppSec review is not an approval. Production deployment must not proceed without AppSec approval or formal risk acceptance.                                                             |
| PS-06  | Risk acceptance must expire                          | Exceptions and risk acceptances must identify an accountable owner, compensating controls, remediation plan, expiration date, and approval authority appropriate to risk severity.                                        |
| PS-07  | Review evidence must be retained                     | Tiering decisions, review notes, approvals, conditions, exceptions, and supporting evidence must be retained in the designated system of record.                                                                          |

## 4. Governance and Accountability

Application security is a shared responsibility. Information Security owns the AppSec program and approval model; Technology and application/platform owners own the implementation of secure designs and remediation; CAB validates that required approvals are complete before production release.

| **Role / Function**                               | **Accountability**                                                                                                                                                                |
|---------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Board / Risk Committee                            | Receives periodic reporting on material application security risks, program maturity, exceptions, and remediation trends, as appropriate.                                         |
| CISO / Information Security                       | Owns the AppSec Program, review model, standards, and approval authority. Provides independent security challenge and approves, rejects, or conditions production AppSec reviews. |
| AppSec Lead / Program Owner                       | Maintains this charter, defines tiering criteria, coordinates AppSec reviews, documents approval decisions, tracks metrics, and drives continuous improvement.                    |
| AppSec Engineer / Analyst                         | Performs tiering, reviews data flows, connectors, access, secrets, platform configuration, testing evidence, and findings; documents outcomes and required conditions.            |
| Technology / Development Leadership               | Ensures application owners and teams submit production-bound work for review, remediate findings, and do not bypass the AppSec/CAB control path.                                  |
| Application / Product / Business Owner            | Owns the business process, data usage, access model, risk acceptance request, remediation plan, and post-go-live follow-up items.                                                 |
| Platform Owner - Snowflake / AWS / Power Platform | Provides platform configuration evidence, RBAC/role model, environment/DLP controls, logging capability, connector controls, and platform-specific guidance.                      |
| IAM / PAM / Identity Team                         | Reviews privileged access, service accounts, app registrations, non-human identities, credential lifecycle, MFA/PAM requirements, and least-privilege scope.                      |
| Data Owner / Data Governance                      | Confirms data classification, permitted use, data handling requirements, masking/tokenization expectations, retention, and downstream sharing constraints.                        |
| Change Advisory Board (CAB)                       | Verifies AppSec approval status, conditions, and exceptions as part of production change approval. CAB does not replace AppSec review.                                            |
| Third-Party Risk Management                       | Coordinates vendor/SaaS risk assessment, contractual security requirements, assurance artifact review, and periodic reassessment for vendor-managed components.                   |
| Internal Audit / Compliance                       | May review the design and operating effectiveness of the program, evidence retention, and alignment with internal policy/regulatory expectations.                                 |

## 5. AppSec Review as a Production Gate

### 5.1 CAB Requirement

The AppSec review is a required production gate. A CAB production change involving an in-scope application, workflow, automation, platform-based solution, or integration must include AppSec approval evidence. The CAB package should include the AppSec review identifier, assigned tier, approval status, open conditions, exception/risk acceptance identifier if applicable, and the date of Information Security approval.

> **CAB decision rule**
>
> CAB should not approve production deployment for an in-scope solution unless the AppSec review is approved, approved with documented conditions, or covered by a formally approved and unexpired risk acceptance.

### 5.2 When AppSec Review Is Triggered

- New application, workflow, automation, platform-based solution, API, data product, or integration moving to production.

- Material change to data classification, customer/employee data usage, PCI impact, business criticality, sharing scope, or user population.

- New external connector, custom connector, API, SFTP, vendor integration, or data export/import path.

- New or changed service account, non-human identity, app registration, key-pair authentication, privileged account, or PAM-managed access.

- New production credentials, secret store, environment separation model, or change to credential ownership.

- New Snowflake database/schema/view/procedure/task/stream/share/stage/external integration that supports a production application or data flow.

- New Power Platform app/flow/shared automation/custom connector/gateway pattern that supports a production business process.

- CAB reviewer, Information Security, platform owner, data owner, or risk/compliance stakeholder requests AppSec review based on risk indicators.

### 5.3 Approval Outcomes

| **Outcome**                        | **Meaning**                                                                                                                   | **CAB Handling**                                                                                             |
|------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------|
| Approved                           | AppSec review is complete and no blocking conditions remain.                                                                  | CAB may proceed if all other CAB requirements are satisfied.                                                 |
| Approved with Conditions           | AppSec permits production deployment with documented conditions, compensating controls, due dates, or post-go-live follow-up. | CAB may proceed only if conditions are included in the change record and accountable owner is assigned.      |
| Not Approved                       | AppSec review identified unacceptable risk, missing evidence, or blocking findings.                                           | CAB should not approve go-live until issues are resolved or formally accepted by appropriate risk authority. |
| Risk Accepted / Exception Approved | A formal, unexpired exception has been approved by the required authority.                                                    | CAB may proceed only if the exception is attached and scope/expiration match the deployment.                 |

## 6. AppSec Tiering Model

Tiering determines the depth of review required. The goal is to right-size security review effort to actual risk while maintaining a consistent production gate. Tiering is performed by Information Security based on submitted intake information, platform details, data classification, sharing scope, identity model, connector boundary, and regulatory impact.

### 6.1 General Tier Matrix

| **Tier** | **Review Type**                         | **Typical Scenarios**                                                                                                                                                                                                                                                   | **Primary Review Focus**                                                                                                                                                                                                               |
|----------|-----------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Tier 1   | Quick review                            | Self-run or single-user solution; no sensitive or regulated data; no service account; no privileged access; no broad sharing; no external connector; no production data write-back beyond the user's own privilege.                                                     | Confirm low-risk scope, data classification, user-owned access, no broad sharing, no service/non-human identity, no sensitive data, and no external connector or PCI impact.                                                           |
| Tier 2   | Platform / configuration-focused review | Solution built on an approved platform such as Snowflake or Power Platform; shared with a defined user group; backend bot or scheduled automation; sensitive data but no PCI boundary impact; external connector or platform RBAC/credential model requires validation. | Review connectors, RBAC, sharing, credential ownership, service account/non-human identity scope, environment separation, logging, data classification, and platform-specific configuration.                                           |
| Tier 3   | Full AppSec boundary review             | Tenant-wide or broadly shared solution; PCI data or potential CDE impact; privileged account; high-scope non-human identity; complex external connectors; sensitive file transfer; production secrets; cross-environment data movement; critical banking process.       | End-to-end boundary review covering data flow, PCI impact, connector chain, RBAC, PAM validation, non-human identities, least privilege, encryption, environment/secret siloing, logging, testing evidence, and formal risk decisions. |

### 6.2 Tier Escalation Rules

- If multiple criteria apply, the highest applicable tier governs.

- PCI data, suspected PCI scope impact, or file/data movement involving PCI data is Tier 3 by default until scope is validated otherwise.

- Use of privileged accounts, PAM-managed accounts, or administrative roles is Tier 3 unless Information Security documents a lower-risk rationale.

- Use of service accounts, app registrations, machine identities, key-pair authentication, or other non-human identities is at least Tier 2 and may be Tier 3 depending on privileges, data access, and blast radius.

- External connectors, custom connectors, HTTP/SFTP/API integrations, vendor APIs, or data exports involving sensitive data are at least Tier 2 and may be Tier 3.

- Broad sharing, tenant-wide deployment, or material increase in user population may escalate the review tier.

- Information Security may escalate or de-escalate based on documented risk rationale, but PCI-impacting and privileged-access solutions require formal justification for any lower-tier decision.

### 6.3 Examples

| **Example**                                                                                                               | **Likely Tier**  | **Rationale**                                                                                                                                                      |
|---------------------------------------------------------------------------------------------------------------------------|------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Single-user Power Automate reminder using only the user's mailbox and no sensitive data                                   | Tier 1           | Self-run, user-owned access, no sensitive data, no service account, no broad sharing.                                                                              |
| Power Automate flow shared with a department and using an approved connector to process customer operational data         | Tier 2           | Shared workflow with sensitive data and connector/RBAC review needs.                                                                                               |
| Power App used by 20 users to submit account-related requests into Snowflake                                              | Tier 2 or Tier 3 | At least Tier 2 due to sharing and platform integration; Tier 3 if regulated/PCI data, privileged identity, external connector, or critical process impact exists. |
| Snowflake-backed data product using service account/key-pair authentication and external SFTP file transfer with PCI data | Tier 3           | PCI impact, non-human identity, external transfer, file encryption, secret isolation, and end-to-end boundary review required.                                     |
| Tenant-wide app registration with broad Microsoft Graph permissions                                                       | Tier 3           | Tenant-wide blast radius and high-scope non-human identity.                                                                                                        |

## 7. Power Platform Review Model

Power Platform solutions are subject to the general tiering model, with additional attention to environment strategy, DLP policy, connectors, connection ownership, solution deployment, sharing scope, service account usage, and gateway/API integration. A maker-friendly platform does not remove the need for production governance when a flow or app becomes a business process.

| **Power Platform Tier**              | **Scenario**                                                                                                                                                                                                                               | **Required Review Focus**                                                                                                                                                                                   |
|--------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Tier 1 - Single-user quick review    | Single-user flow or app; no service account; user operates under their own access privilege; no sensitive or regulated data; no broad sharing; no external/custom connector.                                                               | Confirm user-owned connection, no sensitive data, no service/non-human identity, no business-critical dependency, no broad sharing, and no PCI impact.                                                      |
| Tier 2 - Shared/configuration review | Shared flow or app; approximately 10 or more users or a defined group; sensitive data; backend automation; approved connectors; environment-specific credentials or RBAC require validation.                                               | Review connector list, DLP classification, environment, sharing groups, credentials, owner, service account use, gateway/API path, data classification, and logging/monitoring.                             |
| Tier 3 - End-to-end boundary review  | Broadly shared or tenant-impacting flow/canvas app; PCI data; regulated/highly sensitive data; external/custom connector; service account or app registration; privileged actions; production file passing; critical operational workflow. | Review complete data flow, connectors, identity model, least privilege, secrets, environment separation, file encryption, PCI implications, gateway path, audit logs, exception handling, and CAB evidence. |

### 7.1 Power Platform Review Considerations

- **Environment and DLP:** Confirm whether the app/flow is in an appropriate environment and whether connector use aligns with DLP policy and environment purpose.

- **Connection ownership:** Determine whether connections run as the maker/user, shared connection, service account, service principal, or other non-human identity.

- **Sharing scope:** Review sharing with users, groups, teams, departments, or tenant-wide audiences. Broad sharing may escalate the tier.

- **Connector boundary:** Review use of standard, premium, custom, HTTP, SQL, Snowflake, SFTP, Dataverse, on-prem gateway, or vendor API connectors.

- **Credential handling:** Confirm credentials are not embedded in flow logic, tickets, documentation, or unmanaged scripts; credentials must be stored and rotated using approved methods.

- **ALM and deployment:** For production business processes, confirm whether the solution follows an appropriate dev/test/prod or managed deployment path, as applicable to platform maturity and licensing.

- **Logging and supportability:** Confirm owner, failure handling, flow run visibility, alerting, and operational support model.

## 8. Approved Platform Review Focus

### 8.1 Approved Platform Principle

An approved enterprise platform provides a controlled foundation, but each production solution built on that platform must still be reviewed based on its actual data flow, access model, connector boundary, credential handling, and production impact. Platform approval does not automatically approve every application, flow, data product, connector, or role configuration deployed on the platform.

### 8.2 Snowflake on AWS Review Focus

Snowflake on AWS is expected to host production applications, data products, integrations, and analytics workflows. AppSec reviews for Snowflake-backed solutions should evaluate the application/data boundary and platform configuration, not only traditional application code.

| **Domain**                                   | **Review Focus**                                                                                                                                                            |
|----------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Data classification and permitted use        | Identify data categories, NPI/customer data, employee data, confidential data, PCI data, tokenized data, and downstream users. Confirm data owner approval where required.  |
| RBAC and object access                       | Review role hierarchy, grants, warehouse/database/schema/table/view/procedure access, ownership, administrative roles, break-glass access, and separation of duties.        |
| Masking, row access, and governance policies | Confirm whether masking policies, row access policies, object tagging, sensitive data classification, or secure views are required and implemented.                         |
| Non-human identity and credentials           | Review service users, app roles, key-pair authentication, secrets storage, token/key rotation, ownership, and least privilege.                                              |
| Environment separation                       | Confirm dev/test/prod separation for data, credentials, roles, warehouses, pipelines, and deployment paths. Avoid shared dev/prod credentials or uncontrolled prod changes. |
| External integrations and data movement      | Review stages, external functions, SFTP/API exports, data sharing, file transfers, ingestion paths, and egress controls.                                                    |
| PCI and encryption                           | For PCI data or PCI-impacting flows, validate scope, tokenization assumptions, encryption in transit/at rest, file encryption, retention, and downstream access.            |
| Logging and monitoring                       | Confirm availability of login history, query history, access history, object dependencies, audit logs, alerting, and incident response support.                             |
| Change control                               | Confirm schema, view, masking/row access policy, task/stream/procedure, connector, and role changes follow change management and AppSec/CAB review as applicable.           |

### 8.3 Power Platform Review Focus

| **Domain**                     | **Review Focus**                                                                                                                                         |
|--------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
| Environment strategy           | Confirm appropriate environment, managed environment capabilities if used, DLP policy, connector governance, and production support model.               |
| Connector and gateway controls | Review standard/premium/custom connectors, HTTP/SFTP/API paths, on-premises data gateway, vendor APIs, and endpoint allowlisting.                        |
| Credential and identity model  | Review maker/user-owned connections, service accounts, app registrations, service principals, shared connections, and least privilege.                   |
| Sharing and authorization      | Review app/flow sharing, Dataverse security roles, Microsoft 365 groups, Teams distribution, owner/co-owner access, and administrative roles.            |
| Data handling                  | Review sensitive data inputs/outputs, files, attachments, retention, e-mailing/export behavior, downstream storage, and PCI impact.                      |
| ALM and deployment             | For production solutions, evaluate solution packaging, dev/test/prod movement, solution checker, deployment pipeline, and rollback path when applicable. |
| Monitoring and operations      | Confirm flow failure handling, operational owner, support queue, run history, audit logs, and incident response visibility.                              |

## 9. AppSec Service Catalog

The AppSec function provides a risk-based set of services. Not every service is required for every tier. The tiering decision and platform context determine required activities.

| **Service**                                                | **Purpose**                                                                                      | **Typical Applicability**                                                                     |
|------------------------------------------------------------|--------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| Tiering and intake review                                  | Determine review depth and required security activities.                                         | All in-scope production-bound work.                                                           |
| Security requirements and design advisory                  | Identify security requirements early and align design decisions with policy and risk appetite.   | Tier 2 and Tier 3; Tier 1 where requested.                                                    |
| Threat modeling / boundary review                          | Identify trust boundaries, abuse cases, data flows, connectors, identities, and mitigations.     | Tier 3; selected Tier 2 changes.                                                              |
| Platform configuration review                              | Review Snowflake, Power Platform, AWS, identity, RBAC, DLP, environment, and connector settings. | Tier 2 and Tier 3 platform-based solutions.                                                   |
| Secrets and credential review                              | Validate secret storage, rotation, environment separation, and non-human identity scope.         | Tier 2/Tier 3 where credentials, service accounts, or automated jobs are used.                |
| SAST/SCA/secret scanning review                            | Review source code and dependencies where code repositories or build pipelines exist.            | Traditional apps and coded components; not always applicable to pure low-code configurations. |
| DAST / vulnerability testing review                        | Assess running web applications or APIs for exploitable issues.                                  | Internet-facing, API, high-risk, or Tier 3 applications where feasible.                       |
| Manual security testing / penetration testing coordination | Provide deeper testing for critical, internet-facing, PCI-impacting, or high-risk systems.       | Tier 3 or regulatory/contractual requirement.                                                 |
| Third-party / vendor security coordination                 | Coordinate with TPRM for vendor-hosted apps, external APIs, and outsourced development.          | Vendor/SaaS/integration-dependent solutions.                                                  |
| Security defect management                                 | Track findings, remediation, retest, exceptions, and closure evidence.                           | Tier 2/Tier 3 and any review with findings.                                                   |

## 10. Production Review Workflow

1.  **Intake submission.** Application owner submits intake with business purpose, production target date, platform, data classification, user population, connectors, identities, credentials, environment model, and CAB/change reference where available.

2.  **Tiering.** Information Security assigns Tier 1, Tier 2, or Tier 3 based on risk criteria and may request additional information.

3.  **Review planning.** AppSec identifies required evidence and review activities based on tier, platform, data type, and connector/identity boundary.

4.  **Review execution.** AppSec reviews submitted evidence, conducts meetings or walkthroughs as needed, validates platform-specific controls, and documents findings or conditions.

5.  **Findings and conditions.** Required remediations, compensating controls, conditions, due dates, and accountable owners are documented.

6.  **Approval decision.** Information Security records Approved, Approved with Conditions, Not Approved, or Risk Accepted/Exception Approved.

7.  **CAB production approval.** CAB validates AppSec approval evidence before approving production release.

8.  **Post-go-live follow-up.** Open conditions, exceptions, remediation actions, monitoring items, and evidence updates are tracked to completion.

### 10.1 Expected Review Timing

AppSec review should begin before the CAB meeting whenever possible. CAB should be used to confirm that required approvals are complete, not to perform first-time security discovery. Application owners are responsible for submitting reviews early enough to allow appropriate tiering, evidence collection, review, remediation, and re-review.

### 10.2 Minimum CAB Package for In-Scope Changes

- AppSec review ID or ticket reference.

- Assigned AppSec tier and platform category.

- Information Security approval status and approval date.

- Open conditions, due dates, and accountable owners, if any.

- Exception/risk acceptance identifier, scope, approver, and expiration date, if applicable.

- Confirmation that production deployment scope matches the reviewed scope.

## 11. Findings, Conditions, Exceptions, and Risk Acceptance

### 11.1 Findings and Conditions

AppSec findings should be documented in the designated system of record with severity, owner, remediation expectation, due date, and validation method. Conditions may be attached to an approval when the residual risk is acceptable for production deployment with compensating controls or post-go-live follow-up.

### 11.2 Risk Acceptance

Where remediation cannot be completed before production deployment, the application/business owner must document the risk acceptance request. Information Security provides risk assessment and recommendation. Approval authority depends on severity, data type, regulatory impact, and business criticality.

- Risk acceptance must describe the issue, affected asset/solution, data and business impact, compensating controls, remediation plan, accountable owner, and expiration date.

- Risk acceptance for PCI-impacting, privileged-access, customer-data, or Tier 3 issues must be approved by the appropriate senior risk authority, typically including the CISO or delegated risk forum.

- Expired exceptions must be remediated, re-approved, or escalated. Permanent exceptions should be avoided unless formally approved as an accepted design pattern by governance.

### 11.3 Blocking Conditions

- Unknown or unvalidated PCI boundary impact.

- Unapproved external connector or data export path involving sensitive or regulated data.

- Privileged or high-scope non-human identity without least-privilege review or required PAM/IAM approval.

- Production credentials or secrets shared across environments or stored in unapproved locations.

- Missing encryption for sensitive or PCI data files in transit, storage, or handoff points where encryption is required.

- Broad sharing or tenant-wide deployment without authorization and logging visibility.

- Material review evidence missing before CAB.

## 12. Evidence and Records

Review evidence must be retained in the designated system of record, such as the AppSec review ticket, GRC platform, change record, repository, or approved document repository. Evidence should be sufficient to demonstrate review scope, decision basis, approval, and follow-up tracking.

| **Evidence Type**     | **Examples**                                                                                                                                                                             |
|-----------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Tiering evidence      | Intake form, tier decision, rationale, platform, data classification, user population, connector list, identity model.                                                                   |
| Review evidence       | Architecture/data flow diagram, walkthrough notes, connector/RBAC screenshots or exports, Snowflake role grant evidence, Power Platform connector/environment evidence, testing reports. |
| Approval evidence     | InfoSec approval status, approval date, approver, conditions, CAB change reference, production scope confirmation.                                                                       |
| Risk evidence         | Findings, risk acceptance, compensating controls, exception expiration, remediation owner, follow-up ticket.                                                                             |
| Post-go-live evidence | Retest results, condition closure, monitoring validation, access review, credential rotation confirmation, updated diagrams.                                                             |

## 13. Metrics and Reporting

Metrics should support operational management, risk oversight, auditability, and continuous improvement. Metrics should be risk-based and should not overload senior governance forums with raw scanner counts.

| **Audience**                           | **Recommended Metrics**                                                                                                                                                          |
|----------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Technology / AppSec operations         | Number of reviews by tier; review aging; time to triage; findings by category; conditions by owner; false-positive/duplicate trends; recurring connector/RBAC/credential issues. |
| CISO / Technology Risk                 | Tier 2/Tier 3 review volume; overdue high-risk findings; exception aging; PCI-impacting review status; platform risk trends; AppSec approval coverage for CAB changes.           |
| Board / Risk Committee, as appropriate | Material application security risks; Tier 3/high-risk trends; significant exceptions; remediation progress for material gaps; major platform/security program maturity updates.  |
| Platform owners                        | Power Platform shared app/flow review trends; DLP/custom connector exceptions; Snowflake RBAC/masking/access review issues; non-human identity findings.                         |

## 14. Program Maintenance and Continuous Improvement

- This charter must be reviewed at least annually by the CISO or qualified designee and updated as necessary based on changes to technology, regulatory expectations, risk appetite, audit findings, and platform maturity.

- Tiering criteria should be revisited after major platform changes, new Snowflake/AWS production patterns, Power Platform governance changes, PCI scope changes, material incidents, or significant audit/exam findings.

- Detailed implementation procedures may be maintained separately for Snowflake, Power Platform, IAM/PAM, CAB, secure coding, pipeline scanning, PCI, and exception management.

- Lessons learned from findings, incidents, near misses, and CAB escalations should be incorporated into templates, intake questions, training, and review checklists.

## Appendix A. Minimum Review Requirements by Tier

| **Review Area**                   | **Tier 1**                                  | **Tier 2**                                             | **Tier 3**                                                                                                |
|-----------------------------------|---------------------------------------------|--------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| Intake and tiering                | Required                                    | Required                                               | Required                                                                                                  |
| Data classification               | Confirm no sensitive/regulated data         | Required                                               | Required with data owner input where needed                                                               |
| Architecture/data flow            | Basic description                           | Required for connectors/data movement                  | End-to-end diagram required                                                                               |
| Connector review                  | Confirm none or low-risk approved connector | Required                                               | Full boundary review required                                                                             |
| RBAC/access review                | Confirm user-only privilege                 | Required for platform roles/groups                     | Detailed review of roles, groups, privileged access, and least privilege                                  |
| Service/non-human identity review | Not expected                                | Required if used                                       | Required; validate scope, owner, rotation, monitoring; PAM/IAM as applicable                              |
| Secrets/credentials               | Confirm none or user-owned connection only  | Review credential model                                | Confirm approved secret storage, rotation, environment siloing                                            |
| Environment separation            | Not generally applicable                    | Review if dev/test/prod or platform environments exist | Required; confirm prod isolation and deployment control                                                   |
| PCI impact validation             | Confirm none                                | Confirm none or escalate                               | Required if PCI data/scope impact exists                                                                  |
| Testing evidence                  | Not generally required                      | Risk-based                                             | Required as applicable: threat model, DAST, pen test, SAST/SCA, platform testing, UAT/security validation |
| CAB evidence                      | AppSec approval/tiering record              | AppSec approval with conditions if any                 | AppSec approval plus evidence, conditions, exceptions, and senior approval where required                 |

## Appendix B. AppSec Intake Questions

- What business process does the solution support, and who is the business/application owner?

- Is the solution moving to production, production-like use, or broad business use?

- What platform is used: custom code, Snowflake on AWS, Power Platform, SaaS, API integration, or other?

- Who will use the solution and how broadly will it be shared?

- Does the solution process customer data, employee data, nonpublic information, confidential data, PCI data, tokenized card data, credentials, or regulated records?

- What systems, connectors, APIs, SFTP paths, data stores, e-mail flows, files, or vendor services are involved?

- Does the solution use a service account, app registration, service principal, key-pair authentication, scheduled job, backend bot, or other non-human identity?

- Does the solution use privileged access, administrative roles, PAM-managed accounts, or high-scope permissions?

- Are dev/test/prod environments separated? Are credentials, secrets, and data separated by environment?

- How are files, exports, reports, and downstream data transfers protected and retained?

- What logging, monitoring, support ownership, and failure handling exist?

- What change record, release date, CAB date, and deployment scope are planned?

## Appendix C. CAB Evidence Checklist

| **CAB Item**            | **Required Evidence**                                                                   |
|-------------------------|-----------------------------------------------------------------------------------------|
| AppSec review reference | Ticket/review ID linked to change record.                                               |
| Tier decision           | Tier 1/2/3 and rationale.                                                               |
| Approval status         | Approved, Approved with Conditions, Not Approved, or Risk Accepted/Exception Approved.  |
| Scope match             | Production deployment scope matches reviewed scope.                                     |
| Conditions              | Open conditions, owners, due dates, and tracking tickets.                               |
| Exceptions              | Risk acceptance ID, approver, expiration date, compensating controls.                   |
| Platform evidence       | Snowflake/Power Platform/AWS evidence as applicable.                                    |
| Identity evidence       | Service account, non-human identity, privileged access, PAM/IAM approval as applicable. |
| PCI evidence            | PCI scope/tokenization/encryption/file handling evidence as applicable.                 |

## Appendix D. Evidence Matrix

| **Control Area**               | **Representative Evidence**                                                                                                               |
|--------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| Snowflake RBAC                 | Role/grant export or screenshot, data owner approval, least-privilege rationale, administrative role review.                              |
| Snowflake data protection      | Classification/tagging evidence, masking policy, row access policy, secure view, tokenization validation.                                 |
| Snowflake data movement        | Stage/external integration details, SFTP/API design, file encryption evidence, retention and destination controls.                        |
| Power Platform environment/DLP | Environment name/type, DLP policy classification, managed environment setting if applicable, connector list.                              |
| Power Platform sharing         | Users/groups/shared ownership, connection references, app/flow owner/co-owner list, Dataverse role evidence if applicable.                |
| Power Platform ALM             | Solution package, deployment pipeline/run, solution checker result, dev/test/prod movement evidence where applicable.                     |
| Non-human identity             | Account/app registration/service principal ID, owner, purpose, permissions, rotation schedule, PAM/IAM approval, secret storage evidence. |
| Secrets and credentials        | Approved vault/secret store reference, environment-specific secrets, rotation evidence, no secrets in code/tickets/config exports.        |
| Testing and validation         | Threat model, SAST/SCA/secret scan, DAST, pen test, peer review, platform configuration review, UAT/security test notes as applicable.    |
| Risk acceptance                | Risk description, owner, approver, compensating controls, expiration, remediation plan, residual risk rating.                             |

## Appendix E. Glossary

| **Term**                    | **Definition**                                                                                                                                                                                                  |
|-----------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Application Security Review | Risk-based Information Security review of an application, workflow, automation, data product, platform configuration, or integration before production deployment or material change.                           |
| Approved Platform           | A platform approved for enterprise use by the Bank. Platform approval does not automatically approve each application or configuration built on the platform.                                                   |
| CAB                         | Change Advisory Board or equivalent production change approval forum.                                                                                                                                           |
| Connector                   | A configured integration path to another system or service, including Power Platform connectors, custom connectors, APIs, HTTP actions, SFTP, vendor APIs, and database connectors.                             |
| Non-human Identity          | A service account, app registration, service principal, robot/bot account, API key identity, key-pair-authenticated account, or other identity used by automation or systems rather than a person.              |
| PCI Data                    | Cardholder data or data/processes that may affect PCI scope, including flows involving tokenized card data where tokenization/scope must be validated.                                                          |
| Platform-based Solution     | An application, workflow, report, data product, automation, or integration built primarily using configuration and platform services rather than traditional custom code.                                       |
| Sensitive Data              | Customer information, nonpublic information, employee information, confidential business data, regulated data, PCI data, secrets, credentials, or other data requiring enhanced protection under policy or law. |

## Appendix F. References

The following external references informed this charter. Internal policies, standards, legal interpretations, and approved risk decisions take precedence. Links should be validated during annual review.

- NYDFS 23 NYCRR Part 500, Section 500.8 - Application Security: [https://www.law.cornell.edu/regulations/new-york/23-NYCRR-500.8](https://www.law.cornell.edu/regulations/new-york/23-NYCRR-500.8)

- NYDFS Cybersecurity Resource Center: [https://www.dfs.ny.gov/industry_guidance/cybersecurity](https://www.dfs.ny.gov/industry_guidance/cybersecurity)

- PCI Security Standards Council Document Library - PCI DSS v4.0.1: [https://www.pcisecuritystandards.org/document_library/](https://www.pcisecuritystandards.org/document_library/)

- Microsoft Learn - Power Platform environments overview: [https://learn.microsoft.com/en-us/power-platform/admin/environments-overview](https://learn.microsoft.com/en-us/power-platform/admin/environments-overview)

- Microsoft Learn - ALM environment strategy considerations: [https://learn.microsoft.com/en-us/power-platform/alm/environment-strategy-alm](https://learn.microsoft.com/en-us/power-platform/alm/environment-strategy-alm)

- Microsoft Learn - Managed Environments overview: [https://learn.microsoft.com/en-us/power-platform/admin/managed-environment-overview](https://learn.microsoft.com/en-us/power-platform/admin/managed-environment-overview)

- Microsoft Learn - Overview of pipelines in Power Platform: [https://learn.microsoft.com/en-us/power-platform/alm/pipelines](https://learn.microsoft.com/en-us/power-platform/alm/pipelines)

- Snowflake Documentation - Data Governance in Snowflake: [https://docs.snowflake.com/en/guides-overview-govern](https://docs.snowflake.com/en/guides-overview-govern)

- Snowflake Documentation - Dynamic Data Masking: [https://docs.snowflake.com/en/user-guide/security-column-ddm-intro](https://docs.snowflake.com/en/user-guide/security-column-ddm-intro)

- Snowflake Documentation - Understanding row access policies: [https://docs.snowflake.com/en/user-guide/security-row-intro](https://docs.snowflake.com/en/user-guide/security-row-intro)

Draft generated for internal publication review. Accessed/reference date for external sources: 2026-06-15.
