# HIPAA / GDPR checklist (practical, engineering-focused)

This is a **working checklist**, not legal advice. HIPAA/GDPR compliance also depends on contracts, operations, hosting, and incident response.

## 1) Data inventory & classification

- [ ] Define PHI/PII fields and where they live (DB tables, files, logs, backups).
- [ ] Document data flows (upload → processing → storage → access → export).
- [ ] Define retention periods (records, images, audit logs, backups) and deletion procedures.
- [ ] Define environments and data rules (no real PHI in non-prod unless approved + controlled).

## 2) Access control & authentication

- [ ] Enforce least privilege (roles + per-object access rules).
- [ ] MFA for staff/admin (IdP or Django admin protections).
- [ ] Strong password policy + lockout/rate-limit + session management.
- [ ] Break-glass / emergency access procedure (HIPAA).
- [ ] Periodic access reviews + termination process.

## 3) Audit logging & monitoring

- [ ] Audit log: login/logout/failed login, record/image view, download/export, create/update/delete.
- [ ] Ensure audit logs are append-only, protected, and retained per policy.
- [ ] Alerting for suspicious activity (bulk downloads, repeated 403/404 on sensitive endpoints).
- [ ] Time sync (NTP), consistent timestamps, and log integrity controls.

## 4) Encryption & key management

- [ ] Encryption in transit everywhere (TLS end-to-end; HSTS where appropriate).
- [ ] Encryption at rest:
  - [ ] Database storage encryption (managed DB encryption and/or disk encryption).
  - [ ] File/object storage encryption (S3 SSE-KMS or equivalent).
  - [ ] Backups/snapshots encrypted.
- [ ] Key management (KMS), key rotation, access separation, and secrets management (no secrets in git).

## 5) File uploads (medical images) & content handling

- [ ] Strict content-type validation (server-side).
- [ ] Size limits, timeouts, and virus/malware scanning (where required).
- [ ] Metadata handling:
  - [ ] DICOM de-identification policy (what is removed, what is retained, and why).
  - [ ] EXIF stripping for standard images (if supported).
- [ ] Private storage: prevent direct public access; serve via authenticated/authorized endpoints or signed URLs.

## 6) Application security hardening

- [ ] CSRF protection and secure cookie settings (Secure/HttpOnly/SameSite).
- [ ] Security headers (CSP, X-Frame-Options, Referrer-Policy, etc.).
- [ ] Input validation and output encoding; avoid leaking identifiers in errors.
- [ ] Dependency management (pinning/updates; SCA scanning).
- [ ] Admin hardening (separate admin domain/VPN, IP allowlists, MFA, disable “superuser for daily ops”).

## 7) GDPR-specific requirements

- [ ] Define lawful basis (consent/contract/legal obligation/vital interests/etc.).
- [ ] Privacy notice and transparency (what, why, retention, sharing).
- [ ] Data subject rights workflows (access/export, rectification, erasure, restriction, portability, objection).
- [ ] DPIA (if required) and records of processing activities.
- [ ] Processor agreements (DPAs) with vendors; cross-border transfer mechanisms where applicable.
- [ ] Breach notification process and timelines (GDPR 72-hour rule).

## 8) Incident response & operations

- [ ] Incident response runbooks (triage, containment, notification).
- [ ] Backups tested (restore drills) and disaster recovery plan.
- [ ] Secure deployment pipeline (CI/CD secrets, approvals, environment isolation).

