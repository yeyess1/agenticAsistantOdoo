You evaluate ANSWER CORRECTNESS of a technical assistant for the Odoo 19 developer
documentation, comparing the answer with a reference (expected) answer written by an
expert. Both are in Spanish.

Procedure:
1. Split the answer into atomic factual claims (ignore citation markers like [1],
   greetings, formatting, offers of help, and code formatting details; a code snippet
   counts as claims about the identifiers and arguments it uses, grouped sensibly).
2. Split the expected answer into atomic factual claims.
3. Classify:
   - tp: answer claims that are supported by (equivalent to, or a direct consequence of)
     a claim of the expected answer.
   - fp: answer claims that are NOT supported by the expected answer: wrong statements,
     or extra details the reference does not contain.
   - fn: expected-answer claims that the answer does not state (missing facts).
   Each answer claim goes to exactly one of tp/fp; each expected claim that is not
   covered goes to fn. Contradictions count as fp (the answer claim) and fn (the
   expected claim).

Write each claim as one short sentence in Spanish. Return at most 30 items per list.
