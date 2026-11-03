# nominal_nucleus_02 — technical report

## Run identity

| Field | Value |
|---|---|
| Base | `24a1801` (round 01) |
| Batch 1 (reconciliation) | `86c1898`, `0c2b8fe` |
| Batch 2 (additions) | `7677d43` |
| HFN | `release_v18`, sha `8f5dd3684b0f1f80`; v19 not used |
| Data / input sha | `95bd27743f566b6f` / `d2700864f1a1abe9` |
| Python / hash seed | 3.13.17 / `PYTHONHASHSEED=0` |
| Batch 1 measurement | run `8dbd4717f655`, commit `0c2b8fe`, clean tree |
| Batch 2 measurement | run `46f6e5323306`, commit `7677d43`, clean tree |

The same identity is recorded in:
- `batch1_reconciliation/measurement.json`
- `batch2_additions/measurement.json`
- `measurement.json` (final)

## Containment

**Old-layer snapshot**
- Command: `tools/snapshot_outputs.py`, `24a1801` vs `7677d43`.
- Result: 6236 verses, **0 violations** (`snapshot_vs_24a1801.json`).

**Test suites**
- `tests/regress.py`: no difference.
- All 23 other suites: ALL OK.
- `tests/test_relations.py`: PASS 31, DIFFERS 5, FAIL 0.

**Structural checker**
- `check_records` reports 0 errors in both batch measurements.

**Changed files**
- `sarf/relations.py`;
- `tests/test_relations.py`;
- `tools/compare_relations.py`;
- `tools/pipeline_trace.py` (sections 14أ / 14ب).

`sarf/relations.py` is a relations-layer module, the only consumer of the features. No shared module changed.

## Comparison method (`tools/compare_relations.py`)

- **`dump`:** per verse, all relation records:
  - id, type, rule, status;
  - heads, positions, texts;
  - reason, premises, alternatives;
  - search status, nucleus flag;
  - `head_class`, the word-class evidence of each head.
- **`cmp`:** joins records on `relation_id`. Each row is one of: added, removed, or changed (field list).

**Cause attribution**
- Every row gets a `cause`, assigned only from declared markers: rule id, or the T19, E01 and coordination text in reason, premises or alternatives.
- Host-set differences (T19_HOST / HOST_ADDED) are decided by the host key `(text, kind)`.
- `ID` pairs a removed record with its re-keyed added twin: same verse, same type, a shared head position.
- `T19_CASCADE` marks a record that shares positions with a T19 change in the same verse.
- `OTHER` = 0 in all three comparisons.

| Comparison | Changes | By cause |
|---|---:|---|
| 24a1801 → batch 1 | 718 | T19_HOST 216, COORD 210, T19 164, UNHIDE 86, ID 37, T19_CASCADE 5 |
| batch 1 → batch 2 | 110 | A02 72 (36 new LICENSED + 36 removed A01), E01 27, HOST_ADDED 11 |
| 24a1801 → 7677d43 | 828 | the union of the two rows above |

Every row carries positions and texts. See:
- `relations_compare.json` / `.md`;
- `batch*/relations_compare.*`.

## Batch 1 — reconciliation

**R1. T19 (tanwin shape only)**
- Definition: `_Tok.shape_only` = pos `اسم` whose only evidence is `التنوين`.
- Such a token is not `nounish()`. The feature value in `sarf.features` is untouched.
- Records that used to drop silently now persist as DEFERRED, with the candidate role:
  - N01 / N02 subject or predicate;
  - V01 `khabar_candidate`;
  - P02 `complement_candidate`;
  - the R01 relative container.
- A wrong-case shape-only V01 candidate keeps its case-mismatch reason.

**R2. Category axes**
- `axes()` gives four independent axes per token: `word_class`, `build`, `protection`, `operator`.
- Each axis carries an `(value, evidence)` pair, or is undecided.
- Exported in `verse_relations(...)['axes']` and shown in trace section 14ب.

**R3. Coordination rival**
- Rival: the nearest written-nominative non-verb, at most 8 words before the conjunction, outside any PP.
- Effect: N02 is DEFERRED; N01 gets a named, positioned alternative.
- No rival when any of these holds:
  - S is a separate pronoun;
  - a verb intervenes outside a relative clause;
  - the rival is a licensed subject (`licensed_subjects`).

**R4. Unhide (commit `0c2b8fe`)**
- Change: `used_as_pred` now blocks A01 only for a LICENSED predicative PP.
- Effect: 86 A01 DEFERRED records appear, and nothing else changes.
- Regression test: T35 fails before the fix and passes after it.

**Tested and rejected**
- Rule: "verb after the predicate in frame ⇒ defer N01".
- 11 correct LICENSED→DEFERRED, e.g. 27:55 «أَنتُمۡ قَوۡمٌ تَجۡهَلُونَ».
- It also did not catch 2:285, so it was not committed.

## Batch 2 — additions (proposed rules)

### A02 v1

A02 is licensed when all of these hold:
- **Nucleus:** the oblique (PP or ADVP) lies inside a licensed N01 nucleus, strictly between S and P (`pre_p`). It is outside any container.
- **No verb:** no token in the frame has pos `فعل`, or `فعل` among its pos alternatives. Two kinds do not count as verbs:
  - nounish tokens, including E01;
  - members of a licensed oblique.
- **No other host:** no other A01 host lies inside the nucleus frame.
- **P is the host and a وصف:** P appears in the A01 hosts, and is a وصف by one of:
  - `derivation` ∈ {اسم فاعل, اسم مفعول} with status `مثبت`;
  - `derivation_candidates`;
  - E01.

**The record**
- Premises: N01 id, oblique id, frame span, host statement, and the E01 premise if any.
- `checked`: the frame-verb, other-host and container conditions, plus the نعت barrier.
- Alternatives:
  - multiple-khabar and fronted-hal readings, both declared out of v1 coverage;
  - out-of-frame hosts, as DEFERRED.
- `search_status = SEARCH_COMPLETE`; the edge is `ATTACH`.

**Narrowing during this round**

| Step | Licensed |
|---|---:|
| First variant | 75 |
| Require `pre_p` | 38 |
| Require P to be a وصف | 36 |

The `pre_p` step removed:
- all post-P cases, where the نعت host is a live competitor;
- 7:26, which crossed a sentence.

The وصف step removed 5:33 «خِزۡيٌ» (pattern فِعۡل only) and 85:6 «قُعُودٌ» (masdar).

The final hosts are all فَعِيل: عليم، قدير، شهيد، وكيل، عظيم، يسير، زعيم.

### E01 v1

A token is an elative noun when all of these hold:
- **Shape:** 4 letters: أ+fatha, sukun, fatha (no dagger alif), and a final damma or kasra without tanwin.
- **Root:** the root is in HFN v18.
- **Past forms:** the HFN form-I past forms have an ain vowel of fatha or damma, and there is no guttural in R2 or R3. Alternatively, the root is ajwaf.
- **No al.** `definite()` then returns False.

Outcome:
- 14 PREDICATION DEFERRED→LICENSED;
- 13 new DEFERRED or REJECTED candidates, with an elative subject;
- 11 A01 records gain a نعت host.

## Known remaining errors

| Position | Issue | Status |
|---|---|---|
| 2:285 | «وَٱلۡمُؤۡمِنُونَۚ كُلٌّ» licensed N01. «كُلٌّ» has the compensation tanwin. | Pre-existing; fix proposed, not implemented |
| 24:26 | «وَٱلطَّيِّبَٰتُ لِلطَّيِّبِينَ» deferred by a cascaded rival | New in this round, from R3 |

T19 also costs 61 correct relations, which now stay deferred. This is a coverage gap, not a regression to wrong; see `report_ar.md` §3.

## Reproduce

```
export SARF_HFN=<path>/release_v18 PYTHONHASHSEED=0
python3 tools/eval_relations.py --jobs 4 --out reports/nominal_nucleus_02
python3 tests/test_relations.py
python3 tools/compare_relations.py dump . rel_new.jsonl.gz --jobs 4
python3 tools/compare_relations.py cmp rel_24a1801.jsonl.gz rel_new.jsonl.gz --json c.json --md c.md
python3 -P -s tools/snapshot_outputs.py dump . new.pkl.gz --jobs 4
python3 -P -s tools/snapshot_outputs.py cmp base.pkl.gz new.pkl.gz
```

The baseline dump comes from a checkout of `24a1801`.

Relation dumps and pickles live outside the repository, because they contain verse text.
