# Manual Validation Checklist

## Required Columns

Manual validation ledgers should include:

```text
candidate_id
pathway_uid
case_name
neutral_citation
canlii_url
official_source_url
case_exists_publicly
paragraphs_confirmed
quoted_text_confirmed
case_status_checked
appeal_history_checked
negative_treatment_checked
authority_level_confirmed
current_rule_text_confirmed
source_material_classified
use_purpose_classified
same_or_related_action_classified
privilege_screen_complete
non_party_privacy_screen_complete
sealed_or_restricted_access_checked
verified_by
verified_date
notes
```

## Verification Rules

Do not mark a pathway verified unless:

1. current rule text has been checked against CanLII or an official source;
2. case name and neutral citation are verified;
3. paragraph pins support the holding;
4. court level and hierarchy are confirmed;
5. appeal history/current status is checked;
6. contrary or limiting authorities are logged;
7. the pathway's safe formulation is narrower than the case holding;
8. do-not-overstate warning is included;
9. graph node and relationship targets use exact persistent UIDs;
10. no-write status remains unless a separate governed approval exists.

## Priority Checks

For each candidate holding, ask:

```text
what exactly did the case decide?
is the authority binding, persuasive, historical, or analogue?
does the paragraph support the exact pathway?
is the case interpreting current rules or predecessor rules?
has the case been reversed, limited, or distinguished?
what would opposing counsel say is the narrower reading?
what condition triggers this pathway?
what condition makes this pathway inapplicable?
```
