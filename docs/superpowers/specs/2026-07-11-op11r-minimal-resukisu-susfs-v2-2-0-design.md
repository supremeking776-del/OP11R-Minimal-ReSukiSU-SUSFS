# OP11R Minimal ReSukiSU + SUSFS v2.2.0 — Custom Kernel Build Spec

**Status**: Approved for implementation planning
**Date**: 2026-07-11
**Target repo**: `github.com/supremeking776-del/OP11R-Minimal-ReSukiSU-SUSFS`
**Branch**: `op11r-minimal-susfs`
**Fork parent**: `huangdihd/OnePlus_ReSukiSU_SUSFS` (release tag `v2.2.0-r4`)
**Target device**: OnePlus 11R 5G (CPH2487), SoC SM8475/waipio, OOS 16.0.5.700, kernel android12-5.10.236

---

## 1 · Overview

Build a single-target, auditable, SUSFS-only Android kernel for OnePlus 11R via GitHub Actions on a hardened fork of huangdihd's OnePlus_ReSukiSU_SUSFS repo. The build produces one AK3 flashable zip:

```
AK3_OP11r_OOS16_android12-5.10.236_ReSukiSU_35003_SuSFS_v2.2.0.zip
```

The zip is uploaded as a GitHub Actions artifact (private to the fork, 90-day retention). It flashes into slot B of the user's device using the existing `METHOD_OP11R.md` Step 5 flow, replacing the currently-installed huangdihd r26 kernel.

## 2 · Goals

- **G1** Deterministic CI build against v2.2.0-r4-era upstream pins: ReSukiSU commit `e8f607a2cb1eb6f153809987eccd0d7a40ea1f70` (KSU_VERSION 35003) + SUSFS `4003ecf2d01c6d13fa8edf6c4f2607365738dc3d` (v2.2.0, android12-5.10 branch). Bit-for-bit reproducibility is NOT a goal (ccache timestamps break it); pin-audit + fail-closed gates are.
- **G2** Only SUSFS features compiled in. All other WildKernels features (BBR, BBG, TTL, IP_SET, IP6_NAT, Unicode bypass, Droidspaces, NTSync, HMBIRD SCX, Rust build) disabled at config-JSON level and asserted off at build time.
- **G3** Fail-closed CI: any pin drift, missing SUSFS Kconfig, or leaked feature causes the workflow to fail with no artifact.
- **G4** Drop-in compatibility with `METHOD_OP11R.md` Step 5 (unpack → magiskboot → dd to boot_b) — no changes to Steps 1-4 or 6-11.
- **G5** Auditable strict Python test suite that gates the workflow before checkout and pins every value we care about.

## 3 · Non-goals

- Public releases, download pages, or GitHub Releases from this fork.
- Byte-for-byte reproducible builds (ccache breaks determinism; acceptable).
- Changes to userspace modules (ReZygisk, HMA, TEESimulator, LSPosed, PIF, Yurikey, SUSFS-userspace R27, TreatWheel) — they stay as METHOD_OP11R.md installed them.
- Alternate KMI targets, multiple device matrices, or scheduled builds.
- Kernel string parity with huangdihd stock (`OP-RESUKISU-huangdihd`). We use `OP11R-RESUKISU-SUSFS` so it's identifiably our custom build; SUSFS spoofs uname at runtime anyway.

## 4 · Architecture

Five-layer pipeline. Everything above the divider is code in the fork; everything below is fetched at build time.

```
┌──────────────────────────────────────────────────────────────┐
│  .github/workflows/build-op11r-minimal.yml                   │
│   workflow_dispatch, ubuntu-24.04, 120min timeout            │
│   ├─ python3 tests/test_minimal_build.py -v                  │
│   ├─ jq -c . configs/oos16/OP11r.json → $GITHUB_OUTPUT.json  │
│   └─ uses: ./.github/actions/build-kernel                    │
│      inputs: op_config_json, ksu_branch_or_hash=e8f607a2…,   │
│              expected_ksu_version=35003,                      │
│              susfs_commit_hash_or_branch=4003ecf2…,          │
│              expected_susfs_version=v2.2.0,                  │
│              expected_kernel_release=5.10.236-android12-     │
│                                     OP11R-RESUKISU-SUSFS,    │
│              optimize_level=O2, clean=true,                  │
│              minimal=true, debug=false                       │
├──────────────────────────────────────────────────────────────┤
│  .github/actions/build-kernel/action.yml (2488 lines)        │
│    SUSFS Kconfig block at ~L1183 writes 17 flags             │
│    if: minimal!='true' gates at L1246/1562/1646/1776         │
│    fail-closed asserts at L977 (KSU sha, KSU ver),           │
│                            L1008 (SUSFS ver),                │
│                            L1998 (expanded 17-flag grep),    │
│                            L2192 (uname string)              │
├──────────────────────────────────────────────────────────────┤
│  .github/actions/kernel-source-sync/action.yml               │
│   toolchain cache repo = huangdihd/OnePlus_ReSukiSU_SUSFS    │
│   direct-archive fallback if cache miss                      │
├──────────────────────────────────────────────────────────────┤
│  manifests/oos16/oneplus_11r_w.xml                           │
│   AnyKernel3 revision: <resolved at plan time from wild/     │
│     sm8475 HEAD; fallback ea531d03…>                         │
│   OnePlus kernel_common: 5b5ead1b… (KMI-stable, unchanged)   │
│   OnePlus modules_dt:    46ba2a7a… (unchanged)               │
│   build-tools:           10ab7831… (unchanged)               │
│   clang toolchain:       0fc3d01a… (unchanged)               │
│  configs/oos16/OP11r.json                                    │
│   susfs=true; all other features=false; uname=OP11R-         │
│   RESUKISU-SUSFS                                              │
├══════════════════════════════════════════════════════════════┤
│  Fetched at build time (not in the fork):                    │
│   ReSukiSU/ReSukiSU@e8f607a2  → setup.sh + KSU tree          │
│   simonpunk/susfs4ksu@4003ecf2 (android12-5.10)              │
│   CLO kernel/prebuilts + clang toolchain                     │
└──────────────────────────────────────────────────────────────┘
                             ↓
              AK3 zip + Image + SHA256SUMS + build-provenance.json
              uploaded as GH Actions artifact (90-day retention)
```

## 5 · File-level changes

Six files. Diffs summarize the semantic change; full text derived at plan time.

### 5.1 `.github/workflows/build-op11r-minimal.yml`
Bump three input pin lines: `ksu_branch_or_hash → e8f607a2cb1eb6f153809987eccd0d7a40ea1f70`, `expected_ksu_version → 35003`, `susfs_commit_hash_or_branch → 4003ecf2d01c6d13fa8edf6c4f2607365738dc3d`, `expected_susfs_version → v2.2.0`. Leave `expected_kernel_release` at `5.10.236-android12-OP11R-RESUKISU-SUSFS`.

### 5.2 `configs/oos16/OP11r.json`
No change. Already correct: `susfs=true`; hmbird/ds/bbg/bbr/ttl/ip_set/unicode/ntsync/rust_build/disk_cleanup all `false`; `uname=OP11R-RESUKISU-SUSFS`.

### 5.3 `manifests/oos16/oneplus_11r_w.xml`
Refresh the AnyKernel3 revision to whatever `git ls-remote https://github.com/huangdihd/AnyKernel3 wild/sm8475` returns at plan-execution time. If that command returns empty or errors, keep the existing pin `ea531d03965f702a45e1b0ab7c5db8d196c975c3`. The other four remote revisions are KMI-stable and stay unchanged.

### 5.4 `.github/actions/build-kernel/action.yml`
Expand the config-verification block (currently ~L1998-2001) from 5 grep assertions to 19. The current block writes 17 flags into the defconfig (15 `=y`, 2 `=n`); verification asserts all of them plus `CONFIG_KSU` plus a combined non-SUSFS negative grep.

15 positive assertions of the form `grep -q "^CONFIG_KSU_SUSFS_<flag>=y$" "$OUT/.config"` for: `KSU_SUSFS`, `KSU_SUSFS_HAS_MAGIC_MOUNT`, `KSU_SUSFS_SUS_PATH`, `KSU_SUSFS_SUS_MOUNT`, `KSU_SUSFS_AUTO_ADD_SUS_KSU_DEFAULT_MOUNT`, `KSU_SUSFS_AUTO_ADD_SUS_BIND_MOUNT`, `KSU_SUSFS_SUS_KSTAT`, `KSU_SUSFS_TRY_UMOUNT`, `KSU_SUSFS_AUTO_ADD_TRY_UMOUNT_FOR_BIND_MOUNT`, `KSU_SUSFS_SPOOF_UNAME`, `KSU_SUSFS_ENABLE_LOG`, `KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS`, `KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG`, `KSU_SUSFS_OPEN_REDIRECT`, `KSU_SUSFS_SUS_MAP`.

Plus the existing `CONFIG_KSU=y` assertion (KernelSU itself), for 16 positive greps total.

2 negative assertions `! grep -q "^CONFIG_KSU_SUSFS_<flag>=y$"` for: `SUS_OVERLAYFS`, `SUS_SU`.

1 combined negative grep asserting no non-SUSFS feature snuck in:
```
! grep -qE "^CONFIG_(TCP_CONG_BBR|BBG|SM8750_HMBIRD_SCX|DROIDSPACES|NTSYNC|IP_SET|IP6_NAT)=y$" "$OUT/.config"
```

No other changes to this file — `minimal: true` gates at L1246/1562/1646/1776 already skip Other Patches, Tmpfs, USB DWC3/OTG, and Build-based configs.

### 5.5 `tests/test_minimal_build.py`
Constant swaps in `test_workflow_is_single_target_and_pinned` and `test_build_fails_closed_and_uploads_auditable_artifacts` (see design doc Section 4). No new tests, no new fixtures. Test count stays at 5; assertions grow from ~30 to ~50.

`test_manifest_pins_verified_source_revisions` gets its `AnyKernel3` value refreshed to match whatever we pin in the manifest.

### 5.6 `.github/actions/kernel-source-sync/action.yml`
No changes.

## 6 · Fail-closed verification (six gates)

1. **Pre-checkout static validation** — `tests/test_minimal_build.py` runs before network access. Guards config JSON, manifest revisions, workflow shape, and version pins.
2. **ReSukiSU pin identity** — `KSU_COMMIT_SHA == e8f607a2…` AND `KSU_VERSION == 35003`.
3. **SUSFS pin identity** — `susfs_version == v2.2.0`.
4. **SUSFS Kconfig integrity** — 15 SUSFS flags + `CONFIG_KSU` itself all `=y`; 2 SUSFS flags (`SUS_OVERLAYFS`, `SUS_SU`) confirmed NOT `=y` in produced `.config`.
5. **Kernel uname string** — produced binary contains `5.10.236-android12-OP11R-RESUKISU-SUSFS`.
6. **Non-SUSFS features stayed off** — combined regex grep on 7 disabled feature configs.

Any gate failure = build fails, no artifact uploaded, red X in Actions UI.

## 7 · Artifact & provenance

On successful pass through gates 1-6, `build-kernel` action uploads:

- `AK3_OP11r_OOS16_android12-5.10.236_ReSukiSU_35003_SuSFS_v2.2.0.zip` — the AK3 flashable
- `Image` — raw kernel binary (for magiskboot-based flash paths)
- `SHA256SUMS` — sha256 of both above
- `build-provenance.json` — workflow inputs (all pins), gate results, timestamps, GH run ID

Retention: default 90 days. Private to the fork. No release, no public URL.

## 8 · METHOD_OP11R.md integration

### 8.1 Flash flow — Step 5 replacement

Steps 1-4 and 6-11 in `METHOD_OP11R.md` don't change. Step 5's AK3 zip filename becomes `AK3_OP11r_OOS16_android12-5.10.236_ReSukiSU_35003_SuSFS_v2.2.0.zip`; commands are identical. The custom kernel is written to slot B; slot A still holds the pristine 16.0.3.501 rollback.

### 8.2 Kernel string & SUSFS runtime spoof

Pre-SUSFS-init:  `uname -r` → `5.10.236-android12-OP11R-RESUKISU-SUSFS`
Post-SUSFS-init: `uname -r` (non-root) → `5.10.236-android12-9-o-g2bee83b9e1eb` (spoofed to stock via `spoof_uname=2`).

Existing `susfs_config.sh` values for `kernel_version`, `kernel_build`, and `fake_proc_version.txt` stay unchanged — they're the spoof *target*, independent of the compiled kernel string.

### 8.3 SUSFS v2.1 → v2.2 userspace module compatibility

Installed `ksu_module_susfs_1.5.2+_R27` was built against v2.1.0 kernel ABI. v2.2 adds `SUS_PATH` and reworks `SUS_MOUNT` internals. Approach: **flash first, verify dmesg, decide after**. Success signal: `dmesg | grep susfs` shows `susfs is initialized! version: v2.2.0` with no ENOSYS/EINVAL on ioctls.

If a specific runtime setting silently no-ops, the module can be updated post-flash independently — it's not gating the build.

### 8.4 Post-flash verification

Six-check sequence, stop and rollback on first failure: uname pre-SUSFS, SUSFS+KSU init log, root grant, module list intact (8 modules), SELinux enforcing, ReZygisk report, uname post-SUSFS.

### 8.5 Rollback layers (in preferred order)

1. **Instant slot switch** — `fastboot --set-active=a && fastboot reboot` → clean OOS 16.0.3.501 on slot A.
2. **Re-flash r26 huangdihd kernel** — write existing `AK3_ReSukiSU_34909_boot_b_20260711.img` back to `boot_b`. Fastest recovery to *rooted* working state.
3. **Hard rollback** — `fastboot --slot=b flash boot boot.img` → clean unrooted 16.0.5.700 on slot B.

Both r26 huangdihd image AND the new custom AK3 zip are kept on hand so the user can bounce between them.

### 8.6 METHOD_OP11R.md addendum

Add a v3.1 section documenting the custom-kernel path with pointers to this spec and the CI artifact. Original Step 5 (huangdihd r26 zip flash) stays intact so it remains a valid fallback path.

## 9 · Decisions & rationale

| Decision | Choice | Reason |
|---|---|---|
| Build vs download | Build via CI on GH Actions | User's explicit ask: auditable pipeline, private fork, no scheduled builds. |
| Version pin | v2.2.0-r4 era (ReSukiSU 35003 + SUSFS v2.2.0) | User linked the release; newer than currently-installed v2.1.0/34909. |
| SUSFS feature set | Full SUSFS v2.2.0 Kconfig block (17 flags, 15 on / 2 off) | User answered "everything SUSFS ships in v2.2.0". |
| Non-SUSFS features | All off, asserted at build time | User answered explicitly: "we only need SUSFS". |
| Kernel release string | Keep `OP11R-RESUKISU-SUSFS` (custom, ≠ huangdihd stock) | Identifiability, and SUSFS spoofs uname at runtime so it doesn't leak. |
| Test strictness | Update tests to v2.2.0 pins, keep strict | User answered explicitly. |
| Artifact delivery | GH Actions artifact only, no release | User answered explicitly. |
| Manifest AnyKernel3 pin | Refresh from `wild/sm8475` HEAD at plan time; fallback to existing pin | Kernel source is KMI-stable but AnyKernel3 moves with builds. |
| ReSukiSU SHA choice | `e8f607a26ef5…` (2026-07-04, last before huangdihd v2.2.0-r4 build 2026-07-05) | Best available guess for KSU_VERSION 35003; CI gate 2 catches mismatch. |
| Rollback | Keep r26 img + new AK3 zip both on hand | User answered explicitly. |
| SUSFS userspace R27 | Flash-and-verify, no preemptive upgrade | User answered explicitly. |
| METHOD addendum | Add v3.1 section pointing at this spec | User answered explicitly. |
| Spec location | Inside the fork at `docs/superpowers/specs/` | Ties design to code; commits with the change set. |

## 10 · Open questions / risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| ReSukiSU commit `e8f607a2` produces version ≠ 35003 | Medium | Gate 2 fails closed. Adjust to newer/older commit ±few and retry. |
| SUSFS v2.2 Kconfig option renamed or removed | Low | Gate 4 fails closed. Adjust the 17-flag list to match. |
| `SUS_SU=y` re-enabled by huangdihd upstream fragment | Low | Gate 4 negative grep fails closed. Add explicit `=n` to config JSON if needed. |
| SUSFS v2.2 kernel ABI breaks R27 userspace module ioctl | Low-medium | Detected at post-flash step 8.3; module can be upgraded independently. |
| AnyKernel3 `wild/sm8475` HEAD introduces a bug in flash-time init | Low | Fallback to existing pin `ea531d03…` (known-good). |
| Bootloader on slot B refuses new kernel signature | Very low (bootloader is unlocked) | Instant rollback via `fastboot --set-active=a`. |
| Banking apps break with new kernel string leaking somewhere SUSFS doesn't cover | Low | Post-flash verification includes non-root `uname -r` check. |

## 11 · Success criteria

The design is done when:
- Workflow `build-op11r-minimal.yml` runs green on GH Actions with the v2.2.0-r4 pins.
- Artifact zip lands on the user's phone, SHA256 verified.
- METHOD Step 5 flash flow completes; slot B boots.
- `dmesg` shows `susfs is initialized! version: v2.2.0` and `KernelSU version 35003`.
- Non-root `uname -r` still returns the stock string (SUSFS spoof works).
- All 8 userspace modules remain active.
- `su -c id` returns `uid=0(root) ... context=u:r:ksu:s0`.
- User can flash back to r26 huangdihd or stock at will.
