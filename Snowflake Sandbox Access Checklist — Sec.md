Snowflake Sandbox Access Checklist — Security Review & Git Integration Testing
Purpose: Minimum access required for an Application Security engineer to review Snowflake configuration and test Git integration with Azure DevOps in a sandbox environment.

Prerequisites

 Sandbox Snowflake account is provisioned
 Azure DevOps project and repo exist for testing
 Azure DevOps Personal Access Token (PAT) generated with Code (Read) scope
 Custom role created for security review (e.g., APPSEC_SANDBOX_ADMIN)


1. Account-Level Privileges
PrivilegePurposeGrant StatementCREATE INTEGRATION on ACCOUNTCreate API integration to connect to Azure DevOpsGRANT CREATE INTEGRATION ON ACCOUNT TO ROLE APPSEC_SANDBOX_ADMIN;IMPORTED PRIVILEGES on SNOWFLAKE databaseAccess ACCOUNT_USAGE views (login history, access history, policy references)GRANT IMPORTED PRIVILEGES ON DATABASE snowflake TO ROLE APPSEC_SANDBOX_ADMIN;

2. Database & Schema-Level Privileges
PrivilegePurposeGrant StatementUSAGE on target databaseAccess the sandbox databaseGRANT USAGE ON DATABASE <sandbox_db> TO ROLE APPSEC_SANDBOX_ADMIN;USAGE on target schemaAccess the schema for Git objectsGRANT USAGE ON SCHEMA <sandbox_db.git_test> TO ROLE APPSEC_SANDBOX_ADMIN;CREATE SECRET on schemaStore Azure DevOps PAT as a Snowflake secretGRANT CREATE SECRET ON SCHEMA <sandbox_db.git_test> TO ROLE APPSEC_SANDBOX_ADMIN;CREATE GIT REPOSITORY on schemaCreate Git repository stage objectGRANT CREATE GIT REPOSITORY ON SCHEMA <sandbox_db.git_test> TO ROLE APPSEC_SANDBOX_ADMIN;

3. Warehouse Access
PrivilegePurposeGrant StatementUSAGE on a warehouseExecute queries and Git fetch operationsGRANT USAGE ON WAREHOUSE <sandbox_wh> TO ROLE APPSEC_SANDBOX_ADMIN;

4. Network Configuration (if applicable)

 Confirm outbound access to Azure DevOps is allowed from Snowflake (relevant if using Network Rules / Network Policies)
 If the Snowflake account has a Network Policy restricting egress, ensure dev.azure.com is reachable


5. Git Integration Setup Steps (for testing)
Once access is granted, run through the following to validate:
5a. Create the API Integration
sqlCREATE OR REPLACE API INTEGRATION azdo_git_integration
  API_PROVIDER = git_https_api
  API_ALLOWED_PREFIXES = ('https://dev.azure.com/<org>/<project>')
  ALLOWED_AUTHENTICATION_SECRETS = ALL  -- or scope to specific secret
  ENABLED = TRUE;
5b. Create the Secret (store PAT)
sqlCREATE OR REPLACE SECRET azdo_pat_secret
  TYPE = password
  USERNAME = '<azure_devops_username>'
  PASSWORD = '<azure_devops_PAT>';
5c. Create the Git Repository Object
sqlCREATE OR REPLACE GIT REPOSITORY azdo_test_repo
  API_INTEGRATION = azdo_git_integration
  GIT_CREDENTIALS = azdo_pat_secret
  ORIGIN = 'https://dev.azure.com/<org>/<project>/_git/<repo>';
5d. Fetch and Verify
sqlALTER GIT REPOSITORY azdo_test_repo FETCH;

-- List branches
SHOW GIT BRANCHES IN azdo_test_repo;

-- List files at a branch
LS @azdo_test_repo/branches/main/;

-- Execute a file from the repo
EXECUTE IMMEDIATE FROM @azdo_test_repo/branches/main/deploy/00_schemas.sql;

6. Config Review Commands (Security Audit)
These commands help review the current Snowflake security posture:
sql-- List all existing integrations
SHOW INTEGRATIONS;

-- Inspect a specific integration
DESCRIBE INTEGRATION <integration_name>;

-- List all secrets in a schema
SHOW SECRETS IN SCHEMA <db.schema>;

-- List all Git repos in a schema
SHOW GIT REPOSITORIES IN SCHEMA <db.schema>;

-- Review account-level parameters
SHOW PARAMETERS IN ACCOUNT;

-- Check network policies
SHOW NETWORK POLICIES;

-- Review access history (requires SNOWFLAKE DB imported privileges)
SELECT * FROM snowflake.account_usage.access_history
  WHERE query_start_time > DATEADD(day, -7, CURRENT_TIMESTAMP())
  ORDER BY query_start_time DESC
  LIMIT 100;

-- Review login history
SELECT * FROM snowflake.account_usage.login_history
  WHERE event_timestamp > DATEADD(day, -7, CURRENT_TIMESTAMP())
  ORDER BY event_timestamp DESC
  LIMIT 100;

7. Key Security Considerations

 Read-only reminder: Snowflake Git integration is read-only (pull from repo only, no push back). It is NOT a full CI/CD pipeline.
 PAT rotation: Ensure the Azure DevOps PAT stored in the Snowflake secret has a defined expiration and rotation plan.
 Least privilege for PAT: The Azure DevOps PAT should only have Code (Read) scope — nothing more.
 Secret visibility: Any role with USAGE on the secret can use it in a Git repository object, but cannot read the raw PAT value. Verify RBAC accordingly.
 ALLOWED_AUTHENTICATION_SECRETS: Prefer scoping to specific secrets rather than using ALL in production.
 API_ALLOWED_PREFIXES: Restrict to the specific Azure DevOps org/project URL — do not use overly broad prefixes.
 Audit trail: Query ACCOUNT_USAGE.QUERY_HISTORY and ACCESS_HISTORY to verify who is using Git integration objects and when.


Summary: Minimum Role Grants (Copy-Paste Ready)
sql-- Create role
CREATE ROLE IF NOT EXISTS APPSEC_SANDBOX_ADMIN;

-- Account level
GRANT CREATE INTEGRATION ON ACCOUNT TO ROLE APPSEC_SANDBOX_ADMIN;
GRANT IMPORTED PRIVILEGES ON DATABASE snowflake TO ROLE APPSEC_SANDBOX_ADMIN;

-- Database / Schema
GRANT USAGE ON DATABASE <sandbox_db> TO ROLE APPSEC_SANDBOX_ADMIN;
GRANT USAGE ON SCHEMA <sandbox_db.git_test> TO ROLE APPSEC_SANDBOX_ADMIN;
GRANT CREATE SECRET ON SCHEMA <sandbox_db.git_test> TO ROLE APPSEC_SANDBOX_ADMIN;
GRANT CREATE GIT REPOSITORY ON SCHEMA <sandbox_db.git_test> TO ROLE APPSEC_SANDBOX_ADMIN;

-- Warehouse
GRANT USAGE ON WAREHOUSE <sandbox_wh> TO ROLE APPSEC_SANDBOX_ADMIN;

-- Assign to your user
GRANT ROLE APPSEC_SANDBOX_ADMIN TO USER <your_username>;
Replace <sandbox_db>, <sandbox_wh>, and <your_username> with actual values.