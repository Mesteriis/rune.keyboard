# Q6 retrieval source-token boundaries

The source-boundary audit of the 1,800 frozen historical retrieval rows matched
1,799 rows unambiguously: nine targeted a prefix of a hyphenated token and
1,790 targeted standalone words. The nine full source tokens and their contexts
are retained and added to both registries. Two independent extractions were
byte-identical; the historical source and its attribution remain bound to the
retrieval fixture.

One row is unresolved: its public source has a suspended hyphen in a coordinated
expression ("аудио- и видеофайлов"). The boundary analyzer refuses to infer a
complete token. Its identifier and refusal are retained in `unresolved.json`;
its original article, context and target are already quarantined by the retrieval
history entries. No guessed full form or canonical family is registered. This
historical material cannot qualify a fresh holdout; Q6 coverage remains open.
