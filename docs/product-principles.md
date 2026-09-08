# Product principles

- Validate untrusted input at the boundary and return clear, field-oriented
  feedback.
- Keep the profile model immutable after validation so downstream scoring and
  tailoring features operate on stable data.
- Treat candidate information as sensitive; examples and tests use only
  fictional data and reserved `example.test` addresses.
