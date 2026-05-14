# Prompt Iteration Log

As part of the development process for the Finance Credit Follow-Up Email Agent, the LLM prompt went through several iterations to achieve the required reliability, tone accuracy, and safety. This document outlines the thought process and evolution of the system prompt.

## Iteration 1: The Naive Prompt
**Prompt:**
> "You are an AI assistant. A client named {client_name} owes {amount} on invoice {invoice_number}. They are {days} days late. Write an email to remind them to pay."

**Results \& Failures:**
- **Tone inconsistency:** The LLM would often be too aggressive for a 2-day late invoice or too polite for a 25-day late invoice.
- **Hallucinations:** The LLM would invent imaginary late fees, fake due dates, or fabricate bank account numbers in the email body.
- **Parsing issues:** The output was just raw text. Integrating it back into a JSON log or a database was impossible without brittle regex scraping.

## Iteration 2: Structured Output \& Basic Rules
**Changes Made:**
- Introduced JSON output format.
- Added explicit instructions not to hallucinate facts.

**Prompt Snippet:**
> "Write a payment reminder email. Output your response in JSON format with 'subject' and 'body' keys. Do not invent facts."

**Results \& Failures:**
- **Better parsing:** JSON output made it easier to log the results.
- **Still hallucinates:** "Do not invent facts" was too weak. The LLM would still occasionally invent a sign-off name or a random phone number.
- **Tone mismatch:** It still didn't understand *when* to be angry vs. polite.

## Iteration 3: The Matrix Approach (Adding Determinism)
**Changes Made:**
- Realized that asking the LLM to calculate "how angry to be based on days overdue" is an anti-pattern. AI is bad at deterministic math logic.
- Moved the logic to Python: Python calculates `days_overdue` and assigns a `Stage` (1 to 4).
- Passed the specific `Stage` and the desired `Tone` directly into the prompt.

**Prompt Snippet:**
> "This invoice is Stage 3. Use a 'Formal & Serious' tone. Inform them that credit terms may be impacted."

**Results \& Failures:**
- **Huge improvement:** Tone was perfectly matched to the days overdue.
- **JSON format drift:** The LLM would sometimes wrap the JSON in markdown code blocks (` ```json `) or add conversational filler like "Here is your email: { ... }", which broke Python's `json.loads()`.

## Iteration 4: Final Prompt (Strict Schema + Pydantic)
**Changes Made:**
- Upgraded the prompt to include a strict, rigid JSON schema definition.
- Added explicit "MANDATORY EMAIL CONTENT RULES" (e.g., must contain payment link, must use first name only for Stage 1).
- Implemented **Pydantic** in Python to strictly validate the LLM's output against the schema, rejecting anything that didn't perfectly match.

**Final Prompt Structure:**
> "You are a Finance Credit Follow-Up Email Agent...
> INPUT SCHEMA: ...
> TONE ESCALATION RULES: ...
> OUTPUT FORMAT -- STRICT JSON ONLY: { stage, action, tone_used, subject, body, justification }
> MANDATORY EMAIL CONTENT RULES: ... NEVER fabricate any field. If missing, write '[MISSING]'."

**Final Results:**
- **Zero hallucinations:** Injecting all variables via JSON and telling it to use `[MISSING]` eliminated fabricated data.
- **100% Parsing Success:** Pydantic validation ensures the pipeline never crashes due to format drift.
- **Perfect Tone:** The explicit rules per stage guarantee the exact professional escalation required by finance teams.
