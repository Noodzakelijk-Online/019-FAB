# Security Approach

This document outlines the security measures implemented in the Automated Bookkeeping Solution to protect sensitive data and credentials.

## 1. Secure Credential Management

All sensitive credentials (API keys, OAuth 2.0 tokens, website passwords) are stored and managed securely. Hardcoding of credentials is strictly prohibited.

- **Encryption**: Credentials are encrypted at rest using strong encryption algorithms (e.g., Fernet symmetric encryption from the `cryptography` library).
- **Environment Variables**: For deployment, credentials can be loaded from environment variables, which are not persisted in the codebase.
- **Secrets Management**: Integration with cloud-native secrets management services (e.g., Google Secret Manager) is supported for cloud deployments.
- **Restricted Access**: Access to credential storage is limited to authorized components of the system.

## 2. Data Protection

Sensitive financial data processed by the system is protected throughout its lifecycle.

- **Data Minimization**: Only necessary data is processed and stored.
- **Access Control**: Role-based access control (RBAC) is implemented to ensure that only authorized users or system components can access specific data or functionalities.
- **Audit Logging**: Comprehensive audit trails are maintained for all security-relevant operations, including data access, modifications, and system events. This allows for monitoring and forensic analysis.
- **Data Retention**: Processed documents and extracted data are retained only for the period required by legal and regulatory compliance, and then securely purged.

## 3. Secure Communication

Communication with external APIs and services is secured using industry-standard protocols.

- **HTTPS/TLS**: All network communication (e.g., with Gmail API, Google Drive API, Waveapps API, mijngeldzaken.nl) is conducted over HTTPS/TLS to ensure data in transit is encrypted and protected from eavesdropping and tampering.
- **OAuth 2.0**: Used for authentication and authorization with Google services (Gmail, Drive, Photos) to ensure secure delegated access without sharing user credentials directly.

## 4. Execution Environment Security

Security considerations for the execution environment are paramount.

- **Least Privilege**: The system operates with the minimum necessary permissions in its execution environment.
- **Containerization (Docker)**: For containerized deployments, Docker images are built with security best practices, minimizing the attack surface (e.g., using minimal base images, avoiding unnecessary packages).
- **Cloud Security**: For cloud deployments (Google Cloud Functions, Cloud Run), leverage Google Cloud's built-in security features, such as VPC networks, firewall rules, and IAM policies.
- **Regular Updates**: Dependencies and system components are kept up-to-date to patch known vulnerabilities.

## 5. Error Handling and Resilience

Robust error handling is implemented to prevent security vulnerabilities arising from unexpected states.

- **Input Validation**: All inputs are rigorously validated to prevent injection attacks and other forms of malicious input.
- **Graceful Degradation**: The system is designed to fail gracefully, preventing information leakage or system compromise during errors.
- **Automated Monitoring**: Continuous monitoring for unusual activities or potential security incidents.

## 6. Backup and Disaster Recovery

- **Automated Backups**: Regular, automated backups of critical data and configurations are performed.
- **Encrypted Backups**: Backups are encrypted to protect data confidentiality.
- **Disaster Recovery Plan**: A clear plan is in place for recovering data and restoring system operations in the event of a disaster.

## 7. User Interaction Security

- **Manual Review Interface**: When configured, the operations dashboard token is checked with constant-time comparison. FAB rejects cross-origin mutations even in tokenless loopback mode, rejects non-loopback `Host` headers for a tokenless service, and sets `SameSite=Lax`/`HttpOnly` session cookies. Tokenless sessions use an unpredictable process-local signing key. Opaque-origin form posts used by the in-app local browser require a signed session established by a prior FAB page load; opaque-origin API writes remain blocked. Reverse proxies must declare their trusted public origin with `operations.api_base_url`; forwarded host headers are not trusted implicitly.
- **Financial Response Hardening**: Dashboard and API responses are marked `no-store` and include content-type, frame, referrer, and content-security-policy headers so financial data is not cached or embedded by another site.
- **Audit Redaction**: Audit-event details pass through the same recursive credential redaction used by workflow, connector, and document metadata before SQLite persistence.
- **Browser Automation**: Playwright is used for browser automation, and its interactions are carefully controlled to prevent unintended actions or exposure of sensitive information.


