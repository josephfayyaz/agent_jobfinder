# Claude Tool Calling Spec for Fact Sheet Intake

This document defines a practical Claude tool-calling setup for a job-matching application that builds and maintains a canonical `fact_sheet`.

Use this together with:

- [claude_fact_sheet_prompt_pack.md](/Users/youseffayyaz/Polito/Resume-CV/fact_sheet/claude_fact_sheet_prompt_pack.md)
- [fact_sheet_schema.json](/Users/youseffayyaz/Polito/Resume-CV/fact_sheet/fact_sheet_schema.json)
- [fact_sheet_renderer_spec.md](/Users/youseffayyaz/Polito/Resume-CV/fact_sheet/fact_sheet_renderer_spec.md)

## Goal

Claude should be able to:

1. inspect uploaded user materials
2. extract facts from CVs and related files
3. ask only missing high-value questions
4. generate a structured `fact_sheet` JSON
5. save both JSON and a human-readable plain-text fact sheet

This is the right architecture because the matcher should consume structured data, while recruiters, users, and downstream resume tools often still need readable text.

## Core Execution Model

Use Claude in a loop with tool calling enabled.

Recommended sequence:

1. App loads existing candidate data if present.
2. Claude reads uploaded materials using file tools.
3. Claude decides whether enough data exists.
4. If not enough, Claude calls the question tool.
5. After answers arrive, Claude updates the fact sheet.
6. Claude saves:
   - canonical JSON fact sheet
   - plain-text rendered master fact sheet
7. Matching engine consumes JSON only.

## Recommended Tool Set

These names are intentionally simple and stable.

### Tool: `list_candidate_files`

Purpose:
- return all user-uploaded files available for intake

Input schema:

```json
{
  "type": "object",
  "properties": {
    "candidate_id": {
      "type": "string"
    }
  },
  "required": ["candidate_id"]
}
```

Output shape:

```json
{
  "files": [
    {
      "file_id": "file_123",
      "name": "resume.pdf",
      "mime_type": "application/pdf"
    }
  ]
}
```

### Tool: `extract_candidate_file_text`

Purpose:
- extract normalized text from PDF, DOCX, TXT, or pasted content files

Input schema:

```json
{
  "type": "object",
  "properties": {
    "file_id": {
      "type": "string"
    }
  },
  "required": ["file_id"]
}
```

Output shape:

```json
{
  "file_id": "file_123",
  "name": "resume.pdf",
  "text": "Extracted file text here"
}
```

### Tool: `load_existing_fact_sheet`

Purpose:
- retrieve prior canonical fact sheet JSON for updates

Input schema:

```json
{
  "type": "object",
  "properties": {
    "candidate_id": {
      "type": "string"
    }
  },
  "required": ["candidate_id"]
}
```

Output shape:

```json
{
  "found": true,
  "fact_sheet": {}
}
```

### Tool: `ask_candidate_questions`

Purpose:
- ask concise follow-up questions when key matching data is missing

Input schema:

```json
{
  "type": "object",
  "properties": {
    "candidate_id": {
      "type": "string"
    },
    "questions": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "minItems": 1,
      "maxItems": 5
    },
    "reason": {
      "type": "string"
    }
  },
  "required": ["candidate_id", "questions"]
}
```

Output shape:

```json
{
  "status": "questions_sent"
}
```

### Tool: `save_fact_sheet_json`

Purpose:
- store the canonical structured fact sheet

Input schema:

```json
{
  "type": "object",
  "properties": {
    "candidate_id": {
      "type": "string"
    },
    "fact_sheet": {
      "type": "object"
    }
  },
  "required": ["candidate_id", "fact_sheet"]
}
```

Output shape:

```json
{
  "status": "saved",
  "fact_sheet_id": "fs_123"
}
```

### Tool: `render_fact_sheet_text`

Purpose:
- convert canonical JSON to the human-readable master fact sheet format

Input schema:

```json
{
  "type": "object",
  "properties": {
    "fact_sheet": {
      "type": "object"
    }
  },
  "required": ["fact_sheet"]
}
```

Output shape:

```json
{
  "rendered_text": "MASTER FACT SHEET\n..."
}
```

### Tool: `save_fact_sheet_text`

Purpose:
- store the rendered plain-text fact sheet

Input schema:

```json
{
  "type": "object",
  "properties": {
    "candidate_id": {
      "type": "string"
    },
    "rendered_text": {
      "type": "string"
    }
  },
  "required": ["candidate_id", "rendered_text"]
}
```

Output shape:

```json
{
  "status": "saved"
}
```

## Anthropic Tool Definition Format

If you are using Anthropic tool calling directly, tools can be represented in this style:

```json
[
  {
    "name": "list_candidate_files",
    "description": "List all uploaded files for a candidate.",
    "input_schema": {
      "type": "object",
      "properties": {
        "candidate_id": {
          "type": "string"
        }
      },
      "required": ["candidate_id"]
    }
  },
  {
    "name": "extract_candidate_file_text",
    "description": "Extract text from an uploaded file.",
    "input_schema": {
      "type": "object",
      "properties": {
        "file_id": {
          "type": "string"
        }
      },
      "required": ["file_id"]
    }
  },
  {
    "name": "ask_candidate_questions",
    "description": "Ask up to 5 concise high-value follow-up questions.",
    "input_schema": {
      "type": "object",
      "properties": {
        "candidate_id": {
          "type": "string"
        },
        "questions": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "minItems": 1,
          "maxItems": 5
        },
        "reason": {
          "type": "string"
        }
      },
      "required": ["candidate_id", "questions"]
    }
  }
]
```

## Tool Use Policy for Claude

These rules should be embedded in the system prompt or agent wrapper:

- Always try extraction before asking questions.
- Do not ask questions when the answer is already present in uploaded material.
- Ask questions only for fields that materially affect matching.
- Ask no more than 5 questions at once.
- If an existing fact sheet exists, update it instead of rebuilding.
- Save structured JSON first.
- Then render and save the human-readable text version.
- If data conflicts, preserve both values in `conflicts`.
- Do not silently overwrite strong prior evidence with weak new evidence.

## Suggested Orchestration Logic

Pseudo-flow:

```text
start
load_existing_fact_sheet(candidate_id)
list_candidate_files(candidate_id)
for each relevant file:
  extract_candidate_file_text(file_id)
Claude builds draft fact sheet
if high-impact gaps remain:
  ask_candidate_questions(...)
  wait for answers
  Claude updates draft fact sheet
save_fact_sheet_json(candidate_id, fact_sheet)
render_fact_sheet_text(fact_sheet)
save_fact_sheet_text(candidate_id, rendered_text)
end
```

## Minimum High-Impact Fields

Claude should try to fill these first:

- full name
- current location
- contact links
- target roles
- strongest experience
- education status
- work authorization
- availability
- preferred job locations
- languages
- strongest technical skills

If these are filled, matching can usually begin even if some optional fields remain missing.

## Return Strategy

Use this behavior:

- If enough data exists: return final JSON fact sheet and save it.
- If important gaps remain: call `ask_candidate_questions`.
- After answers return: update fact sheet and save both JSON and text forms.

Do not let Claude return long prose summaries during intake. The primary output should be structured.

## Recommended Storage Strategy

Store two artifacts per user:

1. `fact_sheet.json`
2. `master_fact_sheet.txt`

Why:

- JSON is for matching, scoring, filtering, and downstream app logic.
- TXT is for user review, recruiter review, resume generation, and manual editing.

Do not use the text file as the system of record. JSON should remain the source of truth.

## Good Default Assumptions

Safe assumptions Claude can make:

- normalize dates to `YYYY-MM` when only month/year are known
- map equivalent skill names to canonical labels
- infer role family from job title if obvious
- infer `usable_with_gaps` when strong career data exists but some constraints are missing

Unsafe assumptions Claude should not make:

- work authorization
- exact language levels
- salary expectations
- unverifiable metrics
- degree completion dates if not stated
- current employment status if unclear

## Practical Recommendation

If you want this to work well in production, keep the tool layer thin and deterministic. Let Claude decide what to ask and how to normalize, but keep file extraction, persistence, and user messaging as app-owned tools. That gives you flexibility without making the model responsible for storage logic.
