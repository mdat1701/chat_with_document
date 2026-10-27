Create a focused UML 2.0 use case diagram for **Chat với tài liệu (MVP-lite)** using .drawio XML format that can be imported directly into diagrams.net.

**SYSTEM OVERVIEW:**
The system lets an authenticated user upload text-based PDF files, monitor processing, ask questions over only their own ready documents, and receive a grounded answer with file/page citations or a clear not-found result. The user can delete documents; retention cleanup is automatic. Do not model long-term chat history, follow-up questions, feedback, dashboards, evaluation UI, document groups, OCR, or an admin screen.

**ACTORS (External Entities):**
Primary Actors:
1. Authenticated user - uploads documents, asks questions, checks citations, deletes documents

Secondary Actors:
2. Identity provider - authenticates the user
3. AI service - generates an answer from retrieved evidence
4. Retention scheduler - removes expired data

**USE CASES (Functional Requirements):**
Functional Areas:
- Access: Sign in, show no-access state
- Documents: Upload PDF, process PDF, show status, delete document
- Q&A: Ask question, retrieve only owned evidence, answer with citations, return not-found

**RELATIONSHIPS:**
- Include only required relationships such as asking a question including retrieval, evidence validation and citation rendering.
- Do not add optional P-01…P-08 feature use cases.

**SPECIFICATIONS:**
- Use correct UML notation
- Include system boundary box
- Proper actor stick figures
- Clear use case oval shapes
- Include all <<include>> and <<extend>> stereotypes where applicable

**TECHNICAL FORMAT:**
Generate the output as a .drawio file and save it into [your document folder such as ./docs]