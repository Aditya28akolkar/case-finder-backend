# DEBUG INVESTIGATION REPORT

## Issue 1 — Step 5: Legal Consequence Retrieval

### Verified Findings

**FILE:** `app/services/knowledge_search_service.py`
**FUNCTION:** `search_knowledge()` (lines 781-880)
**STATUS:** Step 5 IS executing, but debug output is not appearing in `retrieval_debug.log`

### Execution Path Traced

1. **Condition Check (lines 813-816):**
   - `asks_for_consequence` is computed from `consequence_query_text`
   - The query contains "consequence" and matches "did .* comply" pattern
   - **Result:** `asks_for_consequence = True`

2. **Branch Entry (line 819):**
   - Print statement: `print("\n>>> STEP 5 BRANCH ENTERED <<<", flush=True)`
   - **Result:** This prints to stdout, NOT to `retrieval_debug.log`
   - **Root cause of missing debug output:** Debug prints go to console, not log file

3. **Function Call (lines 823-830):**
   - `retrieve_legal_consequences()` IS called
   - **Result:** Function executes successfully

4. **Function Execution (lines 896-1059 in `legal_retrieval_service.py`):**
   - Returns 10 documents
   - These documents are logged to stdout, not to `retrieval_debug.log`

5. **Merge (lines 855-863):**
   - Consequence documents are merged with existing candidates
   - **Result:** Candidate pool grows from 30 to 40

### Actual Retrieved Consequence Documents

The function retrieved these 10 documents:

| ID | Page | Chapter | Content Preview | Relevance to RHP Timeline |
|----|------|---------|----------------|---------------------------|
| 11470 | 23 | 11_Companies_Incorporated_Outside_India | Companies incorporated outside India prospectus provisions | ❌ Wrong chapter |
| 10630 | 56 | 03_Prospectus_and_Allotment | Prospectus examination question | ❌ Not about RHP filing |
| 10626 | 52 | 03_Prospectus_and_Allotment | Default in filing return of allotment - liability/penalty | ❌ Wrong provision (return of allotment, not RHP filing) |
| 10614 | 40 | 03_Prospectus_and_Allotment | Punishment for default - liability/penalty | ❌ Generic prospectus default, not RHP-specific |
| 10597 | 23 | 03_Prospectus_and_Allotment | Abridged prospectus - penalty for section 33 non-compliance | ❌ Wrong section (33, not 32) |
| 10588 | 14 | 03_Prospectus_and_Allotment | Expert statement requirements | ❌ Not about consequences |
| 10601 | 27 | 03_Prospectus_and_Allotment | Liability for offence | ❌ Generic prospectus offence |
| 10604 | 30 | 03_Prospectus_and_Allotment | Liability for offence | ❌ Generic prospectus offence |
| 10675 | 39 | 04_Share_Capital_and_Debentures | Share capital provisions | ❌ Wrong chapter |
| 10602 | 28 | 03_Prospectus_and_Allotment | Liability for offence | ❌ Generic prospectus offence |

### Why the Consequence Documents Are Wrong

**FILE:** `app/services/legal_retrieval_service.py`
**FUNCTION:** `retrieve_legal_consequences()` (lines 896-1059)

**Problem:** The function uses a generic consequence-term search strategy:

1. **Line 927-945:** It identifies "concept anchors" from `LEGAL_CONCEPTS`
   - For RHP, it finds: "red herring prospectus", "RHP", "subscription list", "public offer"
   - These are correct for identifying RHP-related documents

2. **Line 983-986:** It searches for consequence terms in those documents:
   - Terms: "penalty", "liable", "liability", "punishment", "offence", etc.
   - This matches ANY prospectus document that mentions penalties

3. **Line 1004-1005:** It prioritizes documents with consequence terms:
   - Score += min(len(matched_consequences) * 3, 15)
   - This boosts documents that mention penalties, regardless of whether those penalties apply to RHP filing

**Root Cause:** The function retrieves documents that:
- Are about prospectus (correct)
- Mention penalties (correct)
- But do NOT specify penalties for RHP filing timing violations (incorrect)

The ICAI material does NOT explicitly state the consequence of filing an RHP less than 3 days before the subscription list opens. It only states the requirement.

### Do These Documents Reach the LLM?

From the test execution output, the consequence documents ARE merged into the candidate pool (40 candidates). However, after reranking and context filtering, only 5 documents remain in the final LLM context (llm_context_debug.txt shows 11 sources, but that's from a different run).

The key issue: Even if consequence documents reach the LLM, they describe penalties for OTHER prospectus violations (section 33 abridged prospectus, return of allotment defaults, mis-statements), NOT for RHP filing timing violations.

---

## Issue 2 — Unsupported Legal Conclusions

### The Problem

The chatbot correctly identifies timely filing but adds:
> "Because the filing was timely, no penalty or adverse consequence arises under the Act."

This conclusion is NOT supported by the retrieved source (ID 10596, page 22), which only states:
> "A company proposing to issue a red herring prospectus shall file it with the Registrar at least three days prior to the opening of the subscription list and the offer."

### Why the Model Makes Unsupported Claims

**FILE:** `app/services/llm_service.py`
**FUNCTION:** `generate_answer()` (lines 68-249)

**Root Cause:** The LLM prompt contains conflicting instructions:

1. **Lines 83-86 (User prompt):**
   ```
   6. Do not conclude that no penalty, liability, or adverse consequence
   exists merely because the facts satisfy the rule being tested.
   State a legal consequence only when the supplied ICAI material
   explicitly supports it.
   ```

2. **Lines 221-224 (System message):**
   ```
   A conclusion that a requirement was satisfied does not establish
   that no other penalty, liability, or adverse consequence exists.
   Do not claim that no consequence arises unless the supplied ICAI
   material explicitly supports that claim.
   ```

These instructions are CORRECT and should prevent the unsupported claim.

However, the LLM is still making the unsupported claim. This suggests:

**Hypothesis 1:** The LLM is using its pre-training knowledge about general legal principles (compliance = no penalty) rather than strictly following the instruction to only use supplied material.

**Hypothesis 2:** The prompt is too long/complex, and the model is not following all instructions consistently.

**Hypothesis 3:** The presence of unrelated consequence documents (from Step 5) confuses the model into thinking consequence information is available.

### What Actually Reaches the LLM

From `llm_context_debug.txt`, the LLM receives:
- SOURCE 1 (Page 21): Information memorandum (not relevant)
- SOURCE 2 (Page 8): Prospectus definition (not relevant)
- SOURCE 3 (Page 22): **The correct RHP rule** - "at least three days prior"
- SOURCE 4 (Page 57): Minimum subscription (not relevant)
- SOURCE 5 (Page 20): Shelf prospectus (not relevant)
- SOURCE 6 (Page 19): Advertisement of prospectus (not relevant)
- SOURCE 7 (Page 23): Abridged prospectus - mentions penalty for section 33 (WRONG SECTION)
- SOURCE 8-10: Other irrelevant content

**Critical:** SOURCE 7 mentions a penalty for section 33 (abridged prospectus), which is unrelated to section 32 (RHP filing timing). The LLM may be incorrectly inferring that "prospectus penalties exist in the material" and applying them to the RHP scenario.

### The Actual Execution Path

1. **Retrieval:** Correct rule (ID 10596) is retrieved at rank 3 after reranking
2. **Context filtering:** The rule survives filtering
3. **LLM context:** The rule is in SOURCE 3
4. **LLM answer:** Correctly applies the rule (Tuesday to Friday = 3 days = compliant)
5. **Unsupported addition:** "no penalty or adverse consequence arises"

### Why the Model Adds the Unsupported Claim

The model likely reasons:
1. Facts satisfy the rule (compliant)
2. Other sources mention penalties (SOURCE 7 has a penalty for section 33)
3. General legal knowledge: compliance = no violation = no penalty
4. The instruction "Do not claim that no consequence arises unless the supplied ICAI material explicitly supports that claim" is not being followed

---

## Recommended Fixes

### Issue 1 Fix: Improve Step 5 Debug Logging

**FILE:** `app/services/knowledge_search_service.py`
**LINES:** 819-874

**Problem:** Debug prints go to stdout instead of `retrieval_debug.log`

**Fix:** Add `debug_log()` calls so Step 5 execution is visible in the log file:

```python
if asks_for_consequence:
    debug_log(">>> STEP 5 BRANCH ENTERED <<<")
    debug_log(">>> STEP 5: ABOUT TO CALL LEGAL CONSEQUENCE RETRIEVAL <<<")
    try:
        consequence_documents = retrieve_legal_consequences(...)
        debug_log(f"LEGAL CONSEQUENCE RESULT COUNT: {len(consequence_documents)}")
        for document in consequence_documents:
            debug_log(f"CONSEQUENCE RESULT: ID={document.id}, Subject={document.subject}, Chapter={document.chapter}, Page={document.page_number}")
        # ... rest of the code
```

### Issue 2 Fix: Prevent Unsupported Consequence Claims

**FILE:** `app/services/llm_service.py`
**LINES:** 221-224 (system message)

**Current instruction:**
```
A conclusion that a requirement was satisfied does not establish
that no other penalty, liability, or adverse consequence exists.
Do not claim that no consequence arises unless the supplied ICAI
material explicitly supports that claim.
```

**Problem:** This instruction is not strong enough. The model still makes unsupported claims.

**Recommended stronger instruction:**
```
A conclusion that a requirement was satisfied does NOT establish
that no penalty, liability, or adverse consequence exists.

CRITICAL: If the supplied ICAI material does NOT explicitly state the
consequence of non-compliance for the specific provision being applied,
DO NOT claim that no consequence arises.

Instead, when a consequence is requested but not specified:
- Answer the compliance question (the facts do/do not satisfy the rule)
- Separately state: "The available ICAI study material does not specify
  the legal consequence of non-compliance with this provision."

Never infer that compliance means no consequence exists.
Never use consequence information from unrelated provisions.
```

### Issue 3 Fix: Improve Consequence Retrieval Specificity

**FILE:** `app/services/legal_retrieval_service.py`
**FUNCTION:** `retrieve_legal_consequences()` (lines 896-1059)

**Problem:** The function retrieves ANY prospectus document with penalty terms, regardless of whether those penalties apply to the specific question.

**Recommended fix:** Add section-specific consequence mapping. For example:

```python
# Add to LEGAL_CONCEPTS or a new structure
SECTION_CONSEQUENCE_MAP = {
    "32": {
        "consequence_keywords": ["at least three days", "prior to opening"],
        # Note: ICAI material does NOT specify consequences for section 32
        "has_explicit_consequence": False
    },
    "33": {
        "consequence_keywords": ["penalty of fifty thousand rupees"],
        "has_explicit_consequence": True
    },
    # ... other sections
}
```

Then in `retrieve_legal_consequences()`:
1. Check if the query specifies a section
2. If yes, check if that section has explicit consequences in the knowledge base
3. If no explicit consequences exist, return empty list
4. This prevents retrieving unrelated consequence documents

### Issue 4 Fix: Context Prioritization to Highlight the Applicable Rule

**FILE:** `app/services/knowledge_search_service.py`
**LINES:** 1181-1222

**Current behavior:** Scenario context prioritization exists but only marks the first result as "PRIMARY LEGAL RULE".

**Problem:** The correct rule (ID 10596) is at rank 3 after reranking, not rank 1. The prioritization doesn't help if the rule isn't first.

**Recommended fix:** Improve the reranking or add a specific check to ensure the document containing the exact section mentioned in the query is prioritized. For the Zenith scenario, the query mentions "Section 32", so documents mentioning "Section 32" should be boosted.

---

## Test Recommendations

### Test 1: Verify Step 5 Debug Output
- Run the Zenith scenario
- Check that `retrieval_debug.log` contains Step 5 debug messages
- Verify consequence documents are logged

### Test 2: Verify Consequence Retrieval Specificity
- Create a scenario question about section 33 (abridged prospectus)
- Verify that section 33-specific consequences are retrieved
- Verify that section 32 scenarios do NOT retrieve section 33 consequences

### Test 3: Verify LLM Does Not Make Unsupported Claims
- Run the Zenith scenario
- Verify the LLM does NOT claim "no consequence arises"
- Verify the LLM states "The available ICAI study material does not specify the legal consequence"

### Test 4: Verify Correct Rule Prioritization
- Create a scenario mentioning a specific section
- Verify that document containing that section is in the top 2 results
- Verify the document reaches the LLM context

---

## Summary

### Issue 1 — Step 5 Debug Output
- **Status:** Step 5 IS executing
- **Problem:** Debug prints go to stdout, not to `retrieval_debug.log`
- **Fix:** Add `debug_log()` calls in Step 5 branch
- **Secondary issue:** Retrieved consequence documents are not specific to the RHP filing timing question

### Issue 2 — Unsupported Legal Conclusions
- **Status:** LLM makes unsupported "no consequence" claim
- **Problem:** LLM prompt instruction is not strong enough; unrelated consequence documents may confuse the model
- **Fix:** Strengthen the system message instruction; prevent retrieval of unrelated consequence documents; add section-specific consequence mapping

### Verification Status
- ✅ Step 5 condition check: True
- ✅ Step 5 branch execution: Yes
- ✅ `retrieve_legal_consequences()` call: Yes
- ✅ Documents retrieved: 10
- ❌ Document relevance: Low (wrong sections/provisions)
- ✅ Documents reach candidate pool: Yes
- ❌ Documents reach final LLM context: Needs verification (context filtering may remove them)
- ✅ Correct rule reaches LLM: Yes (SOURCE 3)
- ❌ LLM follows consequence instruction: No (makes unsupported claim)
