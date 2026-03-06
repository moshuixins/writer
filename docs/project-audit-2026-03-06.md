# Project Audit And Refactor Log

Audit baseline: `docs/development-standard.md`
Audit date: 2026-03-06 (Asia/Shanghai)

## 1. Main Gaps

### P0 Fixed
1. Backend startup previously performed schema patching during import time.
   - Risk: tests, CLI entrypoints, and module imports had hidden side effects.
   - Fix: moved startup work behind an explicit bootstrap entry.

2. Frontend permission checks were split across auth hooks, menu filtering, route guards, and admin pages.
   - Risk: menu visibility and button visibility could drift.
   - Fix: centralized permission helpers and admin permission state mapping.

3. BOM in text files previously broke config and toolchain parsing.
   - Risk: runtime config load failures and broken builds.
   - Fix: added an encoding regression script and documented the rule.

### P1 Further Reduced
1. `backend/app/schema_bootstrap.py` previously mixed schema patching, admin initialization, RBAC seeding, and task recovery.
   - Fix: split responsibilities into schema patch, runtime bootstrap tasks, and a compatibility wrapper.

2. `frontend/src/views/admin/AdminAccounts.vue` previously mixed page state and business logic.
   - Fix: extracted `useAdminAccountsPage.ts` and reduced the page to a view shell.

3. `backend/app/api/auth.py` and `backend/app/api/accounts.py` repeated user, account, invite, and timestamp serialization.
   - Fix: added `backend/app/serializers.py` and moved shared response assembly there.

4. `frontend/src/views/admin/AdminAccounts.vue` still had a large template even after moving state logic out.
   - Fix: split the account list, users tab, and invites tab into dedicated child components with shared page styles.

5. `backend/app/api/chat.py`, `backend/app/api/materials.py`, and `backend/app/api/documents.py` still built session, material, book, draft, and export-history payloads inline.
   - Fix: extended `backend/app/serializers.py` and migrated those API payloads plus `DraftService` draft responses onto the shared serializer layer.

### P1 Remaining
1. Transport-specific SSE payloads in `chat.py` and task-progress payloads in upload/book services are still route-local by design.
2. The three dialogs in `AdminAccounts.vue` can still be extracted if we want an even thinner page shell.

## 2. Refactor Scope

### 2.1 Backend bootstrap
1. Added `backend/app/bootstrap.py` as the single runtime bootstrap entry.
2. Refactored `backend/app/main.py` to `create_app() + lifespan`.
3. Reused the same bootstrap flow in `backend/app/jobs/import_books.py`.

### 2.2 Backend schema bootstrap split
1. Added `backend/app/schema_patch.py` for schema-only patch work.
2. Added `backend/app/runtime_bootstrap_tasks.py` for admin init, RBAC seed, and interrupted task recovery.
3. Kept `backend/app/schema_bootstrap.py` as a compatibility wrapper.

### 2.3 Frontend permission cleanup
1. Added `frontend/src/utils/permission.ts`.
2. Moved `useAuth`, menu filtering, and route guards onto the shared permission helpers.
3. Added `frontend/src/views/admin/permissionState.ts` for admin page button state.
4. Added frontend permission regression checks for menu, route guard, and template bindings.

### 2.4 Frontend admin page split
1. Added `frontend/src/views/admin/useAdminAccountsPage.ts` for page state and actions.
2. Kept `frontend/src/views/admin/AdminAccounts.vue` as the page shell.
3. Added `frontend/src/views/admin/components/AdminAccountsList.vue`.
4. Added `frontend/src/views/admin/components/AdminAccountUsersTab.vue`.
5. Added `frontend/src/views/admin/components/AdminAccountInvitesTab.vue`.
6. Added `frontend/src/views/admin/adminAccounts.css` for shared admin page styling.

### 2.5 Backend serializer consolidation
1. Added `backend/app/serializers.py`.
2. Updated `backend/app/api/auth.py` to use the shared auth user serializer.
3. Updated `backend/app/api/accounts.py` to use shared account, permission, invite, and account-user serializers.
4. Updated `backend/app/api/chat.py` to use shared chat session, chat message, draft, and message serializers.
5. Updated `backend/app/api/materials.py` to use shared material, book-source, book-scan, collection, and message serializers.
6. Updated `backend/app/api/documents.py` to use shared export-history serializers.
7. Updated `backend/app/services/draft_service.py` to reuse the shared draft serializer.

### 2.6 Quality guardrails
1. Added `frontend/scripts/permission-regression.ts`.
2. Added `scripts/check_text_encoding.py`.
3. Added backend API regressions for chat, materials, and documents serialized response shapes.

## 3. Validation

1. Encoding check: passed.
2. Backend regression tests: passed (`7` tests).
3. Frontend type check: passed.
4. Frontend permission regression: passed.
5. Frontend production build: passed.
6. Note: the permission regression script and Vite production build required elevated execution in this environment because sandboxed `spawn` calls returned `EPERM`. That was an environment limitation, not a code defect.
