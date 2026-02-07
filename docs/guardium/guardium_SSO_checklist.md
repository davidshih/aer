Here is the step-by-step checklist for setting up Guardium SSO with Azure AD using only an IP address (The "Bypass" Method), formatted in Markdown.

---

# 📝 Guardium 12.2 SSO (Azure AD) - IP Bypass Checklist

This checklist is designed for **Lab/Testing environments** where you do not have a DNS record or a valid CA-signed certificate and are connecting via IP address.

### Prerequisites

* [ ] **Guardium Admin Access**: Login access to the GUI (admin or accessmgr).
* [ ] **Azure AD (Entra ID) Admin Access**: Ability to create "Enterprise Applications".
* [ ] **Guardium IP Address**: Assume your CM IP is `192.168.1.100` (Replace with your actual IP).
* [ ] **Test User Email**: You need a valid Azure AD user email, e.g., `david@company.com`.

---

### Phase 1: Azure AD (Entra ID) Configuration

*Goal: Tell Azure where to send the authentication data.*

1. [ ] **Log in to Azure Portal** > **Microsoft Entra ID**.
2. [ ] Navigate to **Enterprise applications** > **New application**.
3. [ ] Select **Create your own application**.
* **Name:** e.g., `Guardium-Lab-IP`.
* **Option:** Select **Integrate any other application you don't find in the gallery (Non-gallery)**.
* Click **Create**.


4. [ ] Once created, go to **Single sign-on** > **SAML**.
5. [ ] Edit **Basic SAML Configuration**:
* **Identifier (Entity ID):** `https://192.168.1.100:8443`
*(Note: Use HTTPS and include port 8443)*
* **Reply URL (Assertion Consumer Service URL):** `https://192.168.1.100:8443/ibm/saml20/defaultSP/acs`
*(This must be exact. One typo will cause failure)*
* Click **Save**.


6. [ ] Download Metadata:
* Under the **SAML Certificates** section, find **Federation Metadata XML**.
* Click **Download** and save it to your local machine.



---

### Phase 2: Guardium User Mapping

*Goal: Ensure Guardium recognizes the user sent by Azure.*

1. [ ] Log in to the Guardium GUI as `admin`.
2. [ ] Navigate to **Access Management** > **User Browser** > **Add User**.
3. [ ] Create a new user:
* **Username:** `david@company.com` (Must match the **UserPrincipalName** in Azure AD exactly).
* **Email:** Same as above.
* **Role:** Assign `user` or `admin` for testing.
* **Password:** Set a dummy password (it won't be used for SSO, but is required to create the account).
* Click **Add User**.



---

### Phase 3: Guardium SSO Configuration

*Goal: Import Azure's identity information into Guardium.*

1. [ ] Navigate to **Setup** > **Tools and Views** > **Access Management** > **Authentication**.
2. [ ] Scroll down to the **SAML** section.
3. [ ] **Upload Metadata:**
* Browse and select the Azure XML file downloaded in Phase 1.
* Click **Upload**.


4. [ ] Verify the fields (These should auto-populate):
* **SP entity ID:** `https://192.168.1.100:8443`
* **SP ACS URL:** `https://192.168.1.100:8443/ibm/saml20/defaultSP/acs`


5. [ ] **Enable and Save:**
* Check the **SAML Authentication** box (Enable) at the top of the section.
* Click **Save** at the bottom.



---

### Phase 4: The Critical Test (The "Certificate Bypass") ⚠️

*Goal: Prevent the browser from blocking the SSO redirection due to the "Not Secure" certificate.*

1. [ ] **Log out** of Guardium completely and close the tab.
2. [ ] Open a **New Browser Window** (Incognito/Private mode is recommended).
3. [ ] **Step A (The Bypass):**
* Type your Guardium IP in the address bar: `https://192.168.1.100:8443`.
* The browser will show a "Your connection is not private" (Not Secure) warning.
* Click **Advanced** > **Proceed to 192.168.1.100 (unsafe)**.
* **Stop here.** Once you see the Guardium login page, do not log in yet.
* *Why? You have now forced the browser to accept the invalid certificate for this session. Without this step, the SSO POST back to Guardium will be silently blocked.*


4. [ ] **Step B (The Login):**
* On the Guardium login page, look for a link that says **"Sign in with SAML"** (or similar). Click it.
* Alternatively, go to your Azure AD App's "User access URL".


5. [ ] **Success:**
* You should be redirected to Microsoft login -> Enter credentials -> Redirected back to Guardium.
* If you see the Guardium Dashboard, success!



---

### Troubleshooting Guide

* **Error: "Invalid User" or "Unauthorized"**
* **Cause:** The email Azure is sending does not match the username you created in Phase 2.
* **Fix:** Check the "Attributes & Claims" in Azure AD. Ensure `Unique User Identifier` is mapped to `user.userprincipalname`.


* **Error: Blank white screen / Stuck at `.../acs**`
* **Cause:** The browser blocked the POST request because the certificate is untrusted.
* **Fix:** You skipped **Phase 4, Step A**. You must manually visit the Guardium IP and "Accept the Risk" before attempting SSO.


* **Error: "The reply URL specified in the request does not match..."**
* **Cause:** The ACS URL in Azure AD does not match what Guardium expects.
* **Fix:** Check Phase 1, Step 5. Ensure there are no typos, extra spaces, or missing slashes in the URL.