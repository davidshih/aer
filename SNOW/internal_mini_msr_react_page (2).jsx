import React, { useMemo, useState } from "react";

const platforms = [
  { id: "power-platform", label: "Power Platform", short: "Apps / Flows / Agents", icon: "⚡" },
  { id: "snowflake-python", label: "Snowflake Python", short: "Scripts / Notebooks / Procedures", icon: "❄️" },
  { id: "uipath", label: "UiPath", short: "RPA / Orchestrator / Robots", icon: "🤖" },
];

const statuses = ["Not Reviewed", "Pass", "Fail", "Partial", "N/A"];

function makeControl({
  title,
  severity = "Medium",
  required = true,
  description,
  steps = [],
  evidence = [],
  remediation = "Document exception, compensating control, owner, and remediation date if this cannot be completed before approval.",
  fields = ["Evidence / notes"],
  deepDive = [],
  failIf = [],
  baseline = false,
  owner = "",
}) {
  return { title, severity, required, description, steps, evidence, remediation, fields, deepDive, failIf, baseline, owner };
}

const baselineSection = {
  id: "control-baseline",
  title: "Control Baseline — Required First",
  icon: "🏛️",
  controls: [
    makeControl({
      title: "ServiceNow CMDB Registration",
      severity: "Low",
      required: true,
      baseline: true,
      owner: "IT / Dev",
      description: "The application or automation must be registered in ServiceNow CMDB with owner, dependencies, environment, and support information documented before review completion.",
      steps: ["Confirm CMDB record exists.", "Verify business owner, technical owner, support owner, dependencies, platform, and environment are documented.", "Confirm ServiceNow CHG or RIM/SOW reference is linked when applicable."],
      deepDive: ["For Tier 2/3, dependencies should include upstream/downstream systems, service accounts, APIs, queues, stages, and monitoring sources.", "For production workloads, confirm environment classification and operational owner are not blank."],
      evidence: ["ServiceNow CMDB record", "ServiceNow RIM/SOW or intake reference", "Owner/dependency/environment fields"],
      remediation: "Create or update the ServiceNow CMDB record before approval. Do not approve orphaned production automation.",
      failIf: ["No CMDB record exists for a production workload.", "Owner, environment, or dependency information is missing."],
      fields: ["ServiceNow CMDB record", "Business owner", "Technical owner", "Dependencies", "Environment", "Support group", "RIM/SOW or intake reference"],
    }),
    makeControl({
      title: "Network / Data Flow Diagram",
      severity: "Medium",
      required: true,
      baseline: true,
      owner: "IT / IAM / InfoSec",
      description: "A network and data flow diagram must show flows between systems, protocols, ports, encryption, credentials or identities used, and data classification labels.",
      steps: ["Provide diagram in Visio, draw.io, Lucidchart, or equivalent.", "Show source, destination, intermediate storage, protocols, ports, encryption, and credentials/identities used.", "Label sensitive data and approved platform boundary."],
      deepDive: ["For Tier 2/3, include shadow/intermediate storage such as SharePoint Lists, OneDrive files, queues, Snowflake stages, Blob/S3 landing files, and logs.", "TLS 1.2+ should be minimum; TLS 1.3 is preferred where supported.", "If public or cross-tenant traffic exists, identify gateway, APIM, WAF, private endpoint, firewall rule, or equivalent control."],
      evidence: ["Network diagram", "Data flow diagram", "Protocol/port/encryption annotations", "Credential/identity annotations"],
      remediation: "Create a diagram before approval. If the data path cannot be explained, the review cannot be completed.",
      failIf: ["No diagram exists for a Tier 2/3 or production workload.", "Diagram omits intermediate storage, credentials, ports, protocols, or encryption.", "Data flow leaves approved boundary without approval."],
      fields: ["Diagram link", "Protocols", "Ports", "Encryption", "Credentials / identities used", "Intermediate storage", "Approved boundary notes"],
    }),
    makeControl({
      title: "Dedicated Service Account / Non-Interactive Identity",
      severity: "Medium",
      required: true,
      baseline: true,
      owner: "IT / IAM / InfoSec",
      description: "Automation should use a dedicated non-interactive identity such as service account, service principal, managed identity, robot account, or Snowflake execution role with least privilege per environment.",
      steps: ["Identify identity used in each environment.", "Confirm it is not a developer personal account.", "Confirm least-privilege role and environment separation.", "Confirm MFA/conditional access policy where applicable for human/admin access."],
      deepDive: ["For Snowflake, provide SHOW GRANTS TO ROLE <execution_role> output.", "For Power Platform, identify connection owner and whether it is user-delegated or service identity.", "For UiPath, confirm unattended robot does not use developer personal Windows account."],
      evidence: ["SHOW GRANTS screenshot", "Azure AD / Entra ID policy", "Service account record", "Robot account record", "Role grant evidence"],
      remediation: "Create dedicated least-privilege identities per environment and remove personal-account execution.",
      failIf: ["Production automation runs under a developer personal account.", "Service account has broad admin/export/write permissions without approval.", "Same identity is reused across environments without justification."],
      fields: ["Identity type", "DEV identity", "TEST identity", "PROD identity", "Least-privilege role", "MFA / CA policy", "Grants evidence"],
    }),
    makeControl({
      title: "API Key Storage in Delinea / Enterprise PAM",
      severity: "Critical",
      required: true,
      baseline: true,
      owner: "IT / Dev / InfoSec",
      description: "API keys and long-lived secrets must be stored in Delinea or the approved enterprise PAM/vault. Platform-native secrets such as Snowflake Secrets are acceptable when approved and access-controlled.",
      steps: ["Confirm API keys are not stored in source code, config, run history, notebook, XAML, or exported package.", "Verify Delinea/PAM or approved secret store configuration.", "Confirm access to the secret is least privilege and audited."],
      deepDive: ["For Snowflake, provide CREATE SECRET DDL and grants, or approved external vault configuration.", "For UiPath, provide Orchestrator Asset, CyberArk, Azure Key Vault, HashiCorp Vault, or credential proxy evidence.", "For Power Platform, verify connector/API credentials are not exposed in URL, header text, or flow run history."],
      evidence: ["Delinea config screenshot", "CREATE SECRET DDL + grants", "Vault/PAM access policy", "Secret scanner result"],
      remediation: "Move API keys to Delinea or approved vault, rotate exposed keys, and restrict read permissions.",
      failIf: ["API key appears in code, config, run history, logs, exported package, or notebook.", "Secret store access is broad or unaudited.", "Vault/PAM bootstrap credential is hardcoded."],
      fields: ["Secret type", "Delinea / PAM record", "Snowflake CREATE SECRET DDL", "Vault grants", "Access policy", "Secret scanner result"],
    }),
    makeControl({
      title: "API Key / Secret Rotation",
      severity: "Critical",
      required: true,
      baseline: true,
      owner: "Dev / AppSec",
      description: "API keys and long-lived secrets require at least yearly rotation with documented schedule, runbook, and change records. Immediate rotation is required if a secret entered Git, logs, screenshots, or packages.",
      steps: ["Confirm yearly rotation schedule exists.", "Confirm rotation runbook exists.", "Confirm ServiceNow CHG tickets or equivalent change records exist for prior/planned rotations."],
      deepDive: ["For Tier 2/3, include emergency rotation procedure and dependency impact.", "If the secret has ever been exposed, rotation must be immediate; deletion from code is not enough.", "Confirm downstream systems can tolerate rotation without outage."],
      evidence: ["Rotation schedule document", "Rotation runbook", "ServiceNow CHG tickets", "Last rotation evidence"],
      remediation: "Create rotation runbook and schedule. Rotate exposed or unknown-age secrets before approval.",
      failIf: ["No rotation schedule exists for API keys or long-lived secrets.", "Exposed secret was not rotated.", "No owner exists for rotation."],
      fields: ["Secret/API key", "Rotation owner", "Rotation frequency", "Last rotation date", "Next rotation date", "Runbook link", "ServiceNow CHG"],
    }),
    makeControl({
      title: "SIEM Integration — Purview to Google SecOps",
      severity: "Medium",
      required: true,
      baseline: true,
      owner: "InfoSec / Logging",
      description: "Logging and monitoring must be enabled for applicable platforms. For Power Platform, logs should be enabled in Microsoft Purview and integrated or searchable in Google SecOps where applicable.",
      steps: ["Confirm Power Platform log source is enabled in Purview where applicable.", "Confirm events are forwarded, imported, or searchable in Google SecOps.", "Confirm alerting or detection exists for high-risk activity or failure conditions."],
      deepDive: ["For Tier 2/3, provide Google SecOps search screenshot for the AppID/workload/user or connector activity.", "For Tier 2/3, provide test alert evidence or alert configuration.", "If not applicable, document alternate log source and SIEM/search location."],
      evidence: ["Purview log enablement screenshot", "Google SecOps search screenshot", "Alert configuration", "Test alert evidence"],
      remediation: "Enable platform logging, route/search logs in Google SecOps, and configure alerts for failures or suspicious activity.",
      failIf: ["No searchable logs exist for a production Tier 2/3 workload.", "Sensitive data appears in logs.", "Critical automation failure has no alert or owner."],
      fields: ["Purview log enabled", "Google SecOps search", "Alert config", "Test alert evidence", "Retention", "Log owner"],
    }),
    makeControl({
      title: "SAST / SCA — Snyk Scan",
      severity: "Medium",
      required: true,
      baseline: true,
      owner: "Dev / AppSec",
      description: "Python code and dependencies must be scanned for vulnerabilities. High/Critical findings should block deployment unless formally accepted with remediation plan.",
      steps: ["Run Snyk or approved SAST/SCA scan for code and dependencies.", "Confirm High/Critical findings block deployment or have documented exception.", "Link remediation tickets for open findings."],
      deepDive: ["For Snowflake Python or other Python automation, include dependency file and pipeline scan step.", "For UiPath/Power Platform exported artifacts, include applicable secret/config scan where SAST/SCA is limited.", "For Tier 3, require AppSec disposition for unresolved High/Critical findings."],
      evidence: ["Snyk scan results", "Azure Pipeline YAML", "Jira remediation tickets", "Exception approval"],
      remediation: "Fix High/Critical findings, pin/upgrade dependencies, or document AppSec-approved exception before deployment.",
      failIf: ["High/Critical vulnerability is unresolved without exception.", "No scan is run for code/dependencies where scanning is technically feasible.", "Pipeline does not block or flag High/Critical findings."],
      fields: ["Snyk result", "Pipeline YAML", "High/Critical findings", "Block deployment?", "Jira tickets", "Exception approval"],
    }),
    makeControl({
      title: "Application Security Scope Determination",
      severity: "Low",
      required: true,
      baseline: true,
      owner: "Vendor / InfoSec",
      description: "Determine whether additional application security testing is required. Some workloads are not external-facing web applications and rely on vendor-managed platform testing, but the application-specific configuration still needs review.",
      steps: ["Determine whether the workload is external-facing, customer-facing, internet-exposed, or custom web/API code.", "If not external-facing and platform testing is vendor-managed, document rationale for N/A.", "If custom external-facing web/API exists, escalate to appropriate AppSec testing."],
      deepDive: ["For Tier 2/3, document why platform-managed testing is sufficient or why additional AppSec testing is required.", "External endpoints, public agents, custom APIs, Streamlit apps, or custom web front ends should not be auto-marked N/A."],
      evidence: ["Scope rationale", "Vendor/platform testing statement", "Architecture review", "No customer action required note"],
      remediation: "Escalate to AppSec testing if custom external-facing web/API code exists or if platform-managed scope does not cover the exposed functionality.",
      failIf: ["External-facing custom web/API exists but AppSec testing is marked N/A without rationale.", "Reviewer cannot determine exposure scope."],
      fields: ["External-facing?", "Customer-facing?", "Custom web/API?", "Vendor-managed testing rationale", "No customer action required note", "Evidence link"],
    }),
    makeControl({
      title: "Penetration Testing Determination",
      severity: "Low",
      required: true,
      baseline: true,
      owner: "Vendor / InfoSec",
      description: "Penetration testing is typically N/A for non-external-facing workloads built entirely on vendor-managed platforms, but the N/A decision must be documented.",
      steps: ["Determine whether the workload exposes a public web app, API, agent, or endpoint.", "If no external-facing web/API and platform testing is vendor-managed, document N/A rationale.", "If exposure exists, route to penetration testing or full AppSec review."],
      deepDive: ["For Tier 3, do not rely solely on vendor-managed platform testing if the team built custom public endpoints, custom API logic, or high-risk external integrations.", "Document boundary between vendor-managed platform testing and customer-owned application configuration."],
      evidence: ["N/A rationale", "Vendor-managed platform testing note", "Architecture/exposure review", "No customer action required"],
      remediation: "Schedule penetration testing or enhanced AppSec review when external-facing custom functionality exists.",
      failIf: ["Public endpoint or custom API exists and penetration testing is marked N/A without compensating review.", "No exposure review evidence exists."],
      fields: ["Pentest required?", "N/A rationale", "External exposure", "Vendor-managed scope", "No customer action required note", "Evidence link"],
    }),
    makeControl({
      title: "Azure DevOps Git Repository and Branch Protection",
      severity: "Medium",
      required: true,
      baseline: true,
      owner: "Dev",
      description: "Code, configuration, exported artifacts, notebooks, and automation definitions should be stored in Azure DevOps Git with branch protection and deployment through CI/CD only.",
      steps: ["Confirm repository exists in Azure DevOps Git.", "Confirm branch protection, PR review, and commit history are available.", "Confirm deployment is via CI/CD pipeline only where technically feasible."],
      deepDive: ["For Tier 2/3, require branch policies such as reviewer approval and restricted direct push to main.", "For Power Platform and UiPath, exported solutions/packages/project files should be represented in source control.", "For Snowflake/Python, notebook/procedure/script code should be synced or exported to repo."],
      evidence: ["Git repo screenshot", "Branch policies", "Commit history", "Pipeline YAML", "PR review"],
      remediation: "Move artifacts into Azure DevOps Git and require branch protection and CI/CD deployment before approval.",
      failIf: ["Production code or automation definition is not recoverable from source control.", "Direct production edits bypass review for Tier 2/3 workload.", "No branch protection exists for production branch."],
      fields: ["Azure DevOps repo", "Branch policy", "Commit history", "Pipeline YAML", "CI/CD only?", "PR evidence"],
    }),
    makeControl({
      title: "ServiceNow Change Control / CAB Validation",
      severity: "Medium",
      required: true,
      baseline: true,
      owner: "IT / Dev",
      description: "Production deployment or material change should have ServiceNow CHG record, CAB evidence where applicable, and pipeline change validation.",
      steps: ["Confirm ServiceNow CHG ticket exists for production deployment or material change.", "Confirm CAB approval or standard change classification where applicable.", "Confirm pipeline validates or references the change record before deployment."],
      deepDive: ["For Tier 2/3, link deployment record, CAB minutes, and pipeline run evidence.", "Emergency changes should have retroactive approval and incident/change linkage.", "Material changes should trigger re-review if data, API, privilege, external exposure, or business impact changes."],
      evidence: ["ServiceNow CHG ticket", "CAB meeting minutes", "Pipeline CHG validation", "Deployment record"],
      remediation: "Create or link the change record and enforce change validation in deployment pipeline.",
      failIf: ["Production change has no CHG record or approved standard change path.", "Pipeline/deployment bypasses change approval for Tier 2/3 workload.", "Material change did not trigger re-review."],
      fields: ["ServiceNow CHG", "CAB minutes", "Standard change?", "Pipeline validation", "Deployment record", "Material change review"],
    }),
  ],
};

const sharedSections = [
  {
    id: "data-access",
    title: "Data Access & Classification",
    icon: "🗄️",
    controls: [
      makeControl({
        title: "Data Classification",
        severity: "High",
        description: "All data processed by the application or automation must be classified. Identify Public, Internal, Confidential, Restricted, PII, PHI, PCI, NPI, financial, credential-like, and production-sensitive data.",
        steps: ["Confirm formal classification document, tag, or data owner statement.", "Confirm data flow diagram or inventory identifies data types.", "Confirm cross-system transfers preserve classification requirements."],
        evidence: ["Data classification matrix", "Data flow diagram", "Data inventory", "Data owner confirmation"],
        remediation: "Work with the data owner to classify the data and document handling rules before production approval.",
        fields: ["Data sources", "Classification", "Regulated data type", "Data owner", "Evidence link"],
      }),
      makeControl({
        title: "Data Source Inventory",
        severity: "High",
        description: "All formal and shadow data flows must be identified. Low-code and automation workloads often create hidden copies in Excel, SharePoint Lists, OneDrive, Blob/S3, queues, stages, run history, and logs.",
        steps: ["List every source system and destination system.", "Identify intermediate storage such as OneDrive temp files, SharePoint Lists, Dataverse tables, S3/Blob landing files, Snowflake stages, queues, local folders, logs, and run history.", "Document retention, owner, access scope, and cleanup method for each intermediate node."],
        deepDive: ["For Tier 2/3, verify there is no shadow data flow such as Excel temp files or SharePoint Lists shared to broad groups.", "For Tier 2/3, confirm SELECT/API GET field selection is minimized and does not pull full records only to filter later in the app.", "For Tier 3, require a data flow diagram showing data classification labels, storage locations, and transport protections such as TLS 1.2+ with TLS 1.3 preferred where supported."],
        evidence: ["Data flow diagram with classification labels", "Intermediate storage inventory", "Connector/API list", "Retention/cleanup evidence", "Access screenshot"],
        remediation: "Remove unapproved intermediate storage, restrict access, add retention/cleanup, or redesign the flow so sensitive data is not copied into unmanaged locations.",
        failIf: ["Sensitive or regulated data lands in unmanaged SharePoint/OneDrive/Excel/Blob/Stage/Queue without owner, access control, and retention.", "Production data is copied to lower environment or personal storage without approval and masking.", "Reviewer cannot determine where data is stored after execution."],
        fields: ["Source systems", "Destination systems", "Intermediate storage", "Shadow data flows", "Retention / cleanup", "Owner", "Evidence link"],
      }),
      makeControl({
        title: "Least-Privilege Data Access",
        severity: "High",
        description: "The workload should only access the minimum data required. Review connection identity carefully: user-delegated access and shared service identity have very different privilege escalation risks.",
        steps: ["List access for each source, destination, and intermediate storage location.", "Identify whether each connection uses user-delegated identity, service account, service principal, managed identity, robot account, or Snowflake execution role.", "Validate read, write, delete, approve, export/unload, and admin rights against business need."],
        deepDive: ["For Tier 2/3, prove shared service identities cannot let low-privilege users indirectly access high-privilege data.", "For Tier 2/3, split high-risk permissions where possible, such as read role vs write role vs export/unload role.", "For Tier 3, confirm row-level authorization is enforced at the data/API/backend layer; frontend filtering is not accepted as an authorization control."],
        evidence: ["Access matrix", "Connection identity screenshot", "Role/group membership", "Permission screenshot", "Business justification", "Approval ticket"],
        remediation: "Reduce excessive permissions, separate duties by role, replace personal/shared owner connections, and enforce row-level security at the data or API layer.",
        failIf: ["Shared connection lets a user perform actions or read data they cannot access directly.", "Service account has broad write/export/admin access without justification.", "Authorization is enforced only by frontend filtering."],
        fields: ["Data source", "Connection identity type", "Access type", "Role / group", "Privilege escalation risk", "Justification", "Evidence link"],
      }),
      makeControl({
        title: "Production Write / Delete / Approval Capability",
        severity: "Critical",
        description: "If the workload can write, delete, approve, submit, trigger, or modify production records, the blast radius must be explicitly understood.",
        steps: ["Identify write/delete/approval actions.", "Confirm business owner approval.", "Confirm rollback or reconciliation exists."],
        evidence: ["Permission matrix", "Business approval", "Rollback plan", "Reconciliation report"],
        remediation: "Restrict to read-only or add approval, rollback, and reconciliation controls.",
        fields: ["Write actions", "Delete actions", "Approval actions", "Rollback method", "Business owner approval"],
      }),
      makeControl({
        title: "Sensitive Data in Logs / Run History",
        severity: "High",
        description: "Sensitive data must not be written into logs, debug output, screenshots, prompt transcripts, run history, temp files, queue items, or exception messages.",
        steps: ["Review sample logs and run history.", "Check failed execution paths and exceptions.", "Confirm masking or redaction where needed."],
        evidence: ["Sample log review", "Run history screenshot", "Redaction config", "Exception handling review"],
        remediation: "Remove sensitive values from logs and replace with IDs, hashes, masked values, or references.",
        fields: ["Log source", "Sensitive fields checked", "Redaction method", "Sample reviewed", "Evidence link"],
      }),
      makeControl({
        title: "Data Retention and Cleanup",
        severity: "Medium",
        description: "Temporary outputs, files, exports, queues, local folders, and intermediate tables should not retain sensitive data longer than needed.",
        steps: ["Identify temporary and persistent storage.", "Document retention period.", "Confirm cleanup job or manual deletion process."],
        evidence: ["Retention requirement", "Cleanup job", "Storage location", "Owner confirmation"],
        remediation: "Add retention limit, cleanup process, or storage control before approval.",
        fields: ["Temporary storage", "Retention period", "Cleanup method", "Owner", "Evidence link"],
      }),
      makeControl({
        title: "Data Export / Download / File Transfer Control",
        severity: "High",
        description: "Export, download, unload, email attachment, file share, or transfer behavior must be documented and approved.",
        steps: ["Identify all export paths.", "Confirm who can trigger export.", "Confirm destination is approved and monitored."],
        evidence: ["Export configuration", "File transfer record", "Destination approval", "Monitoring evidence"],
        remediation: "Disable unnecessary exports or restrict destination and permissions.",
        fields: ["Export method", "Destination", "Triggering user/identity", "Data type", "Approval link"],
      }),
      makeControl({
        title: "Cross-Environment Data Movement",
        severity: "High",
        description: "Movement between DEV, TEST, PROD, sandbox, personal environments, or external systems must be controlled, especially when production data is involved.",
        steps: ["Identify environment boundaries.", "Confirm production data is not copied into lower environments without approval.", "Validate masking/sanitization if lower environment data is used."],
        evidence: ["Environment map", "Data movement approval", "Masking evidence", "Transfer log"],
        remediation: "Stop unapproved data movement or add masking and approval controls.",
        fields: ["Source environment", "Destination environment", "Data type", "Masking/sanitization", "Approval link"],
      }),
    ],
  },
  {
    id: "identity-access",
    title: "Identity & Authorization",
    icon: "🔐",
    controls: [
      makeControl({
        title: "Owner and Support Model",
        severity: "Medium",
        description: "Every internal app, script, flow, agent, or bot needs a clear business owner, technical owner, support contact, and backup owner.",
        steps: ["Identify business owner.", "Identify technical owner.", "Identify support group and backup owner."],
        evidence: ["Owner record", "Support group", "Runbook", "CMDB/app inventory entry"],
        remediation: "Assign accountable owners before approval or restrict to non-production use.",
        fields: ["Business owner", "Technical owner", "Support owner", "Backup owner", "Inventory link"],
      }),
      makeControl({
        title: "User Access Scope",
        severity: "High",
        description: "The user population must be documented: individual, team, department, enterprise-wide, guest, external, or cross-tenant.",
        steps: ["List users and groups.", "Identify broad access such as Everyone or all employees.", "Identify guest/external users."],
        evidence: ["Access list", "Group membership", "Sharing screenshot", "Approval record"],
        remediation: "Replace broad access with approved groups and remove unnecessary users.",
        fields: ["Users", "Groups", "Everyone/all employees", "Guest/external users", "Approval link"],
      }),
      makeControl({
        title: "Privileged Owner / Admin / Co-owner Access",
        severity: "High",
        description: "Owner, admin, maker, co-owner, folder admin, or high-privilege roles must be limited and periodically reviewed.",
        steps: ["List privileged users.", "Confirm business need.", "Confirm periodic review or recertification."],
        evidence: ["Privileged access list", "Review record", "Approval ticket"],
        remediation: "Remove unnecessary privileged owners or replace with group-based governance.",
        fields: ["Privileged users", "Role type", "Justification", "Review date", "Evidence link"],
      }),
      makeControl({
        title: "Service Account / Robot Account / Execution Role",
        severity: "High",
        description: "Any non-human identity must have documented owner, purpose, access scope, credential handling method, and review cadence.",
        steps: ["Document execution identity.", "Confirm it is not a developer personal account.", "Validate least privilege and access review cadence."],
        evidence: ["Service account record", "Robot account record", "Snowflake role grant", "Access review evidence"],
        remediation: "Move execution away from personal accounts and reduce excessive permissions.",
        fields: ["Service account", "Robot account", "Execution role", "App identity", "Owner", "Review cadence"],
      }),
      makeControl({
        title: "External User / Guest Access Review",
        severity: "Critical",
        description: "External or guest access to internal automations, agents, apps, flows, data, or APIs requires explicit approval and stronger review.",
        steps: ["Identify all external users or tenants.", "Confirm business justification.", "Confirm access expiration or review cadence."],
        evidence: ["Guest user list", "External sharing approval", "Access expiration", "Risk acceptance"],
        remediation: "Remove guest access or escalate to full review and business risk acceptance.",
        fields: ["External users", "External tenant", "Business justification", "Expiration date", "Approval link"],
      }),
      makeControl({
        title: "Access Removal / Joiner-Mover-Leaver Process",
        severity: "Medium",
        description: "Access removal should be clear when users change role, leave the team, or no longer support the app.",
        steps: ["Identify access owner.", "Confirm removal process.", "Confirm group-based access is tied to HR or IAM process where possible."],
        evidence: ["Access removal procedure", "IAM group", "Owner confirmation"],
        remediation: "Move access to managed groups or define manual review/removal process.",
        fields: ["Access owner", "Removal trigger", "Group/process", "Review frequency", "Evidence link"],
      }),
    ],
  },
  {
    id: "secrets",
    title: "Secrets & Credential Management",
    icon: "🧰",
    controls: [
      makeControl({
        title: "No Hardcoded Secrets",
        severity: "Critical",
        description: "Passwords, tokens, API keys, certificates, PATs, OAuth secrets, database credentials, and encoded secrets must not be hardcoded in code, notebooks, config, state files, XAML, Power Fx, exported packages, or logs.",
        steps: ["Scan source code, notebooks, XAML, Power Fx, exported solution/package files, config files, appsettings.json, .env files, state files, and compressed exports.", "Check for Base64 or otherwise encoded tokens and keys, not only obvious plaintext strings.", "Confirm any credential found in Git, exported package, or logs has been rotated, not merely deleted from code."],
        deepDive: ["For Tier 2/3, review the bootstrap problem: how does the automation obtain the first credential or vault token? Prefer managed identity, workload identity, IAM role, Snowflake secret, or platform-native credential store.", "For Tier 2/3, review catch blocks and error handling so Exception.ToString(), err.message, request headers, connection strings, or payloads do not write secrets to logs.", "For Tier 3, search SIEM/log platform for app-specific indicators such as password, bearer, x-api-key, authorization, secret, token, and connection string."],
        evidence: ["Secret scanner report with disposition", "Config/export package review", "Vault/secret store reference", "Rotation ticket", "7-day log search screenshot"],
        remediation: "Remove hardcoded secrets, rotate anything exposed in Git/export/logs, migrate to approved secret store, and add masking at logging or log-forwarding layer where needed.",
        failIf: ["Confirmed secret exists in code, notebook, config, XAML, export package, run history, or log.", "Vault token or credential used to access the secret store is itself hardcoded.", "Exposed credential was deleted but not rotated."],
        fields: ["Secret type", "Locations checked", "Encoded/base64 checked", "Scan result", "Vault/secret store", "Rotation ticket", "Log search evidence"],
      }),
      makeControl({
        title: "Approved Secret Store",
        severity: "High",
        description: "Secrets should be stored in an approved vault or platform secret store such as Key Vault, Snowflake secrets, UiPath Assets, or approved enterprise vault.",
        steps: ["Identify secret store.", "Confirm only approved identities can read secrets.", "Confirm secret reference is not leaked in logs."],
        evidence: ["Vault reference", "Secret store config", "Access policy", "Permission review"],
        remediation: "Move secrets to approved vault/secret store and restrict read permissions.",
        fields: ["Secret store", "Secret reference", "Read identities", "Access policy", "Evidence link"],
      }),
      makeControl({
        title: "Credential Rotation",
        severity: "High",
        description: "Credentials need an owner and rotation process, especially long-lived API keys, certificates, robot passwords, and service account secrets.",
        steps: ["Identify rotation owner.", "Document rotation frequency or trigger.", "Confirm emergency rotation process."],
        evidence: ["Rotation procedure", "Owner record", "Last rotation", "Expiration date"],
        remediation: "Define rotation ownership and rotate high-risk or unknown credentials.",
        fields: ["Credential owner", "Rotation frequency", "Last rotation", "Expiration date", "Emergency rotation process"],
      }),
      makeControl({
        title: "Secret Exposure in Logs / Screenshots / Run History",
        severity: "High",
        description: "Secrets should not appear in run history, prompts, screenshots, exception traces, queue data, logs, emails, or exported packages.",
        steps: ["Review logs and execution history.", "Check exception path.", "Check screenshots or prompt transcripts where applicable."],
        evidence: ["Log review", "Run history sample", "Screenshot review", "Transcript review"],
        remediation: "Mask/remove secret values and rotate anything exposed.",
        fields: ["Reviewed locations", "Exposure found", "Masking method", "Rotation action", "Evidence link"],
      }),
    ],
  },
  {
    id: "integration",
    title: "API / Connector / Integration",
    icon: "🌐",
    controls: [
      makeControl({
        title: "Integration Inventory",
        severity: "High",
        description: "All APIs, connectors, plugins, HTTP actions, webhooks, SaaS integrations, file transfers, and external endpoints must be documented with authentication, direction, payload, and approval status.",
        steps: ["List inbound and outbound integrations separately.", "Document authentication method, caller identity, permission scope, and data sent or received.", "Confirm external SaaS/vendor/platform approval exists before data transfer."],
        deepDive: ["For inbound webhooks, validate source authentication such as HMAC signature validation, OAuth, mTLS, signed token, or approved gateway—not only IP allowlist.", "For outbound API calls, inspect JSON payloads and confirm only required fields are sent externally.", "For Tier 3, document replay protection, timestamp/nonce validation, and failure handling for public or partner-facing endpoints."],
        evidence: ["Integration inventory", "Connector list", "API documentation", "Webhook/auth configuration", "Payload sample", "Vendor/data transfer approval"],
        remediation: "Remove or block unapproved integrations, add signed webhook validation or approved gateway protection, minimize outbound payloads, or escalate to full review.",
        failIf: ["Inbound webhook has no source authentication or signature validation.", "External endpoint receives full internal/customer record when only partial fields are needed.", "Unapproved SaaS or cross-tenant integration receives regulated/confidential data."],
        fields: ["Inbound APIs/webhooks", "Outbound APIs", "Connectors", "Plugins/actions", "Webhook authentication method", "Payload data fields", "Vendor approval"],
      }),
      makeControl({
        title: "External Endpoint Approval",
        severity: "High",
        description: "External endpoints, SaaS APIs, public URLs, webhooks, and cross-tenant paths require approval and data handling review.",
        steps: ["List external endpoints.", "Confirm endpoint owner/vendor.", "Confirm approval and data classification."],
        evidence: ["Endpoint list", "Vendor approval", "Architecture review", "Data transfer approval"],
        remediation: "Remove unapproved endpoints or escalate to vendor/platform review.",
        fields: ["Endpoint", "Vendor/owner", "Data sent", "Approval link", "Exception notes"],
      }),
      makeControl({
        title: "Authentication Method and Permission Scope",
        severity: "High",
        description: "Authentication method must be documented: OAuth app, delegated user, service account, API key, certificate, managed identity, robot credential, or Snowflake secret.",
        steps: ["Identify auth type.", "Confirm least-privilege permission scope.", "Confirm credential storage and rotation."],
        evidence: ["Auth config", "Permission scope", "Secret store", "Approval record"],
        remediation: "Reduce permissions and replace weak auth with approved enterprise pattern.",
        fields: ["Authentication method", "Permission scope", "Credential storage", "Rotation", "Evidence link"],
      }),
      makeControl({
        title: "External Data Transfer Minimization",
        severity: "Critical",
        description: "Data sent outside the platform or organization must be classified, minimized, and approved. This is where a tiny flow can become a data exfil path, very not cute.",
        steps: ["Identify data sent externally.", "Confirm business need.", "Confirm only necessary fields are sent."],
        evidence: ["Payload sample", "Data minimization review", "Business approval", "DLP/egress control"],
        remediation: "Remove sensitive fields, tokenize/mask data, or block external transfer.",
        fields: ["External destination", "Data fields", "Classification", "Minimization action", "Approval link"],
      }),
      makeControl({
        title: "Retry / Rate Limit / Duplicate Handling",
        severity: "Medium",
        description: "Automations that write, delete, approve, notify, or call transactional APIs must handle retry, rate limit, failure, and duplicate transaction behavior safely.",
        steps: ["Review retry count, backoff, timeout, and rate limit handling.", "Confirm idempotency control exists for write/delete/payment/approval/customer-notification operations.", "Confirm reconciliation detects duplicate, missing, partial, or failed transactions."],
        deepDive: ["For Tier 2/3, require an Idempotency-Key or equivalent unique transaction key when calling external APIs that may be retried.", "For Tier 2/3, validate behavior for HTTP 429, 5xx, timeout, and partial success responses.", "For Tier 3, confirm double-spend/double-submit prevention for payment, approval, customer-impacting, or regulated reporting workflows."],
        evidence: ["Retry config", "Error handling logic", "Idempotency key design", "API request sample", "Business reconciliation report"],
        remediation: "Add retry limits, exponential backoff, idempotency keys, deduplication logic, and reconciliation before production approval.",
        failIf: ["Retry can duplicate payment, approval, deletion, email, customer notification, or production write.", "No idempotency or reconciliation exists for transactional operations.", "5xx/timeout behavior is unknown."],
        fields: ["Retry behavior", "Rate limit handling", "Idempotency control", "Duplicate prevention", "Failure mode", "Reconciliation owner", "Evidence link"],
      }),
    ],
  },
  {
    id: "sdlc",
    title: "SDLC / Change Management",
    icon: "🔁",
    controls: [
      makeControl({
        title: "Source Control",
        severity: "High",
        description: "Source code, configuration, exported artifacts, packages, notebooks, or automation definitions should be stored in an approved repository.",
        steps: ["Confirm repository location.", "Confirm artifacts are complete enough for review/rebuild.", "Confirm repo ownership."],
        evidence: ["Repository link", "Exported solution/package", "Branch policy", "Owner record"],
        remediation: "Move artifacts to approved source control before production approval.",
        fields: ["Repository link", "Artifact types", "Branch", "Repo owner", "Evidence link"],
      }),
      makeControl({
        title: "DEV / TEST / PROD Separation",
        severity: "High",
        description: "Tier 1 and Tier 2 workloads should separate development, test, and production where feasible. Direct production editing is how governance turns into vibes.",
        steps: ["Identify environments.", "Confirm promotion path.", "Confirm production-only data is protected."],
        evidence: ["Environment map", "Deployment process", "Promotion record", "Approval ticket"],
        remediation: "Define separate environments or document why separation is not feasible with compensating controls.",
        fields: ["DEV", "TEST", "PROD", "Promotion method", "Exception notes"],
      }),
      makeControl({
        title: "Peer Review / Pull Request / Change Ticket",
        severity: "High",
        description: "Production change should require peer review, pull request, or change approval depending on platform maturity and risk tier.",
        steps: ["Confirm review record.", "Confirm reviewer is not only the developer.", "Confirm approval before production deployment."],
        evidence: ["PR link", "Reviewer", "Change ticket", "Release approval"],
        remediation: "Add review gate before production deployment.",
        fields: ["PR link", "Reviewer", "Change ticket", "Approval date", "Evidence link"],
      }),
      makeControl({
        title: "Security Scan Evidence",
        severity: "Medium",
        description: "Where source or export is available, run appropriate scans such as secrets scan, dependency scan, static analysis, UiPath Analyzer, or platform config review.",
        steps: ["Identify applicable scan type.", "Run scan before approval.", "Document open findings and disposition."],
        evidence: ["Secrets scan", "Dependency scan", "Static scan", "UiPath Analyzer", "Config review"],
        remediation: "Run missing scans and remediate or accept findings based on severity.",
        fields: ["Secrets scan", "Dependency scan", "Static scan", "Platform scan", "Open findings"],
      }),
      makeControl({
        title: "Rollback / Disable / Kill Switch",
        severity: "Medium",
        description: "Production automations need a documented way to pause, disable, kill, rollback, or compensate when behavior becomes unsafe. 出事時找不到紅色停止鈕，真的會變災難片。",
        steps: ["Document how to disable the app, flow, task, script, agent, job, or bot quickly without breaking unrelated shared services.", "Identify who can execute the kill switch, including L1/L2 support where appropriate.", "Confirm rollback, compensating transaction, snapshot restore point, or manual recovery path exists."],
        deepDive: ["For Tier 2/3, validate circuit breaker design such as DB flag, config switch, vault variable, feature flag, Orchestrator trigger disablement, or platform-native pause control.", "For Tier 3, test or walk through emergency stop and recovery with support owner.", "For Tier 3, document downstream impact if the automation is disabled mid-run."],
        evidence: ["Runbook", "Disable procedure", "Circuit breaker flag/config", "Rollback or compensating transaction procedure", "Support access evidence"],
        remediation: "Add a documented kill switch and recovery SOP in the IT operations knowledge base. If no native rollback exists, document safe disablement and compensating transaction procedure.",
        failIf: ["No one outside the original developer can stop the production automation.", "Automation can run in a loop or mass-update/delete without emergency stop.", "No rollback, restore, reconciliation, or compensating transaction exists for high-impact writes."],
        fields: ["Kill switch / circuit breaker", "Disable method", "Authorized operator", "L1/L2 support access", "Rollback method", "Compensating transaction", "Runbook link"],
      }),
      makeControl({
        title: "Material Change Re-review Trigger",
        severity: "Medium",
        description: "Re-review is required for new sensitive data, new external API, new service account, broader sharing, production write capability, or new critical process impact.",
        steps: ["Define material change criteria.", "Confirm owner understands trigger.", "Document next review cadence."],
        evidence: ["Procedure", "Owner attestation", "Review schedule", "Change policy"],
        remediation: "Add material change requirement to review record or app inventory.",
        fields: ["Material change criteria", "Owner attestation", "Review cadence", "Evidence link"],
      }),
    ],
  },
  {
    id: "logging-monitoring",
    title: "Logging / Monitoring / Response",
    icon: "📈",
    controls: [
      makeControl({
        title: "Audit Trail Availability",
        severity: "High",
        description: "User activity, admin changes, runs/jobs, data access, and failures should be traceable for investigation.",
        steps: ["Identify log sources.", "Confirm key events are captured.", "Confirm logs are accessible to support/security teams."],
        evidence: ["Log source", "Sample event", "Dashboard", "SIEM query"],
        remediation: "Enable platform logs or define compensating monitoring source.",
        fields: ["Log source", "Events captured", "Retention", "Access owner", "Evidence link"],
      }),
      makeControl({
        title: "Failure Alerting",
        severity: "High",
        description: "Critical automations should alert the owner when runs fail, jobs stop, queues back up, or scheduled tasks silently die.",
        steps: ["Identify failure modes.", "Confirm alert destination.", "Confirm owner receives alert."],
        evidence: ["Alert rule", "Notification config", "Sample alert", "Owner confirmation"],
        remediation: "Add email/Teams/SIEM alerting for failure and critical exception conditions.",
        fields: ["Failure mode", "Alert destination", "Alert owner", "Sample alert", "Evidence link"],
      }),
      makeControl({
        title: "Incident Contact and Runbook",
        severity: "Medium",
        description: "There should be a known incident contact and basic runbook for support, triage, manual recovery, and escalation.",
        steps: ["Identify incident contact.", "Confirm runbook exists.", "Confirm escalation path."],
        evidence: ["Runbook", "Support group", "Escalation matrix", "On-call/contact list"],
        remediation: "Document support contact and minimal recovery steps before production approval.",
        fields: ["Incident contact", "Support group", "Runbook link", "Escalation path", "Manual recovery steps"],
      }),
      makeControl({
        title: "Business Reconciliation / Output Validation",
        severity: "Medium",
        description: "For workflows that create or modify business records, reconciliation should detect duplicates, missing transactions, incorrect approvals, or partial failures.",
        steps: ["Identify business output.", "Confirm reconciliation owner.", "Confirm frequency and exception handling."],
        evidence: ["Reconciliation report", "Exception queue", "Business validation procedure"],
        remediation: "Add reconciliation report or exception review process.",
        fields: ["Business output", "Reconciliation method", "Frequency", "Owner", "Exception handling"],
      }),
    ],
  },
];

const platformSections = {
  "power-platform": [
    {
      id: "power-env-dlp",
      title: "Power Platform Environment & DLP",
      icon: "⚡",
      controls: [
        makeControl({
          title: "Environment Identification",
          severity: "High",
          description: "Identify whether the workload runs in Default, DEV, TEST, PROD, sandbox, or personal developer environment.",
          steps: ["Identify environment name and type.", "Confirm owner and purpose.", "Confirm production use is approved."],
          evidence: ["Power Platform Admin Center screenshot", "Environment record", "CoE inventory"],
          remediation: "Move production workloads to governed environment if needed.",
          fields: ["Default", "DEV", "TEST", "PROD", "Sandbox", "Developer env", "Evidence link"],
        }),
        makeControl({
          title: "DLP Policy Applied",
          severity: "High",
          description: "Confirm the correct Data Loss Prevention policy is applied to the environment and matches the intended risk posture.",
          steps: ["Identify DLP policy name.", "Review connector groups.", "Confirm policy is enforced for the environment."],
          evidence: ["DLP policy screenshot", "Connector classification", "Admin Center record"],
          remediation: "Apply correct DLP policy or move app to governed environment.",
          fields: ["DLP policy", "Environment", "Policy scope", "Exception notes", "Evidence link"],
        }),
        makeControl({
          title: "Business / Non-Business / Blocked Connector Review",
          severity: "High",
          description: "Review connector grouping and identify risky combinations such as business data source plus external/non-business connector.",
          steps: ["List business connectors.", "List non-business connectors.", "List blocked connectors and exceptions."],
          evidence: ["Connector list", "DLP policy export", "Exception approval"],
          remediation: "Move risky connectors to appropriate group or block unapproved connectors.",
          fields: ["Business connectors", "Non-Business connectors", "Blocked connectors", "Exceptions", "Evidence link"],
        }),
        makeControl({
          title: "HTTP / Custom / Premium Connector Review",
          severity: "Critical",
          description: "HTTP actions, custom connectors, premium connectors, and cross-tenant paths can create hidden API tunnels. HTTP triggers and naked webhooks are high-risk unless authenticated and protected.",
          steps: ["Identify HTTP actions, HTTP triggers, custom connectors, premium connectors, and cross-tenant endpoints.", "Confirm HTTP trigger requires Entra ID/Azure AD authentication or equivalent signed validation; anonymous public trigger should escalate.", "Review custom connector authentication such as OAuth 2.0, certificate, managed identity, or approved API key handling."],
          deepDive: ["For Tier 2/3, require APIM, WAF, signed webhook validation, authenticated trigger, or equivalent gateway control for externally reachable endpoints.", "For Tier 2/3, verify dynamic URLs are restricted by allowlist to reduce SSRF-style abuse.", "For Tier 3, inspect request/response payload fields and confirm sensitive data is minimized before leaving the tenant/platform."],
          evidence: ["Flow trigger config", "HTTP action list", "Custom connector definition", "Auth configuration", "APIM/WAF/gateway evidence", "Endpoint approval"],
          remediation: "Disable anonymous triggers, put external endpoints behind approved gateway protection, enforce OAuth/Entra ID/signed validation, and restrict dynamic URL targets.",
          failIf: ["Public HTTP trigger is unauthenticated.", "Custom connector sends secrets in URL or plaintext headers without approved secret handling.", "Dynamic URL can call arbitrary external/internal endpoints."],
          fields: ["HTTP action", "HTTP trigger auth", "Custom connector", "Premium connector", "Cross-tenant behavior", "Gateway / APIM / WAF", "Endpoint allowlist", "Approval link"],
        }),
        makeControl({
          title: "Default Environment Production Use",
          severity: "High",
          description: "Production apps in Default environment should be avoided unless formally approved and controlled. Default is the Power Platform 大雜院; oversharing risk is real.",
          steps: ["Check if workload is in Default environment.", "Confirm whether it is production or business-critical.", "Review sharing, connectors, DLP policy, ownership, and migration timeline."],
          deepDive: ["For Tier 2/3, require a dedicated environment plan with DEV/TEST/PROD or approved exception.", "For Tier 2/3, identify current technical debt and target migration date.", "For Tier 3, require platform owner/security approval to remain in Default."],
          evidence: ["Environment record", "App inventory", "DLP policy", "Sharing scope", "Exception approval", "Migration plan"],
          remediation: "Move production workloads to dedicated governed environments or document a time-bound exception with owner and migration plan.",
          failIf: ["Production or sensitive workload remains in Default without exception approval.", "Everyone/guest/broad sharing exists in Default for sensitive workflow.", "No migration owner or target date exists."],
          fields: ["In Default?", "Production use?", "Exception approval", "Migration owner", "Migration target date", "Dedicated environment plan", "Evidence link"],
        }),
      ],
    },
    {
      id: "power-app-flow-agent",
      title: "Power Apps / Flows / Agents",
      icon: "🧩",
      controls: [
        makeControl({
          title: "App / Flow / Agent Ownership",
          severity: "Medium",
          description: "If the question mentions app, flow, agent, and business owner, capture them separately instead of one vague note blob.",
          steps: ["Identify app owner.", "Identify flow owner.", "Identify agent owner.", "Identify business owner and support owner."],
          evidence: ["Power Platform inventory", "CoE inventory", "Maker record", "Owner confirmation"],
          remediation: "Assign missing owners before production approval.",
          fields: ["App owner", "Flow owner", "Agent owner", "Business owner", "Support owner", "Evidence link"],
        }),
        makeControl({
          title: "Sharing Scope and Co-owner Review",
          severity: "High",
          description: "Review sharing to users, groups, Everyone, guests, run-only users, and co-owners. Broad sharing can turn a small workflow into enterprise blast radius speedrun.",
          steps: ["List users and groups.", "Check Everyone or guest access.", "Review run-only users and co-owners."],
          evidence: ["Sharing screen", "Group membership", "Run-only user config", "Co-owner list"],
          remediation: "Replace broad sharing with approved groups and remove unnecessary co-owners.",
          fields: ["Users", "Groups", "Everyone", "Guests", "Run-only users", "Co-owners"],
        }),
        makeControl({
          title: "Flow Trigger Type",
          severity: "High",
          description: "Document whether flow is manual, scheduled, event-driven, webhook, or HTTP-triggered. HTTP or anonymous trigger usually escalates risk.",
          steps: ["Identify trigger type.", "Check authentication and caller.", "Confirm trigger cannot be abused."],
          evidence: ["Trigger config", "Flow definition", "Caller identity", "Approval record"],
          remediation: "Disable unauthenticated trigger or add authentication, validation, and rate control.",
          fields: ["Manual trigger", "Scheduled trigger", "Event-driven trigger", "Webhook", "HTTP trigger", "Caller identity"],
        }),
        makeControl({
          title: "Power Automate Run History Data Exposure",
          severity: "High",
          description: "Flow run history can expose payloads, approvals, emails, attachments, tokens, and customer data. Sensitive actions should use Secure Inputs and Secure Outputs where applicable.",
          steps: ["Review successful and failed run samples, including inputs, outputs, approval details, and error messages.", "Confirm actions handling sensitive data enable Secure Inputs and Secure Outputs where supported.", "Confirm secrets, tokens, headers, and sensitive payloads are not visible in run history."],
          deepDive: ["For Tier 2/3, inspect failed runs because exception output often leaks more than successful runs.", "For Tier 2/3, confirm child flows, approval actions, HTTP actions, and connector outputs do not expose sensitive data.", "For Tier 3, include prompt logs or agent transcripts if Copilot Studio is involved."],
          evidence: ["Run history sample", "Secure Inputs/Secure Outputs screenshots", "Failed run review", "Redaction/masking evidence", "Transcript review if applicable"],
          remediation: "Enable Secure Inputs/Secure Outputs, remove sensitive payloads from action outputs, use references instead of full data, and redesign flow logging if needed.",
          failIf: ["PII, PCI, NPI, secrets, bearer token, API key, or full customer payload appears in run history.", "Sensitive HTTP/action outputs are visible without Secure Outputs or equivalent control.", "Failed run exposes confidential request/response body."],
          fields: ["Run sample reviewed", "Failed run reviewed", "Secure Inputs enabled", "Secure Outputs enabled", "Sensitive fields", "Masking method", "Evidence link"],
        }),
        makeControl({
          title: "Copilot Studio Knowledge Sources",
          severity: "High",
          description: "Agent knowledge sources must be approved and scoped so the agent cannot expose confidential or regulated content to the wrong users.",
          steps: ["List knowledge sources.", "Confirm access trimming/authentication.", "Review publication channel and audience."],
          evidence: ["Knowledge source list", "Agent config", "Auth setting", "Publication channel"],
          remediation: "Remove unapproved knowledge sources and restrict audience/authentication.",
          fields: ["Knowledge sources", "Auth setting", "Audience", "Publication channel", "Evidence link"],
        }),
        makeControl({
          title: "Copilot Studio Actions / Plugins",
          severity: "Critical",
          description: "Agent actions and plugins can perform operations or call systems, so they must be reviewed like API integrations.",
          steps: ["List actions/plugins.", "Review endpoints and auth.", "Confirm least privilege and approval."],
          evidence: ["Action list", "Plugin config", "Connector list", "Endpoint approval"],
          remediation: "Disable or restrict unapproved actions/plugins; escalate if external data or privileged action exists.",
          fields: ["Actions", "Plugins", "Connectors", "Endpoint", "Permission scope", "Approval link"],
        }),
      ],
    },
  ],
  "snowflake-python": [
    {
      id: "snowflake-scope-rbac",
      title: "Snowflake Scope, RBAC & Data Controls",
      icon: "❄️",
      controls: [
        makeControl({
          title: "Snowflake Object and Warehouse Inventory",
          severity: "High",
          description: "Document database, schema, tables, stages, tasks, notebooks, procedures, and warehouse used by the workload.",
          steps: ["List Snowflake objects accessed or created.", "Identify production vs sandbox usage.", "Confirm warehouse and task schedule."],
          evidence: ["Object inventory", "Query history", "Task definition", "Warehouse usage"],
          remediation: "Create object inventory and remove unused objects or privileges.",
          fields: ["Database", "Schema", "Tables", "Stages", "Tasks", "Notebooks", "Procedures", "Warehouse"],
        }),
        makeControl({
          title: "Execution Role Least Privilege",
          severity: "Critical",
          description: "Snowflake code execution must not normally use ACCOUNTADMIN, SYSADMIN, SECURITYADMIN, or other nuclear-grade roles. Use a dedicated least-privilege execution role.",
          steps: ["Identify the exact execution role used by notebook, task, procedure, Snowpark app, or Streamlit app.", "Run or obtain SHOW GRANTS TO ROLE <execution_role>; and review database, schema, table, stage, warehouse, task, procedure, external access, and ownership grants.", "Confirm execution role does not bypass masking/row access policies or use admin roles for normal execution."],
          deepDive: ["For Tier 2/3, split read, write, and unload/export privileges where feasible.", "For Tier 3, verify ACCOUNTADMIN, SYSADMIN, SECURITYADMIN, ORGADMIN, and ownership-level grants are not used without explicit exception.", "For Tier 3, review query history for role switching and privileged operations."],
          evidence: ["SHOW GRANTS TO ROLE output", "Role review", "Query history", "Access approval", "Policy test result"],
          remediation: "Create a dedicated least-privilege role, remove admin/ownership-level execution grants, and separate export/write permissions from read permissions.",
          failIf: ["Normal execution uses ACCOUNTADMIN, SYSADMIN, SECURITYADMIN, or equivalent admin role.", "Execution role has broad OWNERSHIP, ALL PRIVILEGES, or unrestricted UNLOAD without justification.", "Execution role bypasses masking/row access policies without approval."],
          fields: ["Execution role", "Admin role used?", "SHOW GRANTS evidence", "Role grants", "Policy bypass risk", "Query history evidence", "Approval link"],
        }),
        makeControl({
          title: "Read / Write / Delete / Unload Privileges",
          severity: "Critical",
          description: "UNLOAD/export and write/delete permissions are high impact and need explicit business justification.",
          steps: ["Review read/write/delete/unload grants.", "Confirm business justification.", "Confirm monitoring/reconciliation."],
          evidence: ["Grant list", "Business approval", "Query history", "Monitoring evidence"],
          remediation: "Remove excessive grants and split read/write/export roles if needed.",
          fields: ["Read privileges", "Write privileges", "Delete privileges", "Unload/export privileges", "Justification"],
        }),
        makeControl({
          title: "Masking / Row Access Policy Respect",
          severity: "High",
          description: "The Python workload should respect masking policies, row access policies, and data classification controls.",
          steps: ["Identify policies applied to data.", "Confirm execution role behavior.", "Check whether outputs bypass masking."],
          evidence: ["Policy list", "Role test", "Query sample", "Data owner confirmation"],
          remediation: "Adjust role/policy design so workload cannot bypass required controls without approval.",
          fields: ["Masking policies", "Row access policies", "Execution role behavior", "Bypass approval", "Evidence link"],
        }),
        makeControl({
          title: "Temporary Tables / Stages / Query Output",
          severity: "High",
          description: "Temporary tables, stages, exports, UDF/UDTF intermediate output, and query results can expose sensitive data even when source tables are controlled.",
          steps: ["Review temp tables, transient tables, internal/external stages, exports, and query output.", "Confirm cleanup and permissions for temp/intermediate output.", "For Python UDFs/UDTFs, confirm batch/vectorized processing does not leak data across rows, sessions, or unprotected stages."],
          deepDive: ["For Tier 2/3, verify internal stages are encrypted and permission-scoped.", "For Tier 2/3, confirm temporary outputs do not bypass masking/row access controls.", "For Tier 3, inspect vectorized UDF/UDTF behavior for row independence and sensitive data handling."],
          evidence: ["Stage permissions", "Temp object design", "Cleanup procedure", "Query history", "UDF/UDTF code review"],
          remediation: "Restrict stage permissions, remove sensitive temp outputs, add cleanup, and redesign UDF/UDTF handling to avoid unprotected sensitive intermediate data.",
          failIf: ["Sensitive data is written to broadly accessible stage or temp table.", "Temporary output bypasses masking/row access policy without approval.", "Vectorized/batch processing leaks sensitive values across rows/sessions or writes unprotected files."],
          fields: ["Temp tables", "Stages", "Exports", "UDF/UDTF output", "Cleanup method", "Permission scope", "Masking/RLS impact"],
        }),
      ],
    },
    {
      id: "snowflake-python-code",
      title: "Snowflake Python Code & External Access",
      icon: "🐍",
      controls: [
        makeControl({
          title: "Repository / Notebook Sync",
          severity: "High",
          description: "Python scripts, notebooks, and stored procedure code should be synced or exported to approved source control for review and scanning.",
          steps: ["Confirm repository path.", "Confirm notebook export/sync process.", "Confirm production code is reviewable."],
          evidence: ["Repo link", "Notebook export", "Sync job", "PR review"],
          remediation: "Move code to repository or establish export/sync process before production approval.",
          fields: ["Repository link", "Notebook sync method", "Procedure code location", "PR link", "Evidence link"],
        }),
        makeControl({
          title: "Dependency Scan",
          severity: "Medium",
          description: "Python dependencies should be scanned with Snyk, pip-audit, or equivalent where applicable.",
          steps: ["Identify dependency list.", "Run dependency scan.", "Document open findings and disposition."],
          evidence: ["requirements.txt", "Snyk result", "pip-audit result", "Exception record"],
          remediation: "Upgrade vulnerable dependencies or document accepted risk.",
          fields: ["Dependency file", "Snyk result", "pip-audit result", "Open findings", "Exception notes"],
        }),
        makeControl({
          title: "Static Scan / Code Review",
          severity: "Medium",
          description: "Run static scan such as Semgrep, Bandit, CodeQL, or equivalent where applicable. Review dynamic SQL and unsafe input handling manually.",
          steps: ["Run static scan.", "Review dynamic SQL.", "Review input validation and exception handling."],
          evidence: ["Semgrep result", "Bandit result", "CodeQL result", "Manual review notes"],
          remediation: "Fix high-risk code issues or document compensating controls.",
          fields: ["Semgrep result", "Bandit result", "CodeQL result", "Dynamic SQL review", "Open findings"],
        }),
        makeControl({
          title: "External Access Integration and Egress Review",
          severity: "Critical",
          description: "Snowflake external network access must be narrowly scoped. Review EXTERNAL ACCESS INTEGRATION, ALLOWED_NETWORK_RULES, ALLOWED_AUTHENTICATION_SECRETS, secrets, endpoints, and data egress purpose.",
          steps: ["Identify CREATE EXTERNAL ACCESS INTEGRATION configuration used by the workload.", "Confirm ALLOWED_NETWORK_RULES is limited to specific vendor/API endpoints and not broad wildcard-style access.", "Confirm ALLOWED_AUTHENTICATION_SECRETS is limited to specific Snowflake Secrets or approved secret references, not broad all-style access."],
          deepDive: ["For Tier 2/3, confirm credentials are stored in Snowflake Secrets or approved external vault, not code/notebook/config.", "For Tier 2/3, inspect data payload sent externally and verify minimization.", "For Tier 3, require explicit egress approval and monitoring for regulated/confidential data."],
          evidence: ["External access integration DDL", "Network rule DDL", "Secret reference", "Endpoint approval", "Data egress approval", "Query/procedure code review"],
          remediation: "Restrict network rules to specific endpoints, restrict allowed secrets to specific secret objects, remove unnecessary egress, and rotate exposed credentials.",
          failIf: ["Network rule allows broad or arbitrary external destinations.", "Authentication secrets are broadly allowed instead of specific approved secrets.", "Sensitive data leaves Snowflake without approval, minimization, or monitoring."],
          fields: ["External access integration", "Allowed network rules", "Allowed authentication secrets", "Snowflake secret", "Endpoint", "Egress purpose", "Data sent externally"],
        }),
        makeControl({
          title: "Task Schedule and Failure Handling",
          severity: "Medium",
          description: "Scheduled tasks should have an owner, justified frequency, failure notification, and recovery process.",
          steps: ["Identify task schedule.", "Confirm failure alerting.", "Confirm recovery process."],
          evidence: ["Task definition", "Alert config", "Runbook", "Owner confirmation"],
          remediation: "Add failure notification and runbook before production approval.",
          fields: ["Task name", "Schedule", "Failure alert", "Owner", "Runbook link"],
        }),
      ],
    },
  ],
  uipath: [
    {
      id: "uipath-orchestrator",
      title: "UiPath Orchestrator & Robot Identity",
      icon: "🤖",
      controls: [
        makeControl({
          title: "Orchestrator Scope Inventory",
          severity: "High",
          description: "Document tenant, folder, process, package, trigger, queue, and robot type so the automation has a clear operational boundary.",
          steps: ["Identify tenant and folder.", "Document process, package, trigger, queue, and robot type.", "Confirm production vs non-production scope."],
          evidence: ["Orchestrator screenshot", "Process definition", "Queue configuration", "Trigger configuration"],
          remediation: "Complete Orchestrator inventory before approving production use.",
          fields: ["Tenant", "Folder", "Process", "Package", "Trigger", "Queue", "Robot type"],
        }),
        makeControl({
          title: "Robot Identity Not Personal Account",
          severity: "Critical",
          description: "UiPath robots must not run under a developer personal account. Unattended robots should use Service Mode Robot with a dedicated robot/service account where applicable.",
          steps: ["Identify attended vs unattended robot and execution account.", "Confirm unattended robot uses approved Service Mode Robot or approved enterprise execution pattern, not User Mode tied to a developer Windows account.", "Confirm robot account ownership, purpose, access scope, and review cadence."],
          deepDive: ["For Tier 2/3, verify credential and Windows session handling for unattended execution.", "For Tier 3, confirm break-glass/support access does not require the original developer's personal account.", "For Tier 3, review target application access granted to the robot account."],
          evidence: ["Robot account record", "Service Mode configuration", "IAM record", "Owner approval", "Access review"],
          remediation: "Move execution to an approved dedicated robot identity, remove personal account binding, and review target application permissions.",
          failIf: ["Unattended production robot uses a developer personal Windows/account identity.", "Only the original developer can run or recover the robot.", "Robot account ownership or access review cannot be proven."],
          fields: ["Robot account", "Robot mode", "User Mode or Service Mode", "Owner", "Target application access", "Review cadence", "Evidence link"],
        }),
        makeControl({
          title: "Unattended Robot Privileged Access",
          severity: "Critical",
          description: "Privileged unattended robots require clear approval, ownership, target application scope, and access review.",
          steps: ["Identify privileged access.", "Confirm business justification.", "Confirm review cadence and monitoring."],
          evidence: ["Access matrix", "Business approval", "Review record", "Monitoring evidence"],
          remediation: "Remove privileged access or escalate to Tier 1/full review.",
          fields: ["Privileged access", "Target application", "Justification", "Review cadence", "Approval link"],
        }),
        makeControl({
          title: "Folder / Queue / Machine Access Review",
          severity: "High",
          description: "Folder permissions, queue permissions, machine access, and target application access define the bot blast radius.",
          steps: ["Review folder permissions.", "Review queue permissions.", "Review machine and target app access."],
          evidence: ["Folder permissions", "Queue permissions", "Machine access", "Target app access"],
          remediation: "Restrict permissions and split folders/queues if needed.",
          fields: ["Folder permissions", "Queue permissions", "Machine access", "Target app access", "Evidence link"],
        }),
      ],
    },
    {
      id: "uipath-code-ops",
      title: "UiPath Code, Packages & Operations",
      icon: "📦",
      controls: [
        makeControl({
          title: "UiPath Source Control",
          severity: "High",
          description: "UiPath projects should store project.json, XAML files, config, package metadata, and dependency information in approved source control.",
          steps: ["Confirm project.json and XAML in repo.", "Confirm config files and package metadata.", "Confirm production release source."],
          evidence: ["Repository link", "project.json", "XAML files", "Package metadata"],
          remediation: "Move project to approved source control before production release.",
          fields: ["project.json location", "XAML location", "Config location", "Package metadata", "Repository link"],
        }),
        makeControl({
          title: "Package Dependencies and Approved Feeds",
          severity: "Medium",
          description: "Review package dependencies and approved feeds to avoid random package feed fiesta.",
          steps: ["List dependencies.", "Confirm approved feeds.", "Identify exceptions."],
          evidence: ["Dependency list", "Feed config", "Exception approval"],
          remediation: "Use approved feeds and pin/approve dependencies.",
          fields: ["Package dependencies", "Approved feeds", "Pinned versions", "Exceptions", "Evidence link"],
        }),
        makeControl({
          title: "UiPath Analyzer and Secrets Scan",
          severity: "Medium",
          description: "Run UiPath Analyzer and secrets scan before production release.",
          steps: ["Run UiPath Analyzer.", "Run secrets scan.", "Document open findings and disposition."],
          evidence: ["UiPath Analyzer result", "Secrets scan result", "Finding disposition"],
          remediation: "Remediate analyzer and secrets findings or document accepted exceptions.",
          fields: ["UiPath Analyzer result", "Secrets scan result", "Open findings", "Exception notes", "Evidence link"],
        }),
        makeControl({
          title: "Credential Storage in Orchestrator Assets / Vault",
          severity: "High",
          description: "Credentials should be stored in Orchestrator Assets or approved enterprise vault integration such as CyberArk, Azure Key Vault, HashiCorp Vault, or approved credential proxy—not XAML, project.json, config, screenshots, or notes.",
          steps: ["Identify credential assets and vault references used by the process.", "Confirm credential read permissions are limited to the robot/process scope.", "Review XAML, project.json, config files, and logs for hardcoded credentials."],
          deepDive: ["For Tier 2/3, provide vault integration configuration or Orchestrator credential proxy evidence.", "For Tier 2/3, rotate credentials if they ever appeared in source code, config, exported package, screenshots, or logs.", "For Tier 3, validate credential access is audited and periodically reviewed."],
          evidence: ["Orchestrator Asset record", "Vault integration screenshot", "Credential proxy configuration", "Secrets scan result", "Rotation procedure"],
          remediation: "Move credentials to approved store, restrict asset permissions, rotate exposed credentials, and remove hardcoded values from project artifacts.",
          failIf: ["Password or token exists in XAML, project.json, config, screenshot, queue item, or logs.", "Credential was exposed but not rotated.", "Any robot/process can read broad credential assets without scope restriction."],
          fields: ["Credential asset", "Credential store / vault", "Vault integration evidence", "Asset permissions", "Rotation process", "Secrets scan result", "Evidence link"],
        }),
        makeControl({
          title: "Queue Data / Screenshots / Job Logs / Exception Paths",
          severity: "High",
          description: "UiPath can leak sensitive data through queue items, job logs, exception messages, and execution media screenshots. This is especially risky for PII, PCI, NPI, and customer workflows.",
          steps: ["Review sample queue items, job logs, and exception paths.", "Confirm sensitive processes disable or restrict Execution Media / error screenshots where appropriate.", "Review duplicate transaction handling and business reconciliation."],
          deepDive: ["For Tier 2/3, verify queue item fields do not contain unnecessary sensitive payloads.", "For Tier 2/3, confirm Orchestrator Execution Media is disabled or restricted for sensitive workflows.", "For Tier 3, require reconciliation for financial/customer-impacting transactions."],
          evidence: ["Sample job logs", "Queue configuration", "Execution Media setting", "Exception handling design", "Business reconciliation process"],
          remediation: "Mask sensitive data, disable execution screenshots for sensitive workflows, reduce queue payloads, and add reconciliation/duplicate handling controls.",
          failIf: ["Execution Media captures screens with PII/PCI/NPI/secrets.", "Queue items contain full sensitive payload without need or retention control.", "Duplicate transaction handling is missing for write/payment/customer-impacting automation."],
          fields: ["Execution Media setting", "Screenshots", "Queue data", "Job logs", "Exception paths", "Duplicate transaction handling", "Reconciliation owner"],
        }),
        makeControl({
          title: "Bot Failure Notification and Runbook",
          severity: "Medium",
          description: "Failed jobs, queue exceptions, and unavailable robots should alert the support owner and have a documented runbook.",
          steps: ["Identify failure alerts.", "Confirm queue exception review.", "Confirm runbook and support owner."],
          evidence: ["Alert config", "Queue exception report", "Runbook", "Owner confirmation"],
          remediation: "Add alerting, exception review, and runbook before production approval.",
          fields: ["Failure alert", "Queue exception review", "Support owner", "Runbook link", "Evidence link"],
        }),
      ],
    },
  ],
};

function cx(...classes) {
  return classes.filter(Boolean).join(" ");
}

function severityClass(severity) {
  if (severity === "Critical") return "bg-red-100 text-red-700 border-red-200";
  if (severity === "High") return "bg-rose-100 text-rose-700 border-rose-200";
  if (severity === "Medium") return "bg-amber-100 text-amber-700 border-amber-200";
  return "bg-slate-100 text-slate-700 border-slate-200";
}

function statusMeta(status) {
  if (status === "Pass") return { label: "Pass", icon: "✓", color: "border-emerald-200 bg-emerald-50 text-emerald-800", dot: "bg-emerald-500" };
  if (status === "Fail") return { label: "Fail", icon: "×", color: "border-red-200 bg-red-50 text-red-800", dot: "bg-red-500" };
  if (status === "Partial") return { label: "Partial", icon: "◐", color: "border-amber-200 bg-amber-50 text-amber-800", dot: "bg-amber-500" };
  if (status === "N/A") return { label: "N/A", icon: "—", color: "border-slate-200 bg-slate-100 text-slate-700", dot: "bg-slate-500" };
  return { label: "Not Reviewed", icon: "○", color: "border-slate-200 bg-white text-slate-500", dot: "bg-slate-300" };
}

const DetailInput = React.memo(function DetailInput({ label, initialValue, onSave }) {
  const [value, setValue] = useState(initialValue || "");

  React.useEffect(() => {
    setValue(initialValue || "");
  }, [initialValue]);

  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</span>
      <input
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onBlur={() => {
          if (value !== (initialValue || "")) {
            onSave(value);
          }
        }}
        placeholder={`Enter ${label.toLowerCase()}`}
        className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:ring-4 focus:ring-slate-300"
      />
    </label>
  );
});

const DetailTextArea = React.memo(function DetailTextArea({ label, initialValue, onSave }) {
  const [value, setValue] = useState(initialValue || "");

  React.useEffect(() => {
    setValue(initialValue || "");
  }, [initialValue]);

  return (
    <label className="mt-4 block">
      <span className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</span>
      <textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onBlur={() => {
          if (value !== (initialValue || "")) {
            onSave(value);
          }
        }}
        rows={4}
        placeholder="Add extra context, assumptions, exception justification, compensating controls, remediation timeline, reviewer notes..."
        className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:ring-4 focus:ring-slate-300"
      />
    </label>
  );
});

function escapeMarkdown(value) {
  return String(value || "").replace(/\r?\n/g, "<br>").replace(/\|/g, "\\|");
}

function getTierLevel(triage, withinApprovedBoundary) {
  if (!withinApprovedBoundary) return 4;
  const values = Object.values(triage).filter(Boolean);
  if (values.includes("Tier 3")) return 3;
  if (values.includes("Tier 2")) return 2;
  return 1;
}

function tierInfo(level) {
  if (level === 4) {
    return {
      label: "Escalate — Full MSR / Enterprise Security Review",
      short: "Out of approved platform boundary",
      tone: "border-red-300 bg-red-50 text-red-800",
      outcome: "Stop lightweight review and route to full MSR / enterprise security review.",
    };
  }
  if (level === 3) {
    return {
      label: "Tier 3 — High Risk / Enhanced Review",
      short: "Security + Privacy + Compliance",
      tone: "border-red-300 bg-red-50 text-red-800",
      outcome: "Enhanced review by Security, Privacy, Compliance, platform owner, and business risk owner. May escalate to full MSR.",
    };
  }
  if (level === 2) {
    return {
      label: "Tier 2 — Medium Risk / Mini MSR",
      short: "CoE or Security Reviewer",
      tone: "border-amber-300 bg-amber-50 text-amber-800",
      outcome: "Mini MSR review by CoE, platform owner, or security reviewer. Evidence and remediation tracking required.",
    };
  }
  return {
    label: "Tier 1 — Low Risk / Basic Controls",
    short: "Register + Self-Attestation",
    tone: "border-emerald-300 bg-emerald-50 text-emerald-800",
    outcome: "Register workload, complete self-attestation, apply basic controls, record owner and decision.",
  };
}

const triageQuestions = [
  { id: "sensitive", label: "Sensitive, customer, PII, NPI, financial, confidential, or production data", tier: "Tier 2" },
  { id: "write", label: "Production write/delete/approve/submit capability", tier: "Tier 2" },
  { id: "external", label: "External API, SaaS, webhook, email, file transfer, custom connector, or external endpoint", tier: "Tier 2" },
  { id: "secret", label: "Service account, robot account, execution role, API key, OAuth secret, certificate, PAT, token, or password", tier: "Tier 2" },
  { id: "monitoringGap", label: "No clear change management, monitoring, owner, or recovery process for production use", tier: "Tier 2" },
  { id: "regulated", label: "PCI, high-risk privacy data, regulatory reporting, or compliance-impacting workload", tier: "Tier 3" },
  { id: "critical", label: "Customer, payment, financial reporting, regulatory, or critical operations impact", tier: "Tier 3" },
  { id: "public", label: "Internet-facing, public endpoint, unauthenticated trigger, guest access, or externally published app/agent", tier: "Tier 3" },
  { id: "privileged", label: "Privileged admin role, privileged bot, ACCOUNTADMIN/SYSADMIN-like access, or high-impact service account", tier: "Tier 3" },
];

const flowSteps = [
  { id: "A", title: "Start", text: "New automation or material change submitted." },
  { id: "B", title: "Approved Boundary?", text: "Is it within an approved platform and approved boundary? No → Full MSR / Enterprise Security Review." },
  { id: "C", title: "Select Automation Type", text: "Power Platform, UiPath, Snowflake Python/Snowpark/Streamlit/SP/Notebook, or other internal Python automation." },
  { id: "D", title: "Core Intake + Add-On", text: "Complete core intake plus the platform-specific add-on controls." },
  { id: "E", title: "Escalation Conditions", text: "Public exposure, privileged access, regulated data, critical process, or boundary exception → Tier 3 / Enhanced Review or Full MSR." },
  { id: "F", title: "Risk Factors", text: "Evaluate data sensitivity, business impact, integration complexity, privilege level, change management, and monitoring readiness." },
  { id: "G", title: "Determine Tier", text: "Low → Tier 1. Medium → Tier 2. High → Tier 3." },
  { id: "R", title: "Decision", text: "Approve, approve with conditions, escalate, reject, and track remediation." },
];

const mermaidDiagram = `flowchart TD
    A[Start: New automation or material change submitted] --> B{Is it within an approved platform and approved boundary?}

    B -- No --> Z1[Escalate to Full MSR / Enterprise Security Review]
    B -- Yes --> C[Select automation type]

    C --> C1[Power Platform App / Flow / Agent]
    C --> C2[UiPath Automation]
    C --> C3[Snowflake Python / Snowpark / Streamlit / SP / Notebook]
    C --> C4[Other Internal Python Automation]

    C1 --> D[Complete Core Intake + Platform Add-On]
    C2 --> D
    C3 --> D
    C4 --> D

    D --> E{Any immediate escalation conditions?}

    E -- Yes --> Z2[Tier 3 / Enhanced Review or Full MSR]
    E -- No --> F[Evaluate risk factors]

    F --> F1[Data sensitivity]
    F --> F2[Operational / business impact]
    F --> F3[Integration complexity]
    F --> F4[Privilege level]
    F --> F5[Change management / monitoring readiness]

    F1 --> G{Determine initial tier}
    F2 --> G
    F3 --> G
    F4 --> G
    F5 --> G

    G -- Low --> T1[Tier 1]
    G -- Medium --> T2[Tier 2]
    G -- High --> T3[Tier 3]

    T1 --> O1[Outcome: Register + Self-Attestation + Basic Controls]
    T2 --> O2[Outcome: Mini MSR Review by CoE / Security Reviewer]
    T3 --> O3[Outcome: Enhanced Review / Security + Privacy + Compliance]

    O1 --> P[Record decision and owner]
    O2 --> P
    O3 --> P

    P --> Q[Track remediation if needed]
    Q --> R[Approve / Approve with Conditions / Escalate / Reject]`;

function FlowPill({ children, tone = "slate" }) {
  const tones = {
    slate: "border-slate-200 bg-white text-slate-800",
    blue: "border-blue-200 bg-blue-50 text-blue-800",
    amber: "border-amber-200 bg-amber-50 text-amber-800",
    red: "border-red-200 bg-red-50 text-red-800",
    green: "border-emerald-200 bg-emerald-50 text-emerald-800",
    indigo: "border-indigo-200 bg-indigo-50 text-indigo-800",
  };
  return <div className={cx("rounded-2xl border px-4 py-3 text-center text-sm font-bold shadow-sm", tones[tone])}>{children}</div>;
}

function FlowArrow({ label }) {
  return (
    <div className="flex items-center justify-center gap-2 py-1 text-xs font-bold text-slate-500">
      {label && <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5">{label}</span>}
      <span className="text-lg">↓</span>
    </div>
  );
}

function FlowchartModal({ onClose }) {
  return (
    <div className="fixed inset-0 z-50 bg-slate-950/70 p-4 backdrop-blur-sm" onClick={onClose}>
      <div
        className="mx-auto flex max-h-[92vh] max-w-6xl flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-5">
          <div>
            <h2 className="text-2xl font-bold text-slate-950">Internal AppSec MSR Overview Flowchart</h2>
            <p className="mt-1 text-sm text-slate-600">Click outside this panel or use the X button to return to the form.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-bold text-slate-600 hover:bg-slate-100"
            aria-label="Close flowchart"
          >
            ✕
          </button>
        </div>

        <div className="overflow-auto p-6">
          <div className="grid gap-6 xl:grid-cols-[1fr_420px]">
            <section className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
              <div className="grid gap-2">
                <FlowPill tone="indigo">Start: New automation or material change submitted</FlowPill>
                <FlowArrow />
                <FlowPill tone="blue">Approved platform and approved boundary?</FlowPill>
                <div className="grid gap-3 md:grid-cols-2">
                  <div>
                    <FlowArrow label="No" />
                    <FlowPill tone="red">Escalate to Full MSR / Enterprise Security Review</FlowPill>
                  </div>
                  <div>
                    <FlowArrow label="Yes" />
                    <FlowPill tone="green">Select automation type</FlowPill>
                  </div>
                </div>

                <div className="mt-3 grid gap-3 md:grid-cols-4">
                  <FlowPill>Power Platform App / Flow / Agent</FlowPill>
                  <FlowPill>UiPath Automation</FlowPill>
                  <FlowPill>Snowflake Python / Snowpark / Streamlit / SP / Notebook</FlowPill>
                  <FlowPill>Other Internal Python Automation</FlowPill>
                </div>
                <FlowArrow />
                <FlowPill tone="blue">Complete Core Intake + Platform Add-On</FlowPill>
                <FlowArrow />
                <FlowPill tone="amber">Any immediate escalation conditions?</FlowPill>
                <div className="grid gap-3 md:grid-cols-2">
                  <div>
                    <FlowArrow label="Yes" />
                    <FlowPill tone="red">Tier 3 / Enhanced Review or Full MSR</FlowPill>
                  </div>
                  <div>
                    <FlowArrow label="No" />
                    <FlowPill tone="green">Evaluate risk factors</FlowPill>
                  </div>
                </div>

                <div className="mt-3 grid gap-3 md:grid-cols-5">
                  <FlowPill>Data sensitivity</FlowPill>
                  <FlowPill>Operational / business impact</FlowPill>
                  <FlowPill>Integration complexity</FlowPill>
                  <FlowPill>Privilege level</FlowPill>
                  <FlowPill>Change / monitoring readiness</FlowPill>
                </div>
                <FlowArrow />
                <FlowPill tone="blue">Determine initial tier</FlowPill>
                <div className="grid gap-3 md:grid-cols-3">
                  <div><FlowArrow label="Low" /><FlowPill tone="green">Tier 1</FlowPill></div>
                  <div><FlowArrow label="Medium" /><FlowPill tone="amber">Tier 2</FlowPill></div>
                  <div><FlowArrow label="High" /><FlowPill tone="red">Tier 3</FlowPill></div>
                </div>
                <div className="grid gap-3 md:grid-cols-3">
                  <FlowPill tone="green">Register + Self-Attestation + Basic Controls</FlowPill>
                  <FlowPill tone="amber">Mini MSR Review by CoE / Security Reviewer</FlowPill>
                  <FlowPill tone="red">Enhanced Review / Security + Privacy + Compliance</FlowPill>
                </div>
                <FlowArrow />
                <FlowPill tone="indigo">Record decision and owner → Track remediation → Approve / Conditions / Escalate / Reject</FlowPill>
              </div>
            </section>

            <aside className="space-y-4">
              <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
                <h3 className="text-lg font-bold text-slate-950">Tier Meaning</h3>
                <div className="mt-4 space-y-3">
                  {[1, 2, 3].map((level) => {
                    const info = tierInfo(level);
                    return (
                      <div key={level} className={cx("rounded-2xl border p-4", info.tone)}>
                        <div className="font-bold">{info.label}</div>
                        <div className="mt-1 text-sm font-semibold opacity-80">{info.short}</div>
                        <p className="mt-2 text-sm leading-6 opacity-90">{info.outcome}</p>
                      </div>
                    );
                  })}
                </div>
              </div>

              <details className="rounded-3xl border border-slate-200 bg-slate-950 p-5 text-slate-100 shadow-sm">
                <summary className="cursor-pointer text-sm font-bold">Mermaid source</summary>
                <pre className="mt-4 max-h-[420px] overflow-auto whitespace-pre-wrap text-xs leading-5 text-slate-200">{mermaidDiagram}</pre>
              </details>
            </aside>
          </div>
        </div>
      </div>
    </div>
  );
}

const basicCoreTitles = new Set([
  "Data Classification",
  "Data Source Inventory",
  "Owner and Support Model",
  "User Access Scope",
  "No Hardcoded Secrets",
  "Integration Inventory",
  "Source Control",
  "Audit Trail Availability",
  "Material Change Re-review Trigger",
]);

function minTierForControl(control) {
  if (basicCoreTitles.has(control.title)) return 1;
  if (control.severity === "Critical") return 3;
  if (control.severity === "High") return 2;
  return 1;
}

function controlAppliesToTier(control, tierLevel) {
  if (tierLevel === 4) return false;
  if (control.baseline) return true;
  return minTierForControl(control) <= tierLevel;
}

export default function InternalMiniMsrPage() {
  const platformOptions = [
    ...platforms,
    { id: "other-python", label: "Other Internal Python Automation", short: "Python / Scheduled Job / Internal Script", icon: "🐍" },
  ];

  const [activeTab, setActiveTab] = useState("review");
  const [selectedPlatform, setSelectedPlatform] = useState("power-platform");
  const [withinApprovedBoundary, setWithinApprovedBoundary] = useState(true);
  const [openGroups, setOpenGroups] = useState({});
  const [openCards, setOpenCards] = useState({});
  const [statusesById, setStatusesById] = useState({});
  const [details, setDetails] = useState({});
  const [triage, setTriage] = useState({});
  const [query, setQuery] = useState("");
  const [decision, setDecision] = useState("Approved with Conditions");
  const [reviewerNotes, setReviewerNotes] = useState("");
  const [exportMessage, setExportMessage] = useState("");
  const [showFlowchart, setShowFlowchart] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [applicationName, setApplicationName] = useState("");
  const [reviewerName, setReviewerName] = useState("");
  const [reviewDate, setReviewDate] = useState("");

  const selectedPlatformInfo = platformOptions.find((platform) => platform.id === selectedPlatform) || platformOptions[0];
  const tierLevel = getTierLevel(triage, withinApprovedBoundary);
  const tier = tierInfo(tierLevel);

  const rawSections = useMemo(() => {
    return [baselineSection, ...sharedSections, ...(platformSections[selectedPlatform] || [])];
  }, [selectedPlatform]);

  const reviewSections = useMemo(() => {
    return rawSections
      .map((section) => ({
        ...section,
        controls: section.controls.filter((control) => controlAppliesToTier(control, tierLevel)),
      }))
      .filter((section) => section.controls.length > 0);
  }, [rawSections, tierLevel]);

  const allReviewRows = useMemo(() => {
    let counter = 1;
    return reviewSections.flatMap((section) =>
      section.controls.map((control) => {
        const id = `${selectedPlatform}::tier-${tierLevel}::${section.id}::${control.title}`;
        const row = {
          id,
          platform: selectedPlatform,
          platformLabel: selectedPlatformInfo.label,
          sectionId: section.id,
          sectionTitle: section.title,
          sectionIcon: section.icon,
          number: counter,
          control,
        };
        counter += 1;
        return row;
      })
    );
  }, [reviewSections, selectedPlatform, selectedPlatformInfo.label, tierLevel]);

  const filteredSections = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return reviewSections;
    return reviewSections
      .map((section) => ({
        ...section,
        controls: section.controls.filter((control) => {
          return (
            control.title.toLowerCase().includes(q) ||
            control.description.toLowerCase().includes(q) ||
            control.severity.toLowerCase().includes(q) ||
            section.title.toLowerCase().includes(q)
          );
        }),
      }))
      .filter((section) => section.controls.length > 0);
  }, [reviewSections, query]);

  function statusOf(row) {
    return statusesById[row.id] || "Not Reviewed";
  }

  const overallReviewed = allReviewRows.filter((row) => statusOf(row) !== "Not Reviewed").length;
  const overallPass = allReviewRows.filter((row) => statusOf(row) === "Pass").length;
  const overallFail = allReviewRows.filter((row) => statusOf(row) === "Fail").length;
  const overallPartial = allReviewRows.filter((row) => statusOf(row) === "Partial").length;
  const overallNa = allReviewRows.filter((row) => statusOf(row) === "N/A").length;
  const overallAttention = overallFail + overallPartial;
  const overallProgress = allReviewRows.length ? Math.round((overallReviewed / allReviewRows.length) * 100) : 0;

  const findings = allReviewRows.filter((row) => ["Fail", "Partial"].includes(statusOf(row)));
  const passed = allReviewRows.filter((row) => statusOf(row) === "Pass");
  const pending = allReviewRows.filter((row) => statusOf(row) === "Not Reviewed");
  const notApplicable = allReviewRows.filter((row) => statusOf(row) === "N/A");

  function rowFor(sectionId, title) {
    return allReviewRows.find((row) => row.sectionId === sectionId && row.control.title === title);
  }

  function fieldKey(rowId, field) {
    return `${rowId}::${field}`;
  }

  function setDetail(rowId, field, value) {
    setDetails((prev) => ({ ...prev, [fieldKey(rowId, field)]: value }));
  }

  function getDetail(rowId, field) {
    return details[fieldKey(rowId, field)] || "";
  }

  function detailSummary(row) {
    const baseDetails = row.control.fields
      .map((field) => {
        const value = getDetail(row.id, field);
        return value ? `${field}: ${value}` : "";
      })
      .filter(Boolean);

    const additional = getDetail(row.id, "Additional information");
    if (additional) baseDetails.push(`Additional information: ${additional}`);
    return baseDetails.join("; ");
  }

  const sectionStats = useMemo(() => {
    return reviewSections.map((section) => {
      const rows = allReviewRows.filter((row) => row.sectionId === section.id);
      const reviewed = rows.filter((row) => statusOf(row) !== "Not Reviewed").length;
      const fail = rows.filter((row) => statusOf(row) === "Fail").length;
      const partial = rows.filter((row) => statusOf(row) === "Partial").length;
      const pct = rows.length ? Math.round((reviewed / rows.length) * 100) : 0;
      return {
        key: section.id,
        icon: section.icon,
        sectionTitle: section.title,
        total: rows.length,
        reviewed,
        fail,
        partial,
        pct,
      };
    });
  }, [reviewSections, allReviewRows, statusesById]);

  const riskRating = useMemo(() => {
    if (tierLevel === 4) return "Out of Scope / Escalate";
    if (overallReviewed < allReviewRows.length) return "Incomplete";
    if (overallFail > 0 || tierLevel === 3) return "High / Action Required";
    if (overallPartial > 0 || tierLevel === 2) return "Conditional";
    return "Low / Passed";
  }, [tierLevel, overallReviewed, allReviewRows.length, overallFail, overallPartial]);

  const markdown = useMemo(() => {
    const lines = [
      "# Internal AppSec MSR Review Details",
      "",
      "| Field | Value |",
      "|---|---|",
      `| Application Name | ${escapeMarkdown(applicationName)} |`,
      `| Platform | ${escapeMarkdown(selectedPlatformInfo.label)} |`,
      `| Reviewer | ${escapeMarkdown(reviewerName)} |`,
      `| Review Date | ${escapeMarkdown(reviewDate)} |`,
      `| Approved Platform Boundary | ${withinApprovedBoundary ? "Yes" : "No"} |`,
      `| Tier | ${escapeMarkdown(tier.label)} |`,
      `| Tier Meaning | ${escapeMarkdown(tier.outcome)} |`,
      `| Risk Rating | ${escapeMarkdown(riskRating)} |`,
      `| Decision | ${escapeMarkdown(decision)} |`,
      `| Progress | ${overallReviewed}/${allReviewRows.length} reviewed (${overallProgress}%) |`,
      `| Findings | ${overallAttention} |`,
      `| Reviewer Notes | ${escapeMarkdown(reviewerNotes)} |`,
      "",
      "## Control Results",
      "",
      "| # | Group | Control | Required | Severity | Status | Details |",
      "|---:|---|---|---|---|---|---|",
    ];

    allReviewRows.forEach((row) => {
      lines.push(
        `| ${row.number} | ${escapeMarkdown(row.sectionTitle)} | ${escapeMarkdown(row.control.title)} | ${row.control.required ? "Required" : "Optional"} | ${escapeMarkdown(row.control.severity)} | ${escapeMarkdown(statusOf(row))} | ${escapeMarkdown(detailSummary(row))} |`
      );
    });

    return lines.join(String.fromCharCode(10));
  }, [applicationName, selectedPlatformInfo.label, reviewerName, reviewDate, withinApprovedBoundary, tier.label, tier.outcome, riskRating, decision, overallReviewed, allReviewRows, overallProgress, overallAttention, reviewerNotes, statusesById, details]);

  async function copyMarkdown() {
    try {
      await navigator.clipboard.writeText(markdown);
      setExportMessage("Copied markdown to clipboard.");
    } catch (error) {
      setExportMessage("Copy failed. Select the markdown text and copy manually.");
    }
  }

  function downloadMarkdown() {
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "internal-appsec-msr-review.md";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    setExportMessage("Markdown file generated.");
  }

  function jumpToRow(row) {
    setActiveTab("review");
    setOpenGroups((prev) => ({ ...prev, [row.sectionId]: true }));
    setOpenCards((prev) => ({ ...prev, [row.id]: true }));
    setQuery("");
  }

  function resetReview() {
    setStatusesById({});
    setDetails({});
    setDecision("Approved with Conditions");
    setReviewerNotes("");
    setExportMessage("");
  }

  function resetPlatformChange(nextPlatform) {
    setSelectedPlatform(nextPlatform);
    setOpenGroups({});
    setOpenCards({});
    setStatusesById({});
    setDetails({});
    setQuery("");
  }

  function updateStatus(rowId, value) {
    setStatusesById((prev) => ({ ...prev, [rowId]: value }));
    setOpenCards((prev) => ({ ...prev, [rowId]: value === "Not Reviewed" }));
  }

  function renderRowList(title, rows, tone) {
    return (
      <section className={cx("rounded-3xl border p-5 shadow-sm", tone)}>
        <h3 className="text-xl font-bold">{title} ({rows.length})</h3>
        {rows.length === 0 ? (
          <p className="mt-8 text-center text-sm text-slate-500">No items in this bucket yet.</p>
        ) : (
          <div className="mt-4 max-h-[420px] space-y-2 overflow-auto pr-1">
            {rows.map((row) => {
              const meta = statusMeta(statusOf(row));
              return (
                <div key={row.id} className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white/70 px-3 py-2 text-sm">
                  <span className={cx("h-2.5 w-2.5 shrink-0 rounded-full", meta.dot)} />
                  <span className="w-10 shrink-0 font-bold text-slate-400">{String(row.number).padStart(2, "0")}</span>
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-semibold text-slate-900">{row.control.title}</div>
                    <div className="truncate text-xs text-slate-500">{row.sectionTitle} · {row.control.severity}</div>
                  </div>
                  <button type="button" onClick={() => jumpToRow(row)} className="shrink-0 rounded-xl px-3 py-1 text-xs font-bold text-indigo-600 hover:bg-indigo-50">
                    review →
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </section>
    );
  }

  return (
    <div className={cx("min-h-screen bg-slate-50 text-slate-950", darkMode && "msr-dark")}>
      <style>{`
        .msr-dark { background-color: #020617 !important; color: #e2e8f0 !important; }
        .msr-dark .bg-white { background-color: #0f172a !important; }
        .msr-dark .bg-slate-50 { background-color: #1e293b !important; }
        .msr-dark .bg-slate-100 { background-color: #334155 !important; }
        .msr-dark .border-slate-200 { border-color: #334155 !important; }
        .msr-dark .border-slate-100 { border-color: #1e293b !important; }
        .msr-dark .text-slate-950, .msr-dark .text-slate-900, .msr-dark .text-slate-800 { color: #f8fafc !important; }
        .msr-dark .text-slate-700, .msr-dark .text-slate-600, .msr-dark .text-slate-500 { color: #cbd5e1 !important; }
        .msr-dark input, .msr-dark textarea, .msr-dark select { background-color: #020617 !important; color: #e2e8f0 !important; border-color: #475569 !important; }
        .msr-dark input::placeholder, .msr-dark textarea::placeholder { color: #64748b !important; }
      `}</style>

      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <header className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-sm font-semibold text-slate-600">
                🛡️ Internal AppSec MSR · Approved Platform Scope
              </div>
              <h1 className="mt-5 max-w-4xl text-3xl font-bold tracking-tight sm:text-5xl">AppSec MSR Checklist</h1>
              <p className="mt-3 max-w-3xl text-base leading-7 text-slate-600">
                Minimum Security Review for Internal Applications on Approved Platforms — Moderate Depth
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:min-w-[520px]">
              <label>
                <span className="text-xs font-bold uppercase tracking-wide text-slate-500">Platform / Automation Type</span>
                <select
                  value={selectedPlatform}
                  onChange={(e) => resetPlatformChange(e.target.value)}
                  className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none focus:ring-4 focus:ring-slate-300"
                >
                  {platformOptions.map((platform) => (
                    <option key={platform.id} value={platform.id}>{platform.icon} {platform.label}</option>
                  ))}
                </select>
              </label>
              <label>
                <span className="text-xs font-bold uppercase tracking-wide text-slate-500">Approved Platform Boundary?</span>
                <select
                  value={withinApprovedBoundary ? "yes" : "no"}
                  onChange={(e) => setWithinApprovedBoundary(e.target.value === "yes")}
                  className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none focus:ring-4 focus:ring-slate-300"
                >
                  <option value="yes">Yes — use AppSec MSR</option>
                  <option value="no">No — escalate to Full MSR</option>
                </select>
              </label>
              <div className="flex flex-wrap gap-2 sm:col-span-2">
                <button type="button" onClick={() => setShowFlowchart((previous) => !previous)} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-100">
                  {showFlowchart ? "Hide Flowchart" : "Flowchart"}
                </button>
                <button type="button" onClick={() => setDarkMode((previous) => !previous)} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-100">
                  {darkMode ? "☀️ Light" : "🌙 Dark"}
                </button>
                <button type="button" onClick={resetReview} className="rounded-2xl border border-red-300 bg-white px-4 py-2 text-sm font-bold text-red-600 hover:bg-red-50">
                  Reset Review
                </button>
              </div>
            </div>
          </div>

          <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_280px] lg:items-center">
            <div className={cx("rounded-2xl border p-4", tier.tone)}>
              <div className="text-xs font-bold uppercase tracking-wide opacity-80">Current Tier</div>
              <div className="mt-1 text-xl font-bold">{tier.label}</div>
              <p className="mt-2 text-sm leading-6 opacity-90">{tier.outcome}</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="text-sm font-bold">{selectedPlatformInfo.icon} {selectedPlatformInfo.label}</div>
              <div className="mt-1 text-xs text-slate-500">{selectedPlatformInfo.short}</div>
              <div className="mt-3 text-xs text-slate-500">Applicable controls are automatically adjusted by tier.</div>
            </div>
          </div>

          <div className="mt-8 grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
            <div><div className="text-3xl font-bold">{overallReviewed}/{allReviewRows.length}</div><div className="text-sm text-slate-500">Reviewed</div></div>
            <div><div className="text-3xl font-bold text-emerald-500">{overallPass}</div><div className="text-sm text-slate-500">Pass</div></div>
            <div><div className="text-3xl font-bold text-red-500">{overallFail}</div><div className="text-sm text-slate-500">Fail</div></div>
            <div><div className="text-3xl font-bold text-amber-500">{overallPartial}</div><div className="text-sm text-slate-500">Partial</div></div>
            <div><div className="text-3xl font-bold text-slate-400">{overallNa}</div><div className="text-sm text-slate-500">N/A</div></div>
            <div className="text-right sm:text-left lg:text-right"><div className="text-4xl font-bold">{overallProgress}%</div><div className="text-sm text-slate-500">Complete</div></div>
          </div>
          <div className="mt-5 h-3 overflow-hidden rounded-full bg-slate-200">
            <div className="h-full rounded-full bg-indigo-500 transition-all" style={{ width: `${overallProgress}%` }} />
          </div>
        </header>

        {showFlowchart && <FlowchartModal onClose={() => setShowFlowchart(false)} />}

        <nav className="mt-6 flex gap-3 overflow-x-auto pb-2">
          {[
            { id: "review", label: "Review", icon: "🧾" },
            { id: "report", label: "Report", icon: "📋" },
          ].map((tab) => {
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => {
                  setActiveTab(tab.id);
                  setOpenGroups({});
                  setOpenCards({});
                  setQuery("");
                }}
                className={cx(
                  "rounded-2xl border px-5 py-3 text-left text-sm font-bold transition hover:-translate-y-0.5 hover:shadow-md",
                  active ? "border-indigo-400 bg-indigo-50 text-indigo-700 ring-2 ring-indigo-200" : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                )}
              >
                <div className="flex items-center gap-2 whitespace-nowrap text-base"><span>{tab.icon}</span><span>{tab.label}</span><span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-bold opacity-80">{tab.id === "review" ? `${overallReviewed}/${allReviewRows.length}` : "Export"}</span></div>
              </button>
            );
          })}
        </nav>

        {tierLevel === 4 && activeTab === "review" && (
          <section className="mt-6 rounded-3xl border border-red-300 bg-red-50 p-6 text-red-800 shadow-sm">
            <h2 className="text-2xl font-bold">Escalate to Full MSR / Enterprise Security Review</h2>
            <p className="mt-3 text-sm leading-6">This workload is outside the approved platform boundary. Do not continue with the lightweight Internal AppSec MSR. Route it to the full enterprise security review process.</p>
          </section>
        )}

        {activeTab === "report" ? (
          <main className="mt-6 space-y-6">
            <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-2xl font-bold">📋 MSR Report</h2>
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <label><span className="text-sm font-semibold text-slate-500">Application Name</span><input value={applicationName} onChange={(e) => setApplicationName(e.target.value)} placeholder="e.g. HR Onboarding Bot" className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:ring-4 focus:ring-slate-300" /></label>
                <label><span className="text-sm font-semibold text-slate-500">Platform</span><input value={selectedPlatformInfo.label} readOnly className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none" /></label>
                <label><span className="text-sm font-semibold text-slate-500">Reviewer</span><input value={reviewerName} onChange={(e) => setReviewerName(e.target.value)} placeholder="Your name" className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:ring-4 focus:ring-slate-300" /></label>
                <label><span className="text-sm font-semibold text-slate-500">Review Date</span><input type="date" value={reviewDate} onChange={(e) => setReviewDate(e.target.value)} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:ring-4 focus:ring-slate-300" /></label>
                <label className="md:col-span-2"><span className="text-sm font-semibold text-slate-500">Review Decision</span><select value={decision} onChange={(e) => setDecision(e.target.value)} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:ring-4 focus:ring-slate-300"><option>Approved</option><option>Approved with Conditions</option><option>Blocked / Rejected</option><option>Escalate to Full MSR</option><option>Risk Acceptance Required</option></select></label>
              </div>
              <label className="mt-4 block"><span className="text-sm font-semibold text-slate-500">Executive Notes</span><textarea value={reviewerNotes} onChange={(e) => setReviewerNotes(e.target.value)} rows={4} placeholder="Summary notes, major risks, approval conditions, remediation owner, target dates..." className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:ring-4 focus:ring-slate-300" /></label>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xl font-bold">Executive Summary</h2>
              <div className="mt-5 grid gap-4 md:grid-cols-4">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5 text-center"><div className="text-sm text-slate-500">Risk Rating</div><div className="mt-2 text-2xl font-bold">{riskRating}</div></div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5 text-center"><div className="text-sm text-slate-500">Completion</div><div className="mt-2 text-3xl font-bold text-amber-500">{overallProgress}%</div></div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5 text-center"><div className="text-sm text-slate-500">Findings</div><div className="mt-2 text-3xl font-bold text-red-500">{overallAttention}</div></div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5 text-center"><div className="text-sm text-slate-500">Tier</div><div className="mt-2 text-xl font-bold">{tier.label}</div></div>
              </div>
              <div className={cx("mt-5 rounded-2xl border p-4", tier.tone)}><div className="font-bold">{tier.short}</div><p className="mt-2 text-sm leading-6">{tier.outcome}</p></div>
              <div className="mt-6"><div className="text-sm font-bold uppercase tracking-[0.18em] text-slate-500">By Section</div><div className="mt-3 space-y-3">{sectionStats.map((stat) => (<div key={stat.key} className="grid gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-3 md:grid-cols-[260px_1fr_120px] md:items-center"><div className="text-sm font-semibold"><span className="mr-2">{stat.icon}</span>{stat.sectionTitle}</div><div className="h-2 overflow-hidden rounded-full bg-slate-200"><div className="h-full rounded-full bg-indigo-500" style={{ width: `${stat.pct}%` }} /></div><div className="text-right text-xs font-bold text-slate-500">{stat.reviewed}/{stat.total} · {stat.fail + stat.partial} issues</div></div>))}</div></div>
            </section>

            <div className="grid gap-6 xl:grid-cols-2">{renderRowList("Findings", findings, "border-red-200 bg-red-50")}{renderRowList("Passed", passed, "border-emerald-200 bg-emerald-50")}{renderRowList("Not Yet Reviewed", pending, "border-amber-200 bg-amber-50")}{renderRowList("N/A", notApplicable, "border-slate-200 bg-slate-50")}</div>

            <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="text-xl font-bold">Markdown Export</h2><p className="mt-1 text-sm text-slate-600">Copy or download the full report table for evidence packages, Jira, ServiceNow, or audit notes.</p></div><div className="flex gap-2"><button type="button" onClick={copyMarkdown} className="rounded-2xl border border-slate-200 px-4 py-2 text-sm font-bold hover:bg-slate-50">Copy Markdown</button><button type="button" onClick={downloadMarkdown} className="rounded-2xl border border-slate-950 bg-slate-950 px-4 py-2 text-sm font-bold text-white hover:bg-slate-800">Download .md</button></div></div>{exportMessage && <div className="mt-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">{exportMessage}</div>}<textarea value={markdown} readOnly rows={14} className="mt-4 w-full rounded-2xl border border-slate-200 bg-slate-950 px-4 py-3 font-mono text-xs leading-6 text-slate-100 outline-none" /></section>
          </main>
        ) : tierLevel !== 4 && (
          <main className="mt-6 grid gap-6 lg:grid-cols-[360px_1fr]">
            <aside className="space-y-6">
              <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-lg font-bold">Risk Triage</h2><p className="mt-2 text-sm leading-6 text-slate-600">Check what applies. Tier 1 = low/basic, Tier 2 = medium/Mini MSR, Tier 3 = high/enhanced review.</p><div className="mt-4 space-y-3">{triageQuestions.map((q) => { const checked = Boolean(triage[q.id]); return (<label key={q.id} className="flex cursor-pointer gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm leading-5 hover:bg-slate-100"><input type="checkbox" checked={checked} onChange={() => setTriage((prev) => ({ ...prev, [q.id]: checked ? "" : q.tier }))} className="mt-1 h-4 w-4" /><span><span className="font-semibold text-slate-800">{q.label}</span><span className={cx("ml-2 rounded-full px-2 py-0.5 text-xs font-bold", q.tier === "Tier 3" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700")}>{q.tier}</span></span></label>); })}</div></section>
              <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-lg font-bold">Applicable Controls</h2><div className="mt-4 space-y-3 text-sm"><div className="flex justify-between rounded-2xl bg-slate-50 px-4 py-3"><span>Platform</span><strong>{selectedPlatformInfo.label}</strong></div><div className="flex justify-between rounded-2xl bg-slate-50 px-4 py-3"><span>Tier</span><strong>{tierLevel}</strong></div><div className="flex justify-between rounded-2xl bg-slate-50 px-4 py-3"><span>Reviewed</span><strong>{overallReviewed}/{allReviewRows.length}</strong></div><div className={cx("flex justify-between rounded-2xl px-4 py-3", overallAttention ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700")}><span>Needs attention</span><strong>{overallAttention}</strong></div></div></section>
            </aside>

            <section className="space-y-6"><div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="text-xl font-bold">{selectedPlatformInfo.icon} {selectedPlatformInfo.label} Controls</h2><p className="mt-1 text-sm text-slate-600">Checks shown here are adjusted by the current tier. Open a group, expand a control, enter evidence, add context, then set status at the bottom.</p></div><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search controls..." className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:bg-white focus:ring-4 focus:ring-slate-300 sm:max-w-sm" /></div></div>
              {filteredSections.map((section) => { const sectionOpen = Boolean(openGroups[section.id]); const sectionRows = section.controls.map((control) => rowFor(section.id, control.title)).filter(Boolean); const sectionAttention = sectionRows.filter((row) => ["Fail", "Partial"].includes(statusOf(row))).length; const sectionReviewed = sectionRows.filter((row) => statusOf(row) !== "Not Reviewed").length; return (<div key={section.id} className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm"><button type="button" onClick={() => setOpenGroups((prev) => ({ ...prev, [section.id]: !sectionOpen }))} className="flex w-full items-center justify-between gap-4 p-5 text-left hover:bg-slate-50"><div className="flex items-center gap-4"><div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-xl">{section.icon}</div><div><div className="text-lg font-bold">{section.title}</div><div className="mt-1 text-sm text-slate-500">{sectionReviewed}/{sectionRows.length} reviewed · {sectionAttention} attention</div></div></div><span className="text-xl text-slate-400">{sectionOpen ? "▴" : "▾"}</span></button>{sectionOpen && (<div className="space-y-4 border-t border-slate-100 bg-slate-50 p-4">{section.controls.map((control) => { const row = rowFor(section.id, control.title); if (!row) return null; const status = statusOf(row); const cardOpen = Object.prototype.hasOwnProperty.call(openCards, row.id) ? Boolean(openCards[row.id]) : status === "Not Reviewed"; const meta = statusMeta(status); return (<article key={row.id} className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm"><div className="flex items-center gap-4 border-b border-slate-100 px-5 py-4"><div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 border-slate-300 text-sm font-bold text-slate-400">{meta.icon}</div><div className="w-10 shrink-0 text-lg font-semibold text-slate-400">{String(row.number).padStart(2, "0")}</div><button type="button" onClick={() => setOpenCards((prev) => ({ ...prev, [row.id]: !cardOpen }))} className="min-w-0 flex-1 text-left"><div className="flex flex-wrap items-center gap-2"><span className="text-lg font-bold text-slate-950">{control.title}</span><span className={cx("rounded-xl border px-3 py-1 text-xs font-bold tracking-wide", severityClass(control.severity))}>{control.severity.toUpperCase()}</span><span className={cx("rounded-xl border px-3 py-1 text-xs font-bold tracking-wide", control.required ? "border-slate-300 bg-slate-950 text-white" : "border-slate-200 bg-slate-100 text-slate-700")}>{control.required ? "REQUIRED" : "OPTIONAL"}</span><span className="rounded-xl border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-bold tracking-wide text-indigo-700">{control.baseline ? "BASELINE" : `TIER ${minTierForControl(control)}+`}</span><span className={cx("rounded-xl border px-3 py-1 text-xs font-bold tracking-wide", meta.color)}>{meta.label.toUpperCase()}</span></div></button><button type="button" onClick={() => setOpenCards((prev) => ({ ...prev, [row.id]: !cardOpen }))} className="rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-bold text-slate-500 hover:bg-slate-100">{cardOpen ? "▴" : "ⓘ"}</button></div>{cardOpen && (<div className="px-5 py-5"><div className="grid gap-6 xl:grid-cols-[1fr_360px]"><div><section><div className="text-sm font-bold uppercase tracking-[0.18em] text-slate-500">Description</div><p className="mt-2 text-sm leading-6 text-slate-700">{control.description}</p></section><section className="mt-6"><div className="text-sm font-bold uppercase tracking-[0.18em] text-slate-500">Verification Steps</div><ol className="mt-2 space-y-1.5 text-sm leading-6 text-slate-600">{control.steps.map((step, index) => (<li key={step} className="flex gap-4"><span className="w-6 shrink-0 text-slate-400">{index + 1}.</span><span>{step}</span></li>))}</ol></section>{control.deepDive && control.deepDive.length > 0 && (<section className="mt-6 rounded-2xl bg-purple-50 p-4"><div className="text-sm font-bold uppercase tracking-[0.18em] text-purple-700">Tier-Based Deep-Dive Checks</div><ul className="mt-2 space-y-1.5 text-sm leading-6 text-slate-700">{control.deepDive.map((item) => (<li key={item} className="flex gap-3"><span className="text-purple-500">◆</span><span>{item}</span></li>))}</ul></section>)}<section className="mt-6 rounded-2xl bg-blue-50 p-4"><div className="text-sm font-bold uppercase tracking-[0.18em] text-blue-700">Expected Evidence</div><p className="mt-2 text-sm leading-6 text-slate-700">{control.evidence.join(" · ")}</p></section>{control.failIf && control.failIf.length > 0 && (<section className="mt-4 rounded-2xl bg-red-50 p-4"><div className="text-sm font-bold uppercase tracking-[0.18em] text-red-700">Fail / Escalate If</div><ul className="mt-2 space-y-1.5 text-sm leading-6 text-slate-700">{control.failIf.map((item) => (<li key={item} className="flex gap-3"><span className="text-red-500">!</span><span>{item}</span></li>))}</ul></section>)}<section className="mt-4 rounded-2xl bg-emerald-50 p-4"><div className="text-sm font-bold uppercase tracking-[0.18em] text-emerald-700">Remediation Guidance</div><p className="mt-2 text-sm leading-6 text-slate-700">{control.remediation}</p></section></div><aside className="rounded-3xl border border-slate-200 bg-slate-50 p-4"><div className="space-y-3">{control.fields.map((field) => (<DetailInput key={`${row.id}::${field}`} label={field} initialValue={getDetail(row.id, field)} onSave={(newValue) => setDetail(row.id, field, newValue)} />))}</div><DetailTextArea label="Additional Information" initialValue={getDetail(row.id, "Additional information")} onSave={(newValue) => setDetail(row.id, "Additional information", newValue)} /><div className="mt-5 border-t border-slate-200 pt-4"><label className="block"><span className="text-sm font-semibold text-slate-500">Status</span><select value={status} onChange={(e) => updateStatus(row.id, e.target.value)} className={cx("mt-2 w-full rounded-xl border px-3 py-2 text-sm font-semibold outline-none focus:ring-4 focus:ring-slate-300", meta.color)}>{statuses.map((option) => (<option key={option} value={option}>{statusMeta(option).icon} {option}</option>))}</select></label><div className={cx("mt-4 rounded-2xl border p-4", meta.color)}><div className="flex items-center gap-2 text-sm font-bold"><span className={cx("h-2.5 w-2.5 rounded-full", meta.dot)} />{meta.label}</div><p className="mt-2 text-sm leading-6 opacity-90">{status === "Fail" && "Control is not satisfied. Add remediation owner and due date."}{status === "Partial" && "Control is partially satisfied. Add gap, compensating control, and due date."}{status === "Pass" && "Control appears satisfied. Add evidence reference."}{status === "N/A" && "Not applicable. Add reason why this does not apply."}{status === "Not Reviewed" && "No review result recorded yet."}</p></div></div></aside></div></div>)}</article>); })}</div>)}</div>); })}
            </section>
          </main>
        )}
      </div>
    </div>
  );
}
