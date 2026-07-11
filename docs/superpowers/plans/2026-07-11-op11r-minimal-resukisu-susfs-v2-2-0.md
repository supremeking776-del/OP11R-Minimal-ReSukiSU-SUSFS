# OP11R Minimal ReSukiSU + SUSFS v2.2.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the `op11r-minimal-susfs` fork so `build-op11r-minimal.yml` produces an auditable SUSFS-only kernel zip via GitHub Actions, then flash it to the device.

**Architecture:** Six-file diff to the fork at `github.com/supremeking776-del/OP11R-Minimal-ReSukiSU-SUSFS` branch `op11r-minimal-susfs`. Bump ReSukiSU/SUSFS pins to v2.2.0-r4 era, expand kernel-config verification from 5 to 23 assertions, keep the Python test suite as the fail-closed pre-checkout gate. TDD flow: update tests first (they fail), then update code (they pass).

**Tech Stack:** GitHub Actions (ubuntu-24.04), Python 3 unittest, bash, git, AnyKernel3, ReSukiSU 35003, SUSFS v2.2.0, magiskboot (device-side), adb + fastboot (host-side).

**Spec:** `docs/superpowers/specs/2026-07-11-op11r-minimal-resukisu-susfs-v2-2-0-design.md`

---

## File Structure

**Files touched (all in `C:\Users\akash\Desktop\PIXEL_ROOT\ONEPLUS 11R\OP11R-Minimal-ReSukiSU-SUSFS\`):**

| Path | Action | Responsibility |
|---|---|---|
| `tests/test_minimal_build.py` | Modify | Guardrail — asserts every pin/config/verification value we care about; must fail-fast at CI pre-checkout stage. |
| `.github/workflows/build-op11r-minimal.yml` | Modify | Single workflow entry point; passes pins as inputs to build-kernel action. |
| `.github/actions/build-kernel/action.yml` | Modify | Existing 2488-line library; only line 1997-2001 verification block expands to 19 asserts. |
| `manifests/oos16/oneplus_11r_w.xml` | Modify (conditional) | Kernel-source revision pins; only AnyKernel3 refreshes if `wild/sm8475` HEAD moved. |
| `configs/oos16/OP11r.json` | No change | Already correct (`susfs=true`, all others `false`). |
| `.github/actions/kernel-source-sync/action.yml` | No change | Toolchain cache + fallback fetch stays as-is. |

**Files touched in parent workspace:**

| Path | Action | Responsibility |
|---|---|---|
| `../METHOD_OP11R.md` | Modify (append) | v3.1 addendum documenting the custom-kernel flash flow. |

---

## Prerequisites

Before Task 1 the engineer needs:
- A working directory at `C:\Users\akash\Desktop\PIXEL_ROOT\ONEPLUS 11R\OP11R-Minimal-ReSukiSU-SUSFS`, on branch `op11r-minimal-susfs`.
- `git`, `python3`, `curl` available on PATH (Windows Git Bash is fine).
- `gh` CLI authenticated (`gh auth status` returns green) — needed for Task 8 workflow dispatch and Task 10 artifact download.
- adb + fastboot on PATH (SDK platform-tools v37.0.0+) — needed for Task 11 device flash.
- OP11R device at `a94f7320`, currently on OOS 16.0.5.700 slot B rooted (per METHOD_OP11R.md v3.0).

---

## Task 1: Resolve AnyKernel3 HEAD SHA for `wild/sm8475`

**Files:**
- Read: none (network only)
- Output: SHA string used in Task 5 and Task 6

- [ ] **Step 1: Query the current HEAD**

Run:
```bash
git ls-remote https://github.com/huangdihd/AnyKernel3.git refs/heads/wild/sm8475
```

Expected output format (one line):
```
<40-hex-char-sha>	refs/heads/wild/sm8475
```

- [ ] **Step 2: Record the SHA**

Capture the first field (40 hex chars). Record it as `ANYKERNEL3_SHA`. This value gets used in Task 5 (manifest edit) and Task 6 (test file edit).

**Fallback:** if `ls-remote` returns nothing or errors (network problem, branch renamed), use the existing pin `ea531d03965f702a45e1b0ab7c5db8d196c975c3` and note the fallback in the Task 5 commit message.

- [ ] **Step 3: No commit yet**

This task doesn't modify files; nothing to commit.

---

## Task 2: Verify current tests pass against current state

Before making any changes, confirm the existing test suite is green. Establishes the baseline.

**Files:**
- Test: `tests/test_minimal_build.py`

- [ ] **Step 1: Run the current test suite**

Run:
```bash
cd "C:/Users/akash/Desktop/PIXEL_ROOT/ONEPLUS 11R/OP11R-Minimal-ReSukiSU-SUSFS"
python3 tests/test_minimal_build.py -v
```

Expected: 5 tests, all PASS.
```
test_build_action_excludes_unrelated_kernel_changes ... ok
test_build_fails_closed_and_uploads_auditable_artifacts ... ok
test_manifest_pins_verified_source_revisions ... ok
test_op11r_config_enables_only_susfs ... ok
test_source_sync_uses_proven_cache_with_direct_fallback ... ok
----------------------------------------------------------------------
Ran 5 tests in 0.0XXs

OK
```

If any test fails at this baseline, STOP — the fork is in an unexpected state. Do not proceed.

- [ ] **Step 2: No commit**

Baseline check only.

---

## Task 3: Update `test_workflow_is_single_target_and_pinned` for v2.2.0-r4 (test fails)

**Files:**
- Modify: `tests/test_minimal_build.py`

- [ ] **Step 1: Apply the constant swap**

Open `tests/test_minimal_build.py`. Locate the block in `test_workflow_is_single_target_and_pinned` that currently reads:

```python
        self.assertIn(
            "5f702753cf3dbf162ce16e544d46fbed3fa32d0a",
            workflow,
        )
        self.assertIn(
            "86114db0c49f20fa7857b8b559f3ab87cbc2d00d",
            workflow,
        )
        self.assertIn(
            "actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10",
            workflow,
        )
```

Replace with:

```python
        self.assertIn(
            "e8f607a2cb1eb6f153809987eccd0d7a40ea1f70",
            workflow,
        )
        self.assertIn(
            "4003ecf2d01c6d13fa8edf6c4f2607365738dc3d",
            workflow,
        )
        self.assertIn(
            "actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10",
            workflow,
        )
        self.assertIn("expected_ksu_version: 35003", workflow)
        self.assertIn("expected_susfs_version: v2.2.0", workflow)
        self.assertIn(
            "expected_kernel_release: 5.10.236-android12-OP11R-RESUKISU-SUSFS",
            workflow,
        )
```

- [ ] **Step 2: Run test and confirm it now fails**

Run:
```bash
python3 tests/test_minimal_build.py MinimalBuildTests.test_workflow_is_single_target_and_pinned -v
```

Expected: FAIL with `AssertionError: 'e8f607a2cb1eb6f153809987eccd0d7a40ea1f70' not found in ...`

- [ ] **Step 3: No commit yet**

Tests must still fail — implementation comes in Task 5.

---

## Task 4: Update `test_build_fails_closed_and_uploads_auditable_artifacts` for expanded verification (test fails)

**Files:**
- Modify: `tests/test_minimal_build.py`

- [ ] **Step 1: Update the version-string assertions**

In the same file, in `test_build_fails_closed_and_uploads_auditable_artifacts`, locate:

```python
        self.assertIn("expected_ksu_version: 34909", workflow)
        self.assertIn("expected_susfs_version: v2.1.0", workflow)
```

Replace with:

```python
        self.assertIn("expected_ksu_version: 35003", workflow)
        self.assertIn("expected_susfs_version: v2.2.0", workflow)
```

- [ ] **Step 2: Expand the assertions tuple**

Locate the `for assertion in (...)` block in the same test. Replace the entire tuple with:

```python
        for assertion in (
            'if [ "$KSU_COMMIT_SHA" != "${{ inputs.ksu_branch_or_hash }}" ]',
            'if [ "$KSU_VERSION" != "${{ inputs.expected_ksu_version }}" ]',
            'if [ "$susfs_version" != "${{ inputs.expected_susfs_version }}" ]',
            'grep -q "^CONFIG_KSU=y$" "$OUT/.config"',
            'grep -q "^CONFIG_KSU_SUSFS=y$" "$OUT/.config"',
            'grep -q "^CONFIG_KSU_SUSFS_HAS_MAGIC_MOUNT=y$" "$OUT/.config"',
            'grep -q "^CONFIG_KSU_SUSFS_SUS_PATH=y$" "$OUT/.config"',
            'grep -q "^CONFIG_KSU_SUSFS_SUS_MOUNT=y$" "$OUT/.config"',
            'grep -q "^CONFIG_KSU_SUSFS_AUTO_ADD_SUS_KSU_DEFAULT_MOUNT=y$" "$OUT/.config"',
            'grep -q "^CONFIG_KSU_SUSFS_AUTO_ADD_SUS_BIND_MOUNT=y$" "$OUT/.config"',
            'grep -q "^CONFIG_KSU_SUSFS_SUS_KSTAT=y$" "$OUT/.config"',
            'grep -q "^CONFIG_KSU_SUSFS_TRY_UMOUNT=y$" "$OUT/.config"',
            'grep -q "^CONFIG_KSU_SUSFS_AUTO_ADD_TRY_UMOUNT_FOR_BIND_MOUNT=y$" "$OUT/.config"',
            'grep -q "^CONFIG_KSU_SUSFS_SUS_MAP=y$" "$OUT/.config"',
            'grep -q "^CONFIG_KSU_SUSFS_OPEN_REDIRECT=y$" "$OUT/.config"',
            'grep -q "^CONFIG_KSU_SUSFS_SPOOF_UNAME=y$" "$OUT/.config"',
            'grep -q "^CONFIG_KSU_SUSFS_ENABLE_LOG=y$" "$OUT/.config"',
            'grep -q "^CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS=y$" "$OUT/.config"',
            'grep -q "^CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG=y$" "$OUT/.config"',
            '! grep -q "^CONFIG_KSU_SUSFS_SUS_OVERLAYFS=y$" "$OUT/.config"',
            '! grep -q "^CONFIG_KSU_SUSFS_SUS_SU=y$" "$OUT/.config"',
            '! grep -qE "^CONFIG_(TCP_CONG_BBR|BBG|SM8750_HMBIRD_SCX|DROIDSPACES|NTSYNC|IP_SET|IP6_NAT)=y$" "$OUT/.config"',
            'grep -q "${{ inputs.expected_kernel_release }}"',
        ):
            self.assertIn(assertion, action)
```

- [ ] **Step 3: Run test and confirm it now fails**

Run:
```bash
python3 tests/test_minimal_build.py MinimalBuildTests.test_build_fails_closed_and_uploads_auditable_artifacts -v
```

Expected: FAIL with an `AssertionError` on one of the new grep strings not found in action.yml (e.g., `'grep -q "^CONFIG_KSU_SUSFS_HAS_MAGIC_MOUNT=y$" "$OUT/.config"' not found`).

- [ ] **Step 4: No commit yet**

---

## Task 5: Update `test_manifest_pins_verified_source_revisions` if AnyKernel3 SHA changed

**Files:**
- Modify: `tests/test_minimal_build.py`

- [ ] **Step 1: Decide whether to update**

If Task 1 returned the SAME SHA as the existing pin (`ea531d03965f702a45e1b0ab7c5db8d196c975c3`), skip this task entirely.

If Task 1 returned a DIFFERENT SHA, continue with Step 2.

- [ ] **Step 2: Update the expected dict**

In `test_manifest_pins_verified_source_revisions`, replace the AnyKernel3 line:

```python
                "AnyKernel3": "ea531d03965f702a45e1b0ab7c5db8d196c975c3",
```

with:

```python
                "AnyKernel3": "<ANYKERNEL3_SHA from Task 1>",
```

Substitute the literal 40-hex-char SHA. Leave the other 4 revisions unchanged (they're KMI-stable).

- [ ] **Step 3: No commit yet**

The manifest file itself gets edited in Task 7; both need to change together to keep this test green.

---

## Task 6: Update workflow pins to v2.2.0-r4

**Files:**
- Modify: `.github/workflows/build-op11r-minimal.yml`

- [ ] **Step 1: Apply the pin swap**

Open `.github/workflows/build-op11r-minimal.yml`. Locate lines 45-49:

```yaml
          ksu_branch_or_hash: 5f702753cf3dbf162ce16e544d46fbed3fa32d0a
          expected_ksu_version: 34909
          susfs_commit_hash_or_branch: 86114db0c49f20fa7857b8b559f3ab87cbc2d00d
          expected_susfs_version: v2.1.0
          expected_kernel_release: 5.10.236-android12-OP11R-RESUKISU-SUSFS
```

Replace with:

```yaml
          ksu_branch_or_hash: e8f607a2cb1eb6f153809987eccd0d7a40ea1f70
          expected_ksu_version: 35003
          susfs_commit_hash_or_branch: 4003ecf2d01c6d13fa8edf6c4f2607365738dc3d
          expected_susfs_version: v2.2.0
          expected_kernel_release: 5.10.236-android12-OP11R-RESUKISU-SUSFS
```

Only 4 lines actually change; `expected_kernel_release` stays the same.

- [ ] **Step 2: Run `test_workflow_is_single_target_and_pinned`; expect PASS now**

Run:
```bash
python3 tests/test_minimal_build.py MinimalBuildTests.test_workflow_is_single_target_and_pinned -v
```

Expected: PASS.

- [ ] **Step 3: Run `test_build_fails_closed_and_uploads_auditable_artifacts`; expect version part PASS, grep part FAIL**

Run:
```bash
python3 tests/test_minimal_build.py MinimalBuildTests.test_build_fails_closed_and_uploads_auditable_artifacts -v
```

Expected: FAIL on the new grep assertions (build-kernel action.yml verification block hasn't been expanded yet — that's Task 8).

- [ ] **Step 4: No commit yet**

---

## Task 7: Update `manifests/oos16/oneplus_11r_w.xml` (conditional on Task 1)

**Files:**
- Modify: `manifests/oos16/oneplus_11r_w.xml`

- [ ] **Step 1: Skip if SHA unchanged**

If Task 1 returned the existing pin, skip this entire task.

- [ ] **Step 2: Update the AnyKernel3 revision**

Open `manifests/oos16/oneplus_11r_w.xml`. Line 7 currently reads:

```xml
  <project remote="wild" name="AnyKernel3" path="AnyKernel3" revision="ea531d03965f702a45e1b0ab7c5db8d196c975c3"/>
```

Replace `ea531d03965f702a45e1b0ab7c5db8d196c975c3` with the SHA from Task 1. The other 4 `<project>` lines stay unchanged.

- [ ] **Step 3: Run `test_manifest_pins_verified_source_revisions`; expect PASS**

Run:
```bash
python3 tests/test_minimal_build.py MinimalBuildTests.test_manifest_pins_verified_source_revisions -v
```

Expected: PASS.

If FAIL, the SHA in Task 5's edit and this manifest edit don't match; fix and retry.

- [ ] **Step 4: No commit yet**

---

## Task 8: Expand the SUSFS Kconfig verification block in build-kernel action

**Files:**
- Modify: `.github/actions/build-kernel/action.yml` (lines 1997-2001)

- [ ] **Step 1: Read the current block to confirm exact indentation**

Run:
```bash
sed -n '1995,2003p' .github/actions/build-kernel/action.yml
```

Confirm lines 1997-2001 look exactly like:
```
        grep -q "^CONFIG_KSU=y$" "$OUT/.config"
        grep -q "^CONFIG_KSU_SUSFS=y$" "$OUT/.config"
        grep -q "^CONFIG_KSU_SUSFS_SUS_MAP=y$" "$OUT/.config"
        grep -q "^CONFIG_KSU_SUSFS_OPEN_REDIRECT=y$" "$OUT/.config"
        grep -q "^CONFIG_KSU_SUSFS_SPOOF_UNAME=y$" "$OUT/.config"
```

Indentation: 8 spaces at start of each line.

- [ ] **Step 2: Replace the 5-line block with the 19-line block**

Using an Edit / sed / manual editor operation, replace exactly those 5 lines with:

```
        grep -q "^CONFIG_KSU=y$" "$OUT/.config"
        grep -q "^CONFIG_KSU_SUSFS=y$" "$OUT/.config"
        grep -q "^CONFIG_KSU_SUSFS_HAS_MAGIC_MOUNT=y$" "$OUT/.config"
        grep -q "^CONFIG_KSU_SUSFS_SUS_PATH=y$" "$OUT/.config"
        grep -q "^CONFIG_KSU_SUSFS_SUS_MOUNT=y$" "$OUT/.config"
        grep -q "^CONFIG_KSU_SUSFS_AUTO_ADD_SUS_KSU_DEFAULT_MOUNT=y$" "$OUT/.config"
        grep -q "^CONFIG_KSU_SUSFS_AUTO_ADD_SUS_BIND_MOUNT=y$" "$OUT/.config"
        grep -q "^CONFIG_KSU_SUSFS_SUS_KSTAT=y$" "$OUT/.config"
        grep -q "^CONFIG_KSU_SUSFS_TRY_UMOUNT=y$" "$OUT/.config"
        grep -q "^CONFIG_KSU_SUSFS_AUTO_ADD_TRY_UMOUNT_FOR_BIND_MOUNT=y$" "$OUT/.config"
        grep -q "^CONFIG_KSU_SUSFS_SUS_MAP=y$" "$OUT/.config"
        grep -q "^CONFIG_KSU_SUSFS_OPEN_REDIRECT=y$" "$OUT/.config"
        grep -q "^CONFIG_KSU_SUSFS_SPOOF_UNAME=y$" "$OUT/.config"
        grep -q "^CONFIG_KSU_SUSFS_ENABLE_LOG=y$" "$OUT/.config"
        grep -q "^CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS=y$" "$OUT/.config"
        grep -q "^CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG=y$" "$OUT/.config"
        ! grep -q "^CONFIG_KSU_SUSFS_SUS_OVERLAYFS=y$" "$OUT/.config"
        ! grep -q "^CONFIG_KSU_SUSFS_SUS_SU=y$" "$OUT/.config"
        ! grep -qE "^CONFIG_(TCP_CONG_BBR|BBG|SM8750_HMBIRD_SCX|DROIDSPACES|NTSYNC|IP_SET|IP6_NAT)=y$" "$OUT/.config"
```

Preserve the 8-space indentation. The next line (currently line 2002, `KCFLAGS="..."`) stays untouched.

- [ ] **Step 3: Verify the block is exactly 19 lines**

Run:
```bash
awk 'NR==1997 { in_block=1 } in_block && /^        grep|^        ! grep/ { count++ } in_block && !/^        grep|^        ! grep|^$/ && count>0 { print "line count:", count; exit }' .github/actions/build-kernel/action.yml
```

Expected: `line count: 19`

- [ ] **Step 4: No commit yet**

---

## Task 9: Run full test suite; all 5 tests must pass

**Files:**
- Test: `tests/test_minimal_build.py`

- [ ] **Step 1: Run every test**

Run:
```bash
python3 tests/test_minimal_build.py -v
```

Expected: all 5 tests PASS.
```
test_build_action_excludes_unrelated_kernel_changes ... ok
test_build_fails_closed_and_uploads_auditable_artifacts ... ok
test_manifest_pins_verified_source_revisions ... ok
test_op11r_config_enables_only_susfs ... ok
test_source_sync_uses_proven_cache_with_direct_fallback ... ok
----------------------------------------------------------------------
Ran 5 tests in 0.0XXs

OK
```

If any test fails, STOP and diagnose. Do not proceed to commit.

- [ ] **Step 2: No commit yet**

Commit happens as one atomic changeset in Task 10.

---

## Task 10: Commit all changes as one atomic changeset

**Files:**
- All changes from Tasks 3-8 get committed together.

- [ ] **Step 1: Review what's staged and what's dirty**

Run:
```bash
git status
git diff --stat
```

Expected changed files:
```
 .github/actions/build-kernel/action.yml           |  14 +++++++++++--
 .github/workflows/build-op11r-minimal.yml         |   8 ++++----
 tests/test_minimal_build.py                       |  22 ++++++++++++++++++++--
```
(plus `manifests/oos16/oneplus_11r_w.xml` if Task 7 ran)

- [ ] **Step 2: Stage the four modified files**

Run:
```bash
git add tests/test_minimal_build.py .github/workflows/build-op11r-minimal.yml .github/actions/build-kernel/action.yml manifests/oos16/oneplus_11r_w.xml
```

Note: if `manifests/oos16/oneplus_11r_w.xml` wasn't modified, `git add` on it is a no-op.

- [ ] **Step 3: Create the commit**

Run:
```bash
git -c user.email="newerasooo@outlook.com" -c user.name="akash" commit -m "$(cat <<'EOF'
feat: pin OP11R minimal build to ReSukiSU 35003 + SUSFS v2.2.0

Bump workflow inputs from v2.1.0-era to v2.2.0-r4 upstream pins:
- ksu_branch_or_hash: 5f702753 -> e8f607a2 (KSU 34909 -> 35003)
- susfs_commit: 86114db0 -> 4003ecf2 (v2.1.0 -> v2.2.0, android12-5.10)

Expand build-kernel config-verification block from 5 to 19 assertions
(15 SUSFS Kconfig positive + CONFIG_KSU + 2 SUSFS negatives + 1
combined non-SUSFS negative regex). Kernel release string unchanged
so METHOD_OP11R.md flash flow (Step 5) requires only the AK3 filename
bump.

Tests updated to gate the new pins and expanded assertion set at
pre-checkout stage. All 5 tests pass locally.

Spec: docs/superpowers/specs/2026-07-11-op11r-minimal-resukisu-susfs-v2-2-0-design.md

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 4: Verify the commit landed**

Run:
```bash
git log -1 --stat
```

Expected: HEAD is a new commit on `op11r-minimal-susfs` showing the modified files.

---

## Task 11: Push branch to origin

**Files:**
- Remote: `origin` (`github.com/supremeking776-del/OP11R-Minimal-ReSukiSU-SUSFS`)

- [ ] **Step 1: Confirm remote and branch**

Run:
```bash
git remote -v
git branch --show-current
```

Expected:
```
origin	https://github.com/supremeking776-del/OP11R-Minimal-ReSukiSU-SUSFS.git (fetch)
origin	https://github.com/supremeking776-del/OP11R-Minimal-ReSukiSU-SUSFS.git (push)
op11r-minimal-susfs
```

- [ ] **Step 2: Push**

Run:
```bash
git push -u origin op11r-minimal-susfs
```

Expected: push succeeds; `origin/op11r-minimal-susfs` created / updated.

If push is rejected because upstream moved (unlikely on a personal fork branch), run `git pull --rebase origin op11r-minimal-susfs`, resolve any conflicts, then retry the push.

- [ ] **Step 3: No local commit — push only**

---

## Task 12: Dispatch the workflow on GitHub Actions

**Files:**
- Remote workflow: `.github/workflows/build-op11r-minimal.yml`

- [ ] **Step 1: Dispatch via `gh` CLI**

Run:
```bash
gh workflow run build-op11r-minimal.yml --ref op11r-minimal-susfs --repo supremeking776-del/OP11R-Minimal-ReSukiSU-SUSFS
```

Expected: `✓ Created workflow_dispatch event for build-op11r-minimal.yml at op11r-minimal-susfs`

- [ ] **Step 2: Capture the run ID**

Wait ~5 seconds for the run to register, then:
```bash
gh run list --workflow=build-op11r-minimal.yml --repo supremeking776-del/OP11R-Minimal-ReSukiSU-SUSFS --limit 1
```

Expected: one row, status `queued` or `in_progress`. Capture the run ID (first column, numeric).

- [ ] **Step 3: Monitor the run**

Run:
```bash
gh run watch <RUN_ID> --repo supremeking776-del/OP11R-Minimal-ReSukiSU-SUSFS
```

The workflow takes ~40-90 minutes (kernel compile is heavy).

**Gate check:** On success, all six fail-closed gates from the spec's Section 6 have passed:
- Gate 1 (pre-checkout Python tests): ok
- Gate 2 (KSU sha + version): KSU_COMMIT_SHA matched, KSU_VERSION = 35003
- Gate 3 (SUSFS version): v2.2.0
- Gate 4 (Kconfig integrity): all 19 assertions passed
- Gate 5 (kernel uname string): matched
- Gate 6 (non-SUSFS features off): combined negative grep passed

**If the run fails:** identify which gate failed via `gh run view <RUN_ID> --log --repo …`. Most common failure = Gate 2 (KSU_VERSION ≠ 35003 because the SHA we picked doesn't produce that version). Fix by adjusting `ksu_branch_or_hash` in `build-op11r-minimal.yml` to a nearby commit (± 1-3 commits on `main`), re-running Tasks 3, 6, 9, 10, 11, 12.

- [ ] **Step 4: No local commit; monitoring only**

---

## Task 13: Download the artifact locally

**Files:**
- Create: `../artifacts/AK3_OP11r_OOS16_android12-5.10.236_ReSukiSU_35003_SuSFS_v2.2.0.zip`
- Create: `../artifacts/Image`
- Create: `../artifacts/SHA256SUMS`
- Create: `../artifacts/build-provenance.json`

- [ ] **Step 1: Download the artifact**

From inside the fork directory:
```bash
gh run download <RUN_ID> --dir ../artifacts --repo supremeking776-del/OP11R-Minimal-ReSukiSU-SUSFS
```

This creates `../artifacts/` (parallel to the fork) with the 4 files listed above.

- [ ] **Step 2: Verify SHA256SUMS**

Run:
```bash
cd ../artifacts
sha256sum -c SHA256SUMS
```

Expected:
```
AK3_OP11r_OOS16_android12-5.10.236_ReSukiSU_35003_SuSFS_v2.2.0.zip: OK
Image: OK
```

If any file reports FAILED, re-download; do not flash a corrupted zip.

- [ ] **Step 3: Read build-provenance.json for the record**

Run:
```bash
cat build-provenance.json | python3 -m json.tool
```

Expected: shows the six inputs (`ksu_branch_or_hash`, `expected_ksu_version=35003`, `susfs_commit_hash_or_branch`, `expected_susfs_version=v2.2.0`, `expected_kernel_release`, `optimize_level=O2`), timestamps, and workflow run ID.

- [ ] **Step 4: No commit needed — artifact stays in `../artifacts/`**

---

## Task 14: Backup the currently working kernel BEFORE flashing

**Files:**
- Read from device: `/dev/block/by-name/boot_b`
- Save on host: `../backup_boot_b_pre_v2_2_0.img`

- [ ] **Step 1: Confirm device is connected and rooted**

Run:
```bash
adb -s a94f7320 shell "su -c id"
```

Expected: `uid=0(root) gid=0(root) groups=0(root) context=u:r:ksu:s0`

If FAIL, open the ReSukiSU app on the phone and grant root, wait 10 seconds, retry.

- [ ] **Step 2: Dump slot B boot to a device-local file**

Run:
```bash
adb -s a94f7320 shell "su -c 'dd if=/dev/block/by-name/boot_b of=/data/local/tmp/boot_b_backup.img bs=4M && chmod 644 /data/local/tmp/boot_b_backup.img'"
```

- [ ] **Step 3: Pull to host**

Run:
```bash
cd "C:/Users/akash/Desktop/PIXEL_ROOT/ONEPLUS 11R"
adb -s a94f7320 pull /data/local/tmp/boot_b_backup.img backup_boot_b_pre_v2_2_0_$(date +%Y%m%d).img
```

Expected: file of ~192 MB in the parent working directory. This is the r26 huangdihd kernel currently on the device — rollback insurance.

- [ ] **Step 4: Cleanup device-side backup**

Run:
```bash
adb -s a94f7320 shell "su -c 'rm /data/local/tmp/boot_b_backup.img'"
```

---

## Task 15: Flash the new AK3 zip to slot B

Mirrors METHOD_OP11R.md Step 5C with the new filename.

**Files:**
- Push to device: `../artifacts/AK3_OP11r_OOS16_android12-5.10.236_ReSukiSU_35003_SuSFS_v2.2.0.zip`
- Modify on device: `/dev/block/by-name/boot_b`

- [ ] **Step 1: Push the AK3 zip**

Run:
```bash
adb -s a94f7320 push "../artifacts/AK3_OP11r_OOS16_android12-5.10.236_ReSukiSU_35003_SuSFS_v2.2.0.zip" /sdcard/Download/
```

- [ ] **Step 2: Extract Image and bundled magiskboot on device**

Run:
```bash
adb -s a94f7320 shell "su -c 'mkdir -p /data/local/tmp/op11r_v220 && cd /data/local/tmp/op11r_v220 && /data/adb/ksu/bin/busybox unzip -o /sdcard/Download/AK3_OP11r_OOS16_android12-5.10.236_ReSukiSU_35003_SuSFS_v2.2.0.zip Image tools/magiskboot && chmod 755 tools/magiskboot'"
```

- [ ] **Step 3: Dump current slot B boot, unpack, replace kernel, repack**

Run each command; each waits for the previous:
```bash
adb -s a94f7320 shell "su -c 'cd /data/local/tmp/op11r_v220 && dd if=/dev/block/by-name/boot_b of=current_boot.img bs=4M'"
adb -s a94f7320 shell "su -c 'cd /data/local/tmp/op11r_v220 && ./tools/magiskboot unpack current_boot.img'"
adb -s a94f7320 shell "su -c 'cd /data/local/tmp/op11r_v220 && cp Image kernel'"
adb -s a94f7320 shell "su -c 'cd /data/local/tmp/op11r_v220 && ./tools/magiskboot repack current_boot.img new_boot.img'"
```

Expected: `new_boot.img` created; magiskboot output shows no errors.

- [ ] **Step 4: Write to slot B and verify SHA-256 match**

Run:
```bash
adb -s a94f7320 shell "su -c 'cd /data/local/tmp/op11r_v220 && dd if=new_boot.img of=/dev/block/by-name/boot_b bs=4M && sync && sha256sum new_boot.img /dev/block/by-name/boot_b'"
```

Expected: two SHA-256 lines with identical hashes. If they differ, DO NOT reboot — the write is corrupt. Investigate before rebooting.

- [ ] **Step 5: Reboot**

Run:
```bash
adb -s a94f7320 shell "su -c reboot"
```

---

## Task 16: Post-flash verification (matches METHOD Section 8.4)

**Files:**
- Read from device only.

- [ ] **Step 1: Wait for boot, then verify kernel string**

After the phone finishes booting (~60-90 sec), run:
```bash
adb -s a94f7320 wait-for-device
adb -s a94f7320 shell "su -c 'uname -r'"
```

Expected pre-SUSFS-init: `5.10.236-android12-OP11R-RESUKISU-SUSFS`

Post-SUSFS-init this becomes stock (spoofed), see Step 6.

- [ ] **Step 2: SUSFS v2.2.0 kernel init log**

Run:
```bash
adb -s a94f7320 shell "su -c 'dmesg 2>/dev/null | grep -iE \"susfs.*init|ksu.*init\" | head -10'"
```

Expected: `susfs is initialized! version: v2.2.0` and `KernelSU version 35003`.

- [ ] **Step 3: Root grant works**

Run:
```bash
adb -s a94f7320 shell "su -c id"
```

Expected: `uid=0(root) gid=0(root) groups=0(root) context=u:r:ksu:s0`

- [ ] **Step 4: All 8 userspace modules still active**

Run:
```bash
adb -s a94f7320 shell "su -c 'ls /data/adb/modules/ | sort'"
```

Expected exactly these 8 lines:
```
Yurikey
hma_oss_zygisk
playintegrityfix
rezygisk
susfs4ksu
treat_wheel
tricky_store
zygisk_lsposed
```

- [ ] **Step 5: SELinux enforcing + ReZygisk report**

Run:
```bash
adb -s a94f7320 shell "su -c 'getenforce; grep description /data/adb/modules/rezygisk/module.prop'"
```

Expected: `Enforcing` on first line; ReZygisk description contains `Monitor: ✅`, `ReZygisk 64-bit: ✅`, `ReZygisk 32-bit: ✅`.

- [ ] **Step 6: SUSFS runtime uname spoof active (non-root shell)**

Run:
```bash
adb -s a94f7320 shell "uname -r"
```

Expected: `5.10.236-android12-9-o-g2bee83b9e1eb` (stock string, SUSFS spoofed).

- [ ] **Step 7: SUSFS userspace R27 compatibility check**

Run:
```bash
adb -s a94f7320 shell "su -c 'dmesg 2>/dev/null | grep -iE \"susfs|ksu\" | tail -30'"
```

Look for `ENOSYS` or `EINVAL` errors around SUSFS ioctls. Expected: none.

If ENOSYS on a specific ioctl appears, note which flag the R27 userspace module tried to set. Not an emergency — nothing crashes; a specific runtime feature silently no-ops. Track in a separate follow-up task; do not rollback.

- [ ] **Step 8: Cleanup device-side extraction files**

Run:
```bash
adb -s a94f7320 shell "su -c 'rm -rf /data/local/tmp/op11r_v220'"
```

---

## Task 17: Append v3.1 addendum to METHOD_OP11R.md

**Files:**
- Modify: `C:\Users\akash\Desktop\PIXEL_ROOT\ONEPLUS 11R\METHOD_OP11R.md`

- [ ] **Step 1: Append the addendum block**

Open `METHOD_OP11R.md`. Locate the `## VERSION HISTORY` table at the very bottom. Add a new row before the closing `|` line:

```markdown
| v3.1 | 2026-07-11 | Documented custom-kernel path via own fork `github.com/supremeking776-del/OP11R-Minimal-ReSukiSU-SUSFS` branch `op11r-minimal-susfs`. Ships AK3 zip `AK3_OP11r_OOS16_android12-5.10.236_ReSukiSU_35003_SuSFS_v2.2.0.zip` with ReSukiSU 35003 + SUSFS v2.2.0, SUSFS-only Kconfig (all other WildKernels features disabled + build-time asserted off). Step 5 flash flow unchanged except for filename. See `OP11R-Minimal-ReSukiSU-SUSFS/docs/superpowers/specs/2026-07-11-op11r-minimal-resukisu-susfs-v2-2-0-design.md` for full design. |
```

- [ ] **Step 2: Insert a "Step 5-alt" section**

Immediately after the `### STEP 5` block ends (before `### STEP 6:`), insert this section:

```markdown

---

### STEP 5-alt: Flash custom SUSFS-only kernel (v3.1 path)

Use this when you want to boot the fork's SUSFS-only build instead of the huangdihd stock r26/r4 zip.

**Prerequisite:** AK3 zip artifact from a successful `build-op11r-minimal.yml` run on `github.com/supremeking776-del/OP11R-Minimal-ReSukiSU-SUSFS`, downloaded to `../artifacts/`. Verify SHA256 first:

```powershell
cd C:\Users\akash\Desktop\PIXEL_ROOT\artifacts
sha256sum -c SHA256SUMS
```

Then run the identical unpack/repack/flash sequence as Step 5C, but with the custom AK3 filename:

```powershell
adb push "..\artifacts\AK3_OP11r_OOS16_android12-5.10.236_ReSukiSU_35003_SuSFS_v2.2.0.zip" /sdcard/Download/
adb shell "su -c 'mkdir -p /data/local/tmp/op11r_v220 && cd /data/local/tmp/op11r_v220 && /data/adb/ksu/bin/busybox unzip -o /sdcard/Download/AK3_OP11r_OOS16_android12-5.10.236_ReSukiSU_35003_SuSFS_v2.2.0.zip Image tools/magiskboot && chmod 755 tools/magiskboot'"
adb shell "su -c 'cd /data/local/tmp/op11r_v220 && dd if=/dev/block/by-name/boot_b of=current_boot.img bs=4M'"
adb shell "su -c 'cd /data/local/tmp/op11r_v220 && ./tools/magiskboot unpack current_boot.img'"
adb shell "su -c 'cd /data/local/tmp/op11r_v220 && cp Image kernel'"
adb shell "su -c 'cd /data/local/tmp/op11r_v220 && ./tools/magiskboot repack current_boot.img new_boot.img'"
adb shell "su -c 'cd /data/local/tmp/op11r_v220 && dd if=new_boot.img of=/dev/block/by-name/boot_b bs=4M && sync && sha256sum new_boot.img /dev/block/by-name/boot_b'"
adb shell "su -c reboot"
```

After boot: `dmesg | grep susfs` shows `version: v2.2.0`, KernelSU version 35003. Non-root `uname -r` still returns the stock string via SUSFS `spoof_uname=2` — `susfs_config.sh` needs no changes.

**Rollback options (in order of speed):**

1. Instant slot switch to clean OOS 16.0.3.501:
   ```powershell
   adb reboot bootloader; fastboot --set-active=a; fastboot reboot
   ```
2. Re-flash r26 huangdihd rooted kernel on slot B (preserved as `AK3_ReSukiSU_34909_boot_b_20260711.img` in workspace root; also `backup_boot_b_pre_v2_2_0_YYYYMMDD.img` from pre-flash backup).
3. Hard rollback to stock 16.0.5.700 unrooted: `fastboot --slot=b flash boot boot.img`.

**SUSFS userspace R27 compatibility note:** R27 was built against SUSFS v2.1 kernel ABI. v2.2 is largely backward-compatible; if a specific runtime setting silently no-ops, replace R27 with a newer sidex15 release. Kernel doesn't need re-flashing.
```

- [ ] **Step 3: No commit** (METHOD_OP11R.md lives in the parent workspace, not a git repo). Save the file.

---

## Task 18: Add Play Integrity + banking-app validation as a follow-up task, not blocking

Steps 10B and 11 of METHOD_OP11R.md (BASIC + DEVICE + STRONG check, BharatPe test) were `⏳ PENDING` at v3.0. The v2.2.0 kernel doesn't change their PENDING status.

- [ ] **Step 1: Note the pending status in METHOD_OP11R.md**

At the bottom of the addendum's Step 5-alt section, add:

```markdown

**Not part of this plan:** BASIC / DEVICE / STRONG Play Integrity check with a checker app, and banking-app root-hiding test. Both were pending at v3.0 and remain pending; run them separately after confirming the v3.1 kernel boots and the 8 modules stay active.
```

- [ ] **Step 2: No commit** (as Task 17).

---

## Task 19: Final verification and summary

**Files:**
- No modifications.

- [ ] **Step 1: Confirm all files in expected state**

Run:
```bash
cd "C:/Users/akash/Desktop/PIXEL_ROOT/ONEPLUS 11R/OP11R-Minimal-ReSukiSU-SUSFS"
git log --oneline -3
git status
python3 tests/test_minimal_build.py -v 2>&1 | tail -8
```

Expected:
- `git log` shows the docs commit (`260f27e` or later) and the pins commit from Task 10.
- `git status` is clean OR shows only the artifact/backup files in parent workspace.
- All 5 Python tests pass.

- [ ] **Step 2: Confirm device state**

Run:
```bash
adb -s a94f7320 shell "su -c 'dmesg 2>/dev/null | grep -iE \"susfs is initialized|KernelSU version\" | head -5'"
adb -s a94f7320 shell "su -c 'ls /data/adb/modules/ | wc -l'"
adb -s a94f7320 shell "uname -r"
```

Expected:
- SUSFS v2.2.0 initialized, KernelSU version 35003
- 8 modules
- Non-root uname returns stock string (spoofed)

- [ ] **Step 3: Done.**

The custom kernel is running on slot B. Slot A holds pristine OOS 16.0.3.501. Rollback paths remain intact.

---

## Self-Review Notes (author, 2026-07-11)

**Spec coverage:**
- Spec §5.1 (workflow pins) → Task 6 ✓
- Spec §5.2 (OP11r.json unchanged) → no task needed ✓
- Spec §5.3 (manifest AnyKernel3 refresh) → Task 1 + Task 7 ✓
- Spec §5.4 (build-kernel action verification expansion) → Task 8 ✓
- Spec §5.5 (test_minimal_build.py updates) → Tasks 3, 4, 5 ✓
- Spec §5.6 (kernel-source-sync unchanged) → no task needed ✓
- Spec §6 (fail-closed gates) → Task 12 (Gate check bullet list) ✓
- Spec §7 (artifact/provenance) → Task 13 ✓
- Spec §8.1 (Step 5 replacement) → Task 15 ✓
- Spec §8.2 (kernel string / susfs_config compat) → Task 16 Step 6 ✓
- Spec §8.3 (R27 compat) → Task 16 Step 7 ✓
- Spec §8.4 (post-flash checklist) → Task 16 ✓
- Spec §8.5 (rollback layers) → Task 14 (backup) + Task 17 Step 2 (documented rollback) ✓
- Spec §8.6 (v3.1 addendum) → Task 17 ✓
- Spec §10 (open risks) → Task 12 Step 3 (KSU version mismatch retry loop) + Task 16 Step 7 (R27 flag no-op) ✓
- Spec §11 (success criteria) → Task 19 ✓

**Placeholder scan:** none.

**Type / name consistency:** `<RUN_ID>`, `<ANYKERNEL3_SHA>` are explicitly-named handoff values from earlier tasks; not placeholders. Path `../artifacts/` used consistently.
