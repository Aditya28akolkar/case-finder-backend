# LEGAL CONSEQUENCE RETRIEVAL INVESTIGATION REPORT

## Executive Summary

**Primary Root Cause:** The `enforce_legal_consequence_guard()` function in `app/services/llm_service.py` (lines 367-493) is too restrictive. It requires that a consequence appears in the **same sentence** as the specific section number mentioned in the user's question. This design choice:

1. **Rejects valid consequences** that appear in a different sentence or a different section of the retrieved document
2. **Rejects general penalty provisions** that apply across multiple sections
3. **Adds a fallback message** even when the consequence is present but doesn't meet the strict sentence-level co-location requirement

**Secondary Root Cause:** The consequence retrieval system (Step 5 in `knowledge_search_service.py`) is designed to return only documents that contain both the section number AND consequence terms in the same chunk. This fails to retrieve:
- Consequences that are cross-referenced in other sections
- General penalty provisions that apply broadly
- Consequences that are separated by paragraph breaks from the main rule

**Earliest Failure Point:** The consequence is lost at the **retrieval stage** (Step 5) when consequence documents are filtered out for not meeting the strict co-location requirements. If a consequence document does manage to reach the LLM context, it is then rejected by the **post-processing guard** for the same reason.

---

## Actual Request Flow

**File:** `app/services/rag_service.py`
**Function:** `ask_question()` (lines 47-410)

**Sequence:**

1. **User Question** → `ask_question()`
2. **Conversation History** → `get_conversation_history()` (lines 97-101)
3. **Save User Message** → `save_message()` (lines 117-122)
4. **Query Understanding** → `QueryUnderstandingService.analyze_query()` (lines 128-131)
   - **File:** `app/services/query_understanding_service.py`
   - **Function:** `analyze_query()` (lines 55-793)
   - Extracts: section, topic, keywords, legal_retrieval_query, is_scenario, legal_issue
5. **Knowledge Search** → `search_knowledge()` (lines 273-279)
   - **File:** `app/services/knowledge_search_service.py`
   - **Function:** `search_knowledge()` (lines 321-1315)
   - **Sub-steps:**
     a. Semantic search (lines 382-411)
     b. Keyword search (lines 415-718)
     c. Legal concept retrieval (lines 738-778)
     d. **Step 5: Legal consequence retrieval** (lines 781-892)
     e. Reranking (lines 936-952)
     f. Legal term boost (lines 954-977)
     g. Context filtering (lines 1156-1179)
6. **Context Construction** → Lines 317-357 in `rag_service.py`
7. **LLM Generation** → `generate_answer()` (lines 384-388)
   - **File:** `app/services/llm_service.py`
   - **Function:** `generate_answer()` (lines 31-366)
8. **Post-Processing Guard** → `enforce_legal_consequence_guard()` (lines 316-320)
   - **File:** `app/services/llm_service.py`
   - **Function:** `enforce_legal_consequence_guard()` (lines 367-493)
9. **Save Assistant Answer** → `save_message()` (lines 396-401)
10. **Return Answer** → Lines 407-410

---

## Evidence by Pipeline Stage

### 1. Query Understanding

**File:** `app/services/query_understanding_service.py`
**Function:** `analyze_query()` (lines 55-793)

**Status:** Working correctly

**Evidence from `query_debug.txt`:**
- Original question preserved: "Did Aarav Ltd. comply with the filing timeline under Section 32(2) of the Companies Act, 2013? Explain the applicable deadline and legal consequence."
- Section extracted: "32(2)"
- Legal issue identified: "Whether Aarav Ltd. complied with the filing timeline under Section 32(2) of the Companies Act, 2013, including the applicable deadline and legal consequence."
- Legal retrieval query: "Section 32(2) Companies Act 2013 Red Herring Prospectus filing deadline before subscription list opening"
- Consequence intent: Detected (question contains "legal consequence")

**Observation:** Query understanding correctly identifies that the user is asking for a legal consequence and extracts the relevant section. The `legal_retrieval_query` is designed to search for the legal rule only, excluding scenario-specific facts like "Aarav Ltd.", "Monday 18th", "Saturday 16th".

**Expected Behavior:** This is correct. The separation of facts from legal terms is intentional for scenario questions.

---

### 2. Retrieval

**File:** `app/services/knowledge_search_service.py`
**Function:** `search_knowledge()` (lines 321-1315)

**Status:** Partially working - retrieves the rule but fails to retrieve consequences

**Evidence from `retrieval_debug.log`:**

**For the Aarav Ltd. scenario:**
- **Keyword search:** Found target ID 10596 at position 1 (correct)
- **Legal concept search:** Found target ID 10596 at position 5 (correct)
- **Step 5 consequence retrieval:** Triggered, returned 0 documents
- **After merge:** Target ID 10596 at position 1
- **After rerank:** Target ID 10596 at position 3
- **Before context filter:** Target ID 10596 at position 3
- **Final results:** Target ID 10596 at position 3

**Analysis:**
- The primary legal rule (ID 10596, page 22) is correctly retrieved
- The rule states: "A company proposing to issue a red herring prospectus shall file it with the Registrar at least three days prior to the opening of the subscription list and the offer."
- **Step 5 consequence retrieval returned 0 documents** (logged: "STEP 5 RESULT COUNT: 0")

**Why Step 5 Failed:**

**File:** `app/services/legal_retrieval_service.py`
**Function:** `retrieve_legal_consequences()` (lines 897-1041)

**Evidence from retrieval_debug.log:**
```
[2026-10-05 11:12:13] >>> STEP 5: Calling retrieve_legal_consequences
[2026-10-05 11:12:14] === CONSEQUENCE RETRIEVAL START ===
[2026-10-05 11:12:14] Detected sections: ['32']
[2026-10-05 11:12:14] Detected concepts: ['red herring prospectus', 'prospectus']
[2026-10-05 11:12:14] Specific phrases: ['red herring prospectus', 'opening of the subscription list', 'prospectus', 'issue of securities']
[2026-10-05 11:12:14] Applied subject filter: Corporate and Other Laws
[2026-10-05 11:12:14] Candidate pool size: 2
[2026-10-05 11:12:14] REJECTED: ID 10582, Section=True, Concept=True, Consequence=False, Chapter=True
[2026-10-05 11:12:14] REJECTED: ID 10595, Section=True, Concept=True, Consequence=False, Chapter=True
[2026-10-05 11:12:14] Final consequence results: 0
```

**Root Cause in Step 5:**
The function requires ALL three conditions to be true in the same document:
1. Contains the section number ("Section 32")
2. Contains the legal concept ("red herring prospectus")
3. Contains consequence terms ("penalty", "liable", etc.)

**The Problem:** The ICAI study material for Section 32 (RHP filing timing) does NOT contain any consequence terms in the same chunk as the rule. The consequence may be:
- In a different section of the same chapter
- In a general penalty provision elsewhere
- Not explicitly stated at all in the ICAI material

**Evidence from `llm_context_debug.txt`:**
- SOURCE 3 (page 22) contains the Section 32(2) rule with the three-day deadline
- SOURCE 7 (page 23) contains a penalty for Section 33 (abridged prospectus): "A company who makes any default in complying with the provisions of section 33, shall be liable to a penalty of fifty thousand rupees for each default."

**Critical Finding:** SOURCE 7 contains a consequence (penalty) but for a DIFFERENT section (33, not 32). Step 5 correctly rejected this because it doesn't contain "Section 32" AND consequence terms in the same chunk.

**Expected Behavior:** Step 5 should retrieve consequences even if they are:
- In a different section of the same chapter
- In a general penalty provision that applies to prospectus violations broadly
- Cross-referenced in other sections of the Act

**Current Behavior:** Step 5 only retrieves consequences that appear in the same chunk as the section number, which is an unrealistic requirement for ICAI study material.

---

### 3. Reranking and Context Filtering

**File:** `app/services/knowledge_search_service.py`
**Functions:** `rerank()` (lines 936-952), `filter_retrieved_chunks()` (lines 1156-1179)

**Status:** Not the root cause

**Evidence:**
- Target document ID 10596 survived reranking (position 3)
- Target document ID 10596 survived context filtering (position 3)
- The rule reached the final LLM context

**Analysis:** Reranking and context filtering are working correctly. They are not removing consequence documents because Step 5 is not retrieving any consequence documents to begin with.

**File:** `app/services/legal_context_filter.py`
**Function:** `filter_retrieved_chunks()` (lines ~1-893)

**Observation:** The context filter is designed to remove unrelated legal topics (e.g., AGM content mixed with prospectus content). However, since no consequence documents were retrieved by Step 5, the filter cannot remove what doesn't exist.

---

### 4. Context Construction

**File:** `app/services/rag_service.py`
**Lines:** 317-357

**Status:** Working correctly

**Evidence from `llm_context_debug.txt`:**
- 10 sources were passed to the LLM
- SOURCE 3 (page 22) contains the correct Section 32(2) rule
- SOURCE 7 (page 23) contains a Section 33 penalty
- All other sources are from Chapter 3 (Prospectus and Allotment of Securities)

**Analysis:** The context construction preserves the documents returned by retrieval. It does not:
- Truncate content
- Overwrite documents
- Displace relevant material
- Separate related provisions

**Critical Finding:** SOURCE 7 contains a penalty for Section 33, which is unrelated to the Section 32 question. This is a context pollution issue, but it's not the primary cause of the consequence failure. The primary cause is that there is NO Section 32 consequence in the ICAI material at all.

---

### 5. LLM Prompt and Generation

**File:** `app/services/llm_service.py`
**Function:** `generate_answer()` (lines 31-366)

**Status:** Prompt is appropriate but the post-processing guard interferes

**Evidence from the prompt (lines 68-200):**
The prompt contains extensive instructions about:
- Using ICAI material as the source of legal rules and consequences
- Not inventing consequences
- Separating missing case facts from missing legal information
- Addressing legal consequences only when explicitly supported

**Specific instructions (lines 276-287):**
```
When the user asks for a legal consequence or penalty:
1. Retrieve the relevant provision and check for cross-referenced
   penalty provisions elsewhere in the supplied legal documents.
2. Do not assume that the absence of a penalty in the main section
   means that no penalty applies.
3. State a penalty only when the retrieved legal text supports it.
4. Distinguish an explicitly stated penalty from a consequence
   established through a related general provision.
5. If the relevant legal provisions cannot be found, explain
   that the available material is insufficient to establish
   the legal consequence.
```

**Analysis:** The prompt explicitly instructs the LLM to:
- Check for cross-referenced penalty provisions elsewhere
- Not assume that absence in the main section means no penalty applies
- Distinguish explicitly stated penalties from general provisions

However, the LLM's answer is then modified by the post-processing guard, which may override or contradict these instructions.

---

### 6. Post-Processing and Legal Consequence Guard

**File:** `app/services/llm_service.py`
**Function:** `enforce_legal_consequence_guard()` (lines 367-493)

**Status:** **THIS IS THE PRIMARY ROOT CAUSE**

**Evidence from the code (lines 410-436):**

```python
# Only treat a consequence as supported when the same
# sentence identifies the relevant section.
supported = False

for sentence in re.split(r"(?<=[.!?])\s+", context):
    for section in sections:
        section_pattern = (
            rf"\bsections?\s+{re.escape(section)}\b"
        )

        if (
            re.search(
                section_pattern,
                sentence,
                re.IGNORECASE,
            )
            and consequence_terms.search(sentence)
        ):
            supported = True
            break

    if supported:
        break

# Do not alter the answer if the source supports a consequence.
if supported:
    return answer
```

**The Problem:**
The guard requires that the **same sentence** contains BOTH:
1. The section number mentioned in the question (e.g., "Section 32")
2. A consequence term (e.g., "penalty", "liable")

**Why This Fails:**
1. **Sentence-level co-location is unrealistic:** Legal texts often state the rule in one sentence and the consequence in a different sentence, sometimes even in a different paragraph.
2. **Cross-referenced penalties are rejected:** If a general penalty provision in Section 50 applies to violations of Section 32, the guard will reject it because the sentence doesn't contain "Section 32".
3. **Section number parsing issues:** The question asks about "Section 32(2)" but the text might only say "Section 32" without the subsection. The regex pattern `\bsections?\s+(\d+[A-Za-z]?)\b` extracts "32" from "32(2)", but the guard then searches for "section 32" literally. If the text says "section 32(2)" instead of "section 32", the match may fail.

**Evidence from the code (lines 438-464):**
If no supported consequence is found, the guard:
1. Removes sentences containing unsupported claims like "no penalty" or "no consequences arise"
2. Checks if the answer already has a fallback message
3. If not, appends: "The available ICAI study material does not specify the legal consequence for this provision."

**Analysis:** This guard is overly restrictive and:
- Rejects valid consequences that are in a different sentence
- Rejects cross-referenced general penalty provisions
- Forces a fallback message even when the LLM correctly identified a consequence from general provisions
- Contradicts the LLM prompt instructions to check for cross-referenced provisions

---

### 7. Inconsistent Results

**Evidence from retrieval_debug.log:**

Two different questions show different behavior:

**Question 1 (Information memorandum refund):**
- Question: "Has the company complied with the refund timeline specified in the supplied ICAI study material? Explain your answer."
- Step 5: Skipped (no consequence intent detected)
- The question does not contain consequence keywords like "penalty", "consequence", "liable"
- Result: No consequence retrieval triggered

**Question 2 (Aarav Ltd. RHP Section 32):**
- Question: "Did Aarav Ltd. comply with the filing timeline under Section 32(2) of the Companies Act, 2013? Explain the applicable deadline and legal consequence."
- Step 5: Triggered (consequence intent detected)
- Step 5: Returned 0 documents
- Result: Consequence fallback added by guard

**Root Cause of Inconsistency:**
The inconsistency stems from:
1. **Query wording:** Whether the question explicitly uses consequence keywords ("penalty", "consequence", "liable") determines if Step 5 is triggered
2. **Section-specific retrieval:** If the question specifies a section, Step 5 only retrieves consequences from documents containing that exact section number
3. **Sentence-level guard:** Even if a consequence document reaches the LLM, the guard rejects it unless the consequence appears in the same sentence as the section number

**Example of why a consequence might be retrieved sometimes:**
- If a question asks "What is the penalty for non-compliance with Section 33?" and there's a document with "Section 33" and "penalty" in the same sentence, Step 5 will retrieve it and the guard will accept it
- If a question asks "What is the penalty for non-compliance with Section 32?" and the penalty is in a general provision that doesn't mention "Section 32", Step 5 won't retrieve it or the guard will reject it

---

## Exact Failure Point

**Earliest Failure Point:** Step 5 consequence retrieval in `app/services/knowledge_search_service.py` (lines 781-892)

**Why:**
The `retrieve_legal_consequences()` function in `legal_retrieval_service.py` (lines 897-1041) requires all three conditions in the same document chunk:
1. Section number match
2. Legal concept match
3. Consequence term match

**If the consequence exists but is in a different chunk or a cross-referenced general provision, it will not be retrieved.**

**Secondary Failure Point:** Post-processing guard in `app/services/llm_service.py` (lines 367-493)

**Why:**
Even if a consequence document somehow reaches the LLM context, the guard rejects it unless the consequence appears in the **same sentence** as the section number.

---

## Primary Root Cause vs Contributing Factors

### Primary Root Cause (Confidence: High)

**File:** `app/services/llm_service.py`
**Function:** `enforce_legal_consequence_guard()` (lines 367-493)
**Lines:** 410-436

**The Problem:** The guard requires sentence-level co-location of the section number and consequence terms. This is an unrealistic requirement for legal texts where:
- Rules and consequences are often in different sentences
- General penalty provisions apply across multiple sections
- Cross-references separate the rule from its consequence

**Impact:** Even if a consequence is present in the retrieved context, the guard will reject it if it's not in the same sentence as the section number, forcing a fallback message.

### Contributing Factor 1 (Confidence: High)

**File:** `app/services/legal_retrieval_service.py`
**Function:** `retrieve_legal_consequences()` (lines 897-1041)
**Lines:** 1002-1003

**The Problem:** The function requires section + concept + consequence terms to be in the same chunk (lines 1002-1003). This fails to retrieve:
- Consequences in different paragraphs of the same document
- Cross-referenced general penalty provisions
- Consequences that are section-independent

**Impact:** Consequence documents are not retrieved at all in many cases, so they never reach the LLM or the guard.

### Contributing Factor 2 (Confidence: Medium)

**File:** `app/services/legal_retrieval_service.py`
**Function:** `retrieve_legal_consequences()` (lines 897-1041)
**Lines:** 1034-1041 (chapter validation)

**The Problem:** The chapter validation added in Step 5 fix filters out documents from unrelated chapters, which is correct. However, it may also filter out valid cross-chapter consequences if they exist.

**Impact:** Minor - this is actually a correct safeguard against retrieving consequences from unrelated acts (e.g., LLP Act for Companies Act questions).

### Contributing Factor 3 (Confidence: Low)

**File:** `app/services/llm_service.py`
**Function:** `generate_answer()` (lines 68-287)

**The Problem:** The prompt instructions (lines 276-287) tell the LLM to check for cross-referenced provisions, but the guard contradicts this by requiring sentence-level co-location.

**Impact:** The LLM may correctly identify a consequence from general provisions, but the guard then removes or overrides this.

---

## Concrete Example Trace

**Question:** "Did Aarav Ltd. comply with the filing timeline under Section 32(2) of the Companies Act, 2013? Explain the applicable deadline and legal consequence."

### Stage 1: Query Understanding
**File:** `app/services/query_understanding_service.py`
**Function:** `analyze_query()`

**Output:**
- Section: "32(2)"
- Legal issue: "Whether Aarav Ltd. complied with the filing timeline under Section 32(2) of the Companies Act, 2013, including the applicable deadline and legal consequence."
- Legal retrieval query: "Section 32(2) Companies Act 2013 Red Herring Prospectus filing deadline before subscription list opening"
- Consequence intent: Detected (question contains "legal consequence")

**Status:** Working correctly

### Stage 2: Retrieval
**File:** `app/services/knowledge_search_service.py`
**Function:** `search_knowledge()`

**Semantic search:** Retrieved 30 documents
**Keyword search:** Retrieved 50 documents (including target ID 10596 at position 1)
**Legal concept search:** Retrieved 30 documents (including target ID 10596 at position 5)
**Merge:** Combined pool of 53 documents (target ID 10596 at position 1)

**Step 5 Consequence Retrieval:**
- Triggered: Yes (consequence intent detected)
- Called: `retrieve_legal_consequences()`
- Parameters:
  - question: Full scenario with facts
  - topic: "Red Herring Prospectus subscription list"
  - expanded_query: "Section 32(2) Companies Act 2013 Red Herring Prospectus filing deadline before subscription list opening"
  - subject: "Corporate and Other Laws"
- Detected sections: ['32']
- Detected concepts: ['red herring prospectus', 'prospectus']
- Specific phrases: ['red herring prospectus', 'opening of the subscription list', 'prospectus', 'issue of securities']
- Candidate pool: 2 documents (IDs 10582, 10595)
- Both documents rejected because: Consequence=False (no penalty terms in the same chunk)
- **Result: 0 documents returned**

**Status:** **FAILURE** - No consequence documents retrieved

### Stage 3: Reranking
**File:** `app/services/knowledge_search_service.py`
**Function:** `rerank()` (via import)

**Before rerank:** Target ID 10596 at position 1
**After rerank:** Target ID 10596 at position 3
**Status:** Working correctly - rule preserved

### Stage 4: Context Filtering
**File:** `app/services/legal_context_filter.py`
**Function:** `filter_retrieved_chunks()`

**Before filter:** Target ID 10596 at position 3
**After filter:** Target ID 10596 at position 3
**Status:** Working correctly - rule preserved

### Stage 5: Context Construction
**File:** `app/services/rag_service.py`
**Lines:** 317-357

**Context passed to LLM:** 10 sources from Chapter 3
- SOURCE 3 (page 22): Contains Section 32(2) rule with three-day deadline
- SOURCE 7 (page 23): Contains Section 33 penalty for abridged prospectus
- Other sources: General prospectus information

**Status:** Working correctly - context includes the rule

### Stage 6: LLM Generation
**File:** `app/services/llm_service.py`
**Function:** `generate_answer()`

**Prompt:** Instructs LLM to check for cross-referenced penalty provisions and distinguish general provisions

**LLM receives:** Context with Section 32 rule and Section 33 penalty

**LLM likely behavior:** The LLM could potentially:
- Apply the Section 32 rule to the facts (Saturday 16th to Monday 18th = 2 days, violates "at least three days" requirement)
- Note that Section 33 has a penalty but is for abridged prospectus, not RHP filing
- Conclude that no Section 32 consequence is specified

**Status:** LLM generation not visible in logs, but prompt is appropriate

### Stage 7: Post-Processing Guard
**File:** `app/services/llm_service.py`
**Function:** `enforce_legal_consequence_guard()` (lines 367-493)

**Execution:**
1. Checks if question asks about consequence: YES (contains "legal consequence")
2. Extracts section numbers: ['32'] (extracted from "32(2)")
3. Searches context for sentences containing BOTH "section 32" AND consequence terms
4. SOURCE 3 contains "section 32" but no consequence terms
5. SOURCE 7 contains consequence terms but "section 33", not "section 32"
6. **Result:** `supported = False`
7. Since not supported, removes unsupported claims and adds fallback
8. **Final fallback:** "The available ICAI study material does not specify the legal consequence for this provision."

**Status:** **FAILURE** - Guard rejects consequence even if LLM identified one

---

## Recommended Fixes (Suggestions Only)

### Fix 1: Relax the Sentence-Level Co-Location Requirement

**File:** `app/services/llm_service.py`
**Function:** `enforce_legal_consequence_guard()` (lines 367-493)
**Lines:** 410-436

**Current Behavior:** Requires section number and consequence terms to be in the same sentence

**Proposed Change:** Check at the document or paragraph level instead of sentence level

**Why:** Legal texts often state rules and consequences in different sentences. For example:
- Sentence 1: "Section 32 requires RHP to be filed at least three days before opening."
- Sentence 2: "A company who fails to comply shall be liable to a penalty."

The current guard would reject this because they're in different sentences.

**Implementation:**
```python
# Instead of sentence-level check, check at paragraph level
paragraphs = re.split(r"\n\n+", context)
for paragraph in paragraphs:
    if any(section in paragraph for section in sections) and consequence_terms.search(paragraph):
        supported = True
        break
```

### Fix 2: Allow Cross-Referenced General Penalty Provisions

**File:** `app/services/llm_service.py`
**Function:** `enforce_legal_consequence_guard()` (lines 367-493)
**Lines:** 410-436

**Current Behavior:** Only accepts consequences that mention the exact section number from the question

**Proposed Change:** Accept consequences from general penalty provisions that apply to the legal domain (e.g., prospectus violations)

**Why:** Many Acts have general penalty provisions that apply to violations across multiple sections. For example, a general provision might state "Any violation of prospectus provisions shall be liable to a penalty of Rs. 50,000." This should be accepted for Section 32 questions.

**Implementation:**
```python
# Check for general penalty provisions that apply to the legal domain
legal_domain_keywords = []
if "prospectus" in question.lower():
    legal_domain_keywords = ["prospectus", "securities", "public offer"]

# If no section-specific consequence found, check for general provision
if not supported and legal_domain_keywords:
    for paragraph in paragraphs:
        if any(kw in paragraph.lower() for kw in legal_domain_keywords) and consequence_terms.search(paragraph):
            supported = True
            break
```

### Fix 3: Improve Consequence Retrieval to Check Neighboring Chunks

**File:** `app/services/legal_retrieval_service.py`
**Function:** `retrieve_legal_consequences()` (lines 897-1041)
**Lines:** 1002-1003

**Current Behavior:** Requires section + concept + consequence terms to be in the same chunk

**Proposed Change:** If a document contains the section and concept but not the consequence, check neighboring chunks (±2 IDs) for consequence terms

**Why:** The consequence might be in the next paragraph or nearby page, not in the same chunk.

**Implementation:**
```python
# After finding documents with section + concept but no consequence
# Check neighboring chunks for consequence terms
if has_section and has_concept and not has_consequence:
    # Query database for neighboring chunks
    neighbor_ids = range(document.id - 2, document.id + 3)
    neighbor_docs = db.query(KnowledgeDocument).filter(
        KnowledgeDocument.id.in_(neighbor_ids)
    ).all()
    
    for neighbor in neighbor_docs:
        neighbor_content = neighbor.content or ""
        if any(term.lower() in neighbor_content.lower() for term in LEGAL_CONSEQUENCE_TERMS):
            # Add neighbor to results
            consequence_results.append(neighbor)
            break
```

### Fix 4: Add Fallback to Direct Consequence Questions

**File:** `app/services/knowledge_search_service.py`
**Function:** `search_knowledge()` (lines 781-892)

**Current Behavior:** Step 5 only searches for consequences when the question mentions the section

**Proposed Change:** If the question asks "What is the penalty for X?" without mentioning a section, perform a broader consequence search

**Why:** Users may ask "What is the penalty for late RHP filing?" without specifying "Section 32". The current implementation would miss general penalty provisions.

**Implementation:**
```python
# If question asks for consequence but no section detected
if asks_for_consequence and not sections:
    # Perform broader consequence search without section filter
    consequence_documents = retrieve_general_consequences(
        db=db,
        question=question,
        topic=topic,
        subject=subject,
        limit=10
    )
```

### Fix 5: Improve Section Number Parsing

**File:** `app/services/llm_service.py`
**Function:** `enforce_legal_consequence_guard()` (lines 392-396)

**Current Behavior:** Extracts "32" from "32(2)" and searches for "section 32"

**Proposed Change:** Search for both "section 32" and "section 32(2)" to handle subsection references

**Why:** The text might say "section 32(2)" while the guard only searches for "section 32", causing a mismatch.

**Implementation:**
```python
# Generate both patterns: with and without subsection
section_patterns = []
for section in sections:
    section_patterns.append(rf"\bsections?\s+{re.escape(section)}\b")
    # Also try with subsection pattern if original had it
    if "(" in question:
        section_patterns.append(rf"\bsections?\s+{re.escape(section)}\s*\(")
```

---

## Missing Evidence

1. **Actual LLM generation output:** The logs do not show what the LLM generated before the guard was applied. We can only see the final answer after post-processing.

2. **Database content for cross-referenced provisions:** We don't have direct database access to verify whether general penalty provisions exist in the ICAI material for prospectus violations.

3. **Direct consequence questions test:** We don't have logs for a direct question like "What is the penalty for non-compliance with Section 33?" to verify that the guard works correctly when the section and consequence are in the same sentence.

4. **Alternative scenario tests:** We only have logs for RHP Section 32 scenarios. We don't have logs for other legal domains (e.g., board meetings, annual returns) to verify if the issue generalizes.

5. **Exact LLM answer before guard:** Without seeing the LLM's raw output, we cannot definitively say whether the LLM would have correctly identified a consequence from general provisions before the guard modified the answer.

---

## Conclusion

**Why does the chatbot fail to provide legal consequences when the relevant legal information may exist in the knowledge base?**

The chatbot fails to provide legal consequences due to a **two-stage restrictive design**:

1. **Retrieval Stage (Step 5):** The consequence retrieval system requires that a single document chunk contain the section number, legal concept, AND consequence terms simultaneously. This fails to retrieve consequences that are:
   - In a different paragraph of the same document
   - In cross-referenced general penalty provisions
   - Section-independent but legally applicable

2. **Post-Processing Stage (Guard):** The `enforce_legal_consequence_guard()` function requires that the section number and consequence terms appear in the **same sentence**. This rejects valid consequences that are:
   - In a different sentence than the rule
   - In general penalty provisions that don't mention the specific section number
   - Separated by paragraph breaks from the main rule

**The fundamental architectural issue is that the system assumes legal consequences are always co-located with the rules in the same sentence/chunk, which is not true for most legal texts.** The ICAI study material structure, like most legal documents, often separates rules from their consequences across paragraphs, sections, or general provisions.

The prompt correctly instructs the LLM to check for cross-referenced provisions and general penalties, but the retrieval and guard implementations prevent the LLM from ever seeing or using such information.
