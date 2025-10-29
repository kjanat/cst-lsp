# E2E LSP Testing Infrastructure - Requirements Document

## Executive Summary

Comprehensive e2e testing infrastructure for CST-LSP server targeting full LSP protocol coverage with maintainable, reusable test framework. Prioritizes completeness over speed (1-2min suite acceptable), establishing foundation for long-term quality assurance.

**Total Scope:** 91 tests across 3 phases
**Total Effort:** 52-68 hours (6-8 working days)
**Framework:** pytest-lsp with comprehensive fixture system

---

## 1. Current State Analysis

### Existing Test Coverage
- ✅ **Unit tests**: Transformation logic, symbol finding (mocked), diff conversion
- ❌ **Missing**: LSP protocol flow, server lifecycle, real stdio communication, TextEdit validation

### Coverage Gap
| Component | Unit Coverage | E2E Coverage | Gap |
|-----------|--------------|--------------|-----|
| Transformations (libcst) | ✅ High | ❌ None | Protocol integration |
| Symbol finder | ✅ Medium (mocked) | ❌ None | Real ripgrep integration |
| Server lifecycle | ❌ None | ❌ None | Initialize/shutdown |
| LSP protocol | ❌ None | ❌ None | Request/response flow |
| TextEdit application | ⚠️ Partial | ❌ None | Editor simulation |

---

## 2. User Stories & Acceptance Criteria

### 2.1 Server Lifecycle

**US-1.1: Server Initialization**
```
As a client application
I want server initialization with capability negotiation
So that both sides understand supported features

Acceptance Criteria:
- Server responds to initialize with capabilities object
- codeActionProvider advertised with supported kinds
- textDocumentSync capabilities declared
- serverInfo contains name and version
- Server transitions from uninitialized → initialized state
```

**US-1.2: Graceful Shutdown**
```
As a client
I want clean shutdown sequence
So that no resources leak

Acceptance Criteria:
- shutdown request → null response
- Server stops accepting new requests
- exit notification → process terminates
- No exceptions or orphaned processes
```

### 2.2 Code Actions - Extract Method

**US-2.1: Simple Extraction**
```
As a developer
I want to extract selected lines into new function
So that code organization improves

Acceptance Criteria:
Given:
  def calculate_total():
      subtotal = price * quantity  # [SELECT START]
      tax = subtotal * 0.08        # [SELECT END]
      return subtotal + tax

When: textDocument/codeAction at selection
Then: CodeAction with:
  - title = "Extract Method"
  - kind = "refactor.extract"
  - edit creates new function with correct params/returns
  - Applied edit produces valid Python
  - Original behavior preserved
```

**US-2.2: Complex Scenarios** (With params, returns, async, types)

See full PRD for 20 extract method test scenarios.

### 2.3 Code Actions - Import Symbol

**US-3.1: Single Symbol Import**
```
As a developer
I want auto-import for undefined symbol at cursor
So that manual import lookup avoided

Acceptance Criteria:
- Symbol search across project + Python path
- Import inserted at correct position
- PEP 8 import grouping (stdlib, third-party, local)
- Multiple matches → multiple CodeActions
```

**US-3.2: Bulk Import**
```
As a developer
I want bulk import for all undefined symbols
So that file-wide imports handled efficiently

Acceptance Criteria:
- All undefined symbols resolved atomically
- Correct import grouping/sorting
- Single WorkspaceEdit operation
```

---

## 3. Technical Architecture

### 3.1 Test Framework Stack

**Primary Framework: pytest-lsp**
```python
# Dependencies
pytest = "^8.0"
pytest-lsp = "^0.4.0"           # Primary e2e framework
pytest-asyncio = "^0.23.0"      # Async test support
deepdiff = "^6.0"               # Response comparison
jsonschema = "^4.0"             # Protocol validation
pyfakefs = "^5.0"               # Virtual filesystem
pytest-benchmark = "^4.0"       # Performance testing
pytest-timeout = "^2.2"         # Timeout control
pytest-html = "^4.0"            # Test reporting
```

**Justification:**
- ✅ Built for LSP testing
- ✅ Async/await native
- ✅ Realistic client simulation
- ✅ Community proven
- ⚠️ Slower than threading (acceptable per requirements)

### 3.2 Directory Structure

```
tests/
├── e2e/                           # All e2e tests
│   ├── conftest.py                # Shared fixtures
│   ├── fixtures/                  # Test data
│   │   ├── sample_projects/       # Complete Python projects
│   │   ├── code_samples/          # Individual snippets
│   │   └── expected_results/      # Golden files
│   ├── helpers/                   # Utilities
│   │   ├── assertions.py          # LSP validators
│   │   ├── builders.py            # Request builders
│   │   └── matchers.py            # Custom matchers
│   ├── test_lifecycle.py          # Init/shutdown (10 tests)
│   ├── test_code_actions.py       # Extract/import (35 tests)
│   ├── test_symbol_search.py      # Symbol ops (10 tests)
│   ├── test_text_sync.py          # Document sync (8 tests)
│   ├── test_error_handling.py     # Errors (15 tests)
│   ├── test_edge_cases.py         # Edge cases (12 tests)
│   └── test_performance.py        # Benchmarks (8 tests)
└── unit/                          # Existing tests
```

### 3.3 Core Fixtures

```python
@pytest.fixture
async def lsp_client(simple_project):
    """Configured LSP client connected to server."""
    config = ClientServerConfig(
        server_command=["python", "-m", "cst_lsp.server"],
        root_uri=simple_project.as_uri(),
    )
    async with LanguageClient(config) as client:
        yield client

@pytest.fixture
def simple_project(tmp_path):
    """5-file Python project."""
    # Creates realistic test project structure

@pytest.fixture
def complex_project(tmp_path):
    """50-file Python project for performance tests."""
```

---

## 4. Implementation Roadmap

### Phase 1: Foundation (Week 1-2) - **START HERE**

**Goal:** Core infrastructure + 5 critical tests

**Tasks:**
1. Install pytest-lsp dependencies
2. Create tests/e2e/ structure
3. Implement base fixtures (lsp_client, simple_project)
4. Create assertion helpers (assert_lsp_response, assert_text_edit_correct)
5. Implement 5 critical tests:
   - `test_initialize_with_capabilities()`
   - `test_shutdown_sequence()`
   - `test_extract_method_simple()`
   - `test_import_single_symbol()`
   - `test_invalid_range_handling()`
6. Integrate with CI (GitHub Actions)

**Success Criteria:**
- All 5 tests pass reliably
- Test suite <30s
- CI integrated

**Effort:** 12-16 hours

### Phase 2: Full Coverage (Week 3-5)

**Tests:** 63 additional tests (68 total)
**Coverage:** >90% LSP protocol
**Effort:** 24-32 hours

### Phase 3: Edge Cases & Performance (Week 6-7)

**Tests:** 23 additional tests (91 total)
**Coverage:** Complete suite with benchmarks
**Effort:** 16-20 hours

---

## 5. Success Metrics

| Metric | Phase 1 | Phase 2 | Phase 3 |
|--------|---------|---------|---------|
| **Test Count** | 5 | 68 | 91 |
| **Protocol Coverage** | 30% | 90% | 95% |
| **Suite Runtime** | <30s | <90s | <120s |
| **Flake Rate** | <2% | <2% | <1% |
| **Code Coverage** | 40% | 80% | 85% |

---

## 6. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| pytest-lsp limitations | Evaluate in Phase 1, fallback to threading |
| Async complexity | Invest in fixtures/helpers early |
| Test data maintenance | Parameterized tests, fixture factories |
| CI timeouts | Parallel execution (pytest-xdist) |
| Flaky tests | Proper async handling, strict timeouts |

---

## 7. Next Steps

**Immediate Actions:**
1. ✅ Review PRD (this document)
2. ⏭️ Begin Phase 1 implementation
3. ⏭️ Add pytest-lsp to pyproject.toml
4. ⏭️ Create test infrastructure
5. ⏭️ Implement 5 critical tests

**Future Phases:**
- Phase 2: Full protocol coverage (after Phase 1 validation)
- Phase 3: Edge cases + performance (after Phase 2 completion)

---

For complete details on:
- All 91 test scenarios (exhaustive breakdown)
- Assertion patterns and helper functions
- Performance benchmarks and thresholds
- CI/CD integration strategies
- Sample test implementations

See sections 5-11 in the full analysis above.

**Total Investment:** 6-8 working days for production-grade e2e testing infrastructure.
