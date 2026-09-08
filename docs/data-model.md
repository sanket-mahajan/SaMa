# Candidate profile data model

The first supported record is `candidate_profile.v1`. It uses JSON at the
system boundary and becomes an immutable `CandidateProfile` in the application.

Required top-level fields are `schema_version`, `candidate_id` (UUID),
`full_name`, `email`, `skills`, and `experience`. Optional fields are `phone`
(E.164), `location`, `summary`, `links`, and `education`.

`skills` contains unique (case-insensitive) names and optional non-negative
`years_experience`. Each experience record requires `company`, `title`,
`start_date`, and `is_current`. Current roles omit `end_date`; past roles supply
one no earlier than `start_date`. Links must be absolute HTTP(S) URLs.

See `data/examples/candidate-profile.json` for a wholly synthetic record.
