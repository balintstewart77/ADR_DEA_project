# REDCap project setup checklist

- [ ] Create one non-longitudinal synthetic test project and record the actual REDCap version.
- [ ] Import `redcap_data_dictionary_candidate.csv`; record every warning.
- [ ] Confirm form order: assignment_admin, scratch_coder, project_owner.
- [ ] Enable only appropriate reviewer forms as surveys; assignment_admin is never reviewer-facing.
- [ ] Configure user rights: coders have no export, API, administrative-form, or other-record rights.
- [ ] Use individual owner survey links or another approved restricted routing method.
- [ ] Verify survey queue or record routing if used, and verify audit logging.
- [ ] Confirm hidden/read-only action tags and piping in the actual instance.
- [ ] Confirm no API token, live URL, or contact file is stored in Git.
- [ ] Import only synthetic assignments until pilot preparation is authorised.
- [ ] Verify one assignment per REDCap record/export row and shared hidden project clustering.
- [ ] Delete all synthetic records before pilot preparation.
