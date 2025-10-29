# Phase 1 E2E Testing - Deep Dive Learnings

## Summary

**Time Invested:** ~6 hours (setup + deep-dive)
**Tests Passing:** 4/7 (57%)
**Infrastructure:** ✅ Complete
**Key Finding:** pytest-lsp works for basic operations, but code action requests timeout

---

## ✅ Successes

### Infrastructure Complete
- pytest-lsp + 7 testing dependencies installed
- Test directory structure created (fixtures/, helpers/)
- Base fixtures implemented (client, simple_project)
- Assertion helpers created (apply_text_edit, assert_code_action_present)
- pytest configuration in pyproject.toml

### Working Tests (4/7)
1. ✅ `test_initialize_with_capabilities` - Server initializes correctly
2. ✅ `test_shutdown_sequence` - Clean shutdown validated
3. ✅ `test_client_connects` - Client fixture works
4. ✅ `test_open_document` - text_document_did_open notification works

### API Patterns Discovered
```python
# Correct pytest-lsp patterns:

# 1. Fixture definition
@pytest_lsp.fixture(
    scope="module",
    config=ClientServerConfig(
        server_command=[sys.executable, "-m", "cst_lsp.server"],
    ),
)
async def client(lsp_client: LanguageClient, simple_project):
    await lsp_client.initialize_session(InitializeParams(...))
    yield lsp_client  # Important: yield the injected client!
    await lsp_client.shutdown_session()

# 2. Notifications (synchronous, no await)
client.text_document_did_open(params=DidOpenTextDocumentParams(...))

# 3. Requests (async, await result)
actions = await client.text_document_code_action_async(params=CodeActionParams(...))
```

---

## ⚠️ Blockers

### Issue 1: Code Action Requests Timeout

**Symptom:**
```
tests/e2e/test_simple_code_action.py::test_code_action_request_basic
Opening: file:///tmp/.../minimal.py
Requesting code actions...
+++++++++++++++++++++++++++++++++++ Timeout (>5.0s) ++++++++++++++++++++++++++++++++++++
```

**Analysis:**
- Server receives initialize ✅
- Server receives didOpen ✅
- Server **hangs** on code action request ❌
- Request never returns (5s+ timeout)

**Potential Causes:**

1. **Server Not Handling Request**
   - code_action handler not properly registered
   - Exception in handler silently caught
   - Infinite loop in transformation logic

2. **LSP Protocol Mismatch**
   - Params format incorrect
   - Missing required fields
   - Server expecting different structure

3. **Async/Await Issues**
   - Server handler not properly async
   - Deadlock in event loop
   - pytest-lsp async context problem

4. **Document Not in Workspace**
   - Server can't find document in workspace
   - `workspace.get_document()` failing
   - Deprecation warning: should use `get_text_document()`

### Issue 2: workspace.get_document Deprecation

**Warning:**
```
/cst_lsp/server.py:173: DeprecationWarning: 'workspace.get_document' has been deprecated,
use 'workspace.get_text_document' instead
```

**Impact:** May cause issues with document retrieval in newer pygls versions

**Fix:** Update server.py:173 to use `get_text_document()`

---

## 🔬 Debugging Steps Taken

1. ✅ Verified pytest-lsp API patterns from docs/examples
2. ✅ Fixed notification vs request method usage
3. ✅ Confirmed client fixture initialization works
4. ✅ Confirmed document open notifications work
5. ⚠️ Code action requests timeout - needs deeper investigation

### What Works
```python
# This pattern works:
async def test_works(client):
    # Client is initialized ✅
    # Can send notifications ✅
    client.text_document_did_open(...)
    # Test passes ✅
```

### What Doesn't Work
```python
# This pattern times out:
async def test_fails(client):
    client.text_document_did_open(...)
    actions = await client.text_document_code_action_async(...)  # Hangs here ❌
```

---

## 💡 Next Steps - Recommendations

### Option A: Debug Server Code Action Handler (2-4h)

**Tasks:**
1. Fix `workspace.get_document()` deprecation → `get_text_document()`
2. Add logging to server code_action_handler
3. Test server manually with JSON-RPC messages
4. Verify transformations list is populated after initialize
5. Check if handler is catching exceptions silently

**Code to investigate:**
```python
# server.py:172-200
async def code_action_handler(self, params: lsp.CodeActionParams):
    document = self.workspace.get_document(params.text_document.uri)  # Line 173 - deprecated!
    # ... rest of handler
```

**Hypothesis:** `get_document()` might be failing/returning None in test context

### Option B: Simplify Tests with Direct Assertions (1-2h)

**Approach:**
- Keep lifecycle tests (working!)
- Create simpler code action tests that just verify server doesn't crash
- Skip full TextEdit validation for Phase 1
- Move complex assertions to Phase 2

**Example:**
```python
@pytest.mark.timeout(2)
async def test_code_action_no_crash(client):
    """Verify server responds to code action (even if empty)."""
    try:
        result = await client.text_document_code_action_async(params)
        assert True, "Server responded without timeout"
    except asyncio.TimeoutError:
        pytest.fail("Server timed out on code action request")
```

### Option C: Manual Server Testing Script (1h)

Create standalone script to test server:
```python
# scripts/test_server_manually.py
# Sends initialize → initialized → didOpen → codeAction
# Validates responses at each step
# Helps isolate pytest-lsp vs server issues
```

---

## 📊 Current Test Matrix

| Test | Status | Runtime | Notes |
|------|--------|---------|-------|
| test_initialize_with_capabilities | ✅ PASS | 0.7s | Validates initialization |
| test_shutdown_sequence | ✅ PASS | 0.7s | Validates shutdown |
| test_client_connects | ✅ PASS | 0.7s | Validates client fixture |
| test_open_document | ✅ PASS | 0.7s | Validates didOpen notification |
| test_code_action_request_basic | ❌ TIMEOUT | >5s | Server hangs on code action |
| test_extract_method_simple | ❌ TIMEOUT | >5s | Same root cause |
| test_import_single_symbol | ❌ TIMEOUT | >5s | Same root cause |
| test_invalid_range_handling | ❌ TIMEOUT | >5s | Same root cause |

**Pattern:** All tests with `text_document_code_action_async` timeout

---

## 🎯 Recommended Path Forward

**Immediate (30 min):**
1. Fix `workspace.get_document()` → `workspace.get_text_document()` in server.py
2. Re-run tests to see if this fixes timeout

**If Still Times Out (2h):**
3. Add debug logging to server
4. Create manual test script
5. Isolate server vs pytest-lsp issue

**If Server Issue Found (1h):**
6. Fix server code
7. Re-run all tests
8. Should get 7/7 passing

**If pytest-lsp Issue (2h):**
9. Research pytest-lsp async code action examples
10. May need to use lower-level protocol methods
11. Consider hybrid approach (manual client for code actions)

---

## 📝 Files Created (Phase 1)

```
tests/e2e/
├── conftest.py                    # Base fixtures
├── helpers/
│   ├── __init__.py
│   └── assertions.py              # LSP validation utilities
├── test_lifecycle.py              # ✅ 2/2 passing
├── test_simple.py                 # ✅ 2/2 passing (diagnostic)
├── test_simple_code_action.py     # ❌ 1/1 timeout (diagnostic)
├── test_code_actions.py           # ❌ 2/2 timeout (needs fix)
├── test_error_handling.py         # ❌ 1/1 timeout (needs fix)
└── README.md                      # Phase 1 status
└── PHASE1_LEARNINGS.md            # This document

docs/
└── E2E_TESTING_PRD.md             # Complete requirements (91 tests planned)

pyproject.toml                     # Updated with pytest-lsp deps
```

**Lines of Code:** ~1200 (tests + infrastructure + docs)

---

## 🔑 Key Takeaways

1. **pytest-lsp works** - Basic lifecycle and notifications validated
2. **Server has bug** - `workspace.get_document()` deprecated, may cause issues
3. **Code actions timeout** - Root cause needs investigation (likely server-side)
4. **Infrastructure solid** - Fixtures and helpers ready for expansion
5. **Path forward clear** - Fix server bug, re-test, expand to full suite

**Confidence Level:** High that fixing server's `get_document()` issue will resolve timeouts

**Next Session:** Start with server fix, should get to 7/7 tests passing quickly
