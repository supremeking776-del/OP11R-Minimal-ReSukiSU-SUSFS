# OP11R /proc/version Banner Spoof - Kernel-Level Fix

**Status**: Approved for implementation
**Date**: 2026-07-12
**Target repo**: `github.com/supremeking776-del/OP11R-Minimal-ReSukiSU-SUSFS`
**Branch**: `spoof-proc-version` (off `op11r-minimal-susfs`)
**Depends on**: `2026-07-11-op11r-minimal-resukisu-susfs-v2-2-0-design.md`

---

## 1 - Problem

SUSFS v2.2.0's runtime `OPEN_REDIRECT` for `/proc/version` fails to spoof the banner for banking apps on OP11R. Concrete evidence gathered on device (2026-07-12) proves:

1. The SUSFS module's userspace R27 registers `add_open_redirect /proc/version /data/adb/susfs4ksu/fake_proc_version` with `uid_scheme=2` at boot. `dmesg` confirms `CMD_SUSFS_ADD_OPEN_REDIRECT -> ret: 0`.
2. `uid_scheme=2` ("non-su processes") NEVER fires in the kernel's `susfs_open_redirect_spoof_do_sys_openat` for shell UID 2000 or app UID 10373. Only `uid_scheme=0` (uid<10000) was observed to fire in extensive testing.
3. Even when the redirect DOES fire, the target file `/data/adb/susfs4ksu/fake_proc_version` is at a chmod-700 root-only path. SUSFS opens the redirect target with the CALLER's credentials, so shell/app hits EACCES on directory traversal. The kernel silently falls through to opening the real `/proc/version`, and the caller reads the leaked custom banner (`Linux version 5.10.236-android12-OP11R-RESUKISU-SUSFS ...`).
4. YesPayNext (`com.yesbank.yespaynext`) reads `/proc/version`, sees `OP11R-RESUKISU-SUSFS`, and self-exits via `System.exit(0)` within 8 seconds of launch.

Fixing the userspace-level SUSFS redirect requires (a) placing the fake file in an app-readable path and (b) working around a `uid_scheme` bug that is not reachable from userspace. Both are fragile and namespace-sensitive (KSU umount, Zygote isolation).

## 2 - Solution

Overwrite the C-source-level output of `/proc/version` at kernel build time. The kernel binary itself will emit the stock banner unconditionally for every reader in every mount namespace, without any SUSFS ioctl involvement.

### 2.1 - Mechanism

`fs/proc/version.c` implements one function that reads `linux_banner` (the compile-time-baked global banner) and writes it to a seq_file:

```c
static int version_proc_show(struct seq_file *m, void *v)
{
    seq_printf(m, linux_banner);
    return 0;
}
```

We inject a static const array holding the stock banner and swap the write source:

```c
static const char op_spoofed_linux_banner[] =
    "Linux version 5.10.236-android12-9-o-g2bee83b9e1eb "
    "(build-user@build-host) (Android (7284624, based on r416183b) clang version 12.0.5 "
    "...) #1 SMP PREEMPT Mon May 11 02:04:22 UTC 2026\n";

static int version_proc_show(struct seq_file *m, void *v)
{
    seq_puts(m, op_spoofed_linux_banner);
    return 0;
}
```

`linux_banner` is left untouched. `uname()` and `uname -r` continue to be handled by SUSFS's `spoof_uname=2` runtime spoof (which works for uid<AID_APP already; verified). Only `/proc/version` is affected by this patch.

### 2.2 - Why not overwrite `linux_banner` directly?

`linux_banner` is in `.rodata`. Modifying it at boot requires page permission changes (unlock, write, relock), or a compile-time redefinition through `LINUX_COMPILE_BY`/`LINUX_COMPILE_HOST`/`UTS_VERSION`. The compile-time route can't reproduce the exact stock string because `UTS_RELEASE` embeds the (custom) localversion `OP11R-RESUKISU-SUSFS`. Adding a second static array and only swapping the `/proc/version` reader is the smallest, safest change with the largest coverage.

### 2.3 - What this does NOT cover

- `uname()` / `uname -r` -- handled by SUSFS `spoof_uname=2` at runtime.
- `/sys/kernel/version` -- absent on Android; not a leak vector.
- `dmesg` output of `linux_banner` at very early boot -- readable only to root/dmesg-privileged UIDs; banking apps don't have this.
- Kernel modules that stringify `UTS_RELEASE` at compile time -- affects niche vendor daemons, not the /proc/version path banks read.

## 3 - Config-driven design

The banner string is per-device (each stock kernel has a unique banner). We keep it in `configs/oos16/OP11r.json` as a new field:

```json
{
  ...existing fields...,
  "spoof_proc_version_banner": "Linux version 5.10.236-android12-9-o-g2bee83b9e1eb ... UTC 2026"
}
```

If the field is empty or absent, the build step is a no-op and the kernel behaves exactly as before. This preserves the fork's minimal, config-gated design.

## 4 - File-level changes

Four files. Each change is small.

### 4.1 - `configs/oos16/OP11r.json`
Add `spoof_proc_version_banner` string field with the stock OP11R OOS 16.0.5.700 banner captured from device (`/data/adb/susfs4ksu/fake_proc_version`, MD5 `b0f8d2875a145f0db9eb73611e632b80`).

### 4.2 - `.github/actions/build-kernel/action.yml`
Add a new step `Spoof /proc/version banner` immediately after `Apply SUSFS Patches`, guarded by `env.OP_SPOOF_PROC_VERSION_BANNER != ''`. The step runs a Python heredoc that:
1. Reads `$COMMON_KERNEL_FOLDER/fs/proc/version.c`.
2. Verifies the anchor `static int version_proc_show(struct seq_file *m, void *v)` and marker `seq_printf(m, linux_banner);` are present. Fails closed if not.
3. C-escapes the banner string.
4. Inserts a `static const char op_spoofed_linux_banner[] = "...";` declaration above `version_proc_show`.
5. Replaces `seq_printf(m, linux_banner);` with `seq_puts(m, op_spoofed_linux_banner);`.
6. Prints a full diff for audit.

The subsequent Image-verification step is amended to:
- Grep `linux_banner` explicitly by requiring `expected_kernel_release` to appear in the matched line (previously `tail -n1`, which is now ambiguous because two `Linux version ...` strings coexist in `Image`).
- Fail closed if the spoofed banner substring is NOT found in `strings Image`.

### 4.3 - `tests/test_minimal_build.py`
Two additions:
- `test_op11r_config_enables_only_susfs` gains banner presence + content assertions (starts with `Linux version`, contains stock release token, does NOT contain `OP11R-RESUKISU-SUSFS`, includes SMP tail).
- New `test_build_action_spoofs_proc_version_banner` asserts the workflow contains the spoof step, the seq_puts replacement, the Image-embedding check, and the disambiguated linux_banner grep.

### 4.4 - `docs/superpowers/specs/2026-07-12-op11r-proc-version-banner-spoof.md`
This file.

## 5 - Fail-closed gates

The existing 6-gate strict CI (see 2026-07-11 design doc) grows by two gates:

7. **Spoof step succeeded** -- Python heredoc exits 0, meaning `fs/proc/version.c` had both the anchor and the marker and was patched.
8. **Spoofed banner embedded in Image** -- `strings Image | grep -qF "$OP_SPOOF_PROC_VERSION_BANNER"` returns match. If this fails, the seq_puts was inlined out or the compiler dropped the static, and we don't want an artifact.

Existing gate 5 (uname string) is tightened to grep for the release token INSIDE the line (not just the last line matching `Linux version.*#`).

## 6 - Post-flash verification

On the device after flashing the new AK3 zip:

```bash
# Every UID gets the stock banner:
adb shell "su -c 'cat /proc/version'"     # stock
adb shell 'cat /proc/version'              # stock
adb shell "su 10373 -c 'cat /proc/version'" # stock

# uname still spoofs via SUSFS (unchanged):
adb shell 'uname -r'                       # 5.10.236-android12-9-o-g2bee83b9e1eb

# YesPayNext launches and stays alive (no more System.exit(0) at 8s):
adb shell 'am start -n com.yesbank.yespaynext/...'
sleep 30
adb shell 'pidof com.yesbank.yespaynext'   # non-empty
```

Rollback path unchanged (see METHOD_OP11R.md Step 5 rollback options).

## 7 - Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| `fs/proc/version.c` upstream refactor changes anchor/marker | Very low (5.10 stable) | Python step fails closed with the full source dumped to log. |
| Compiler drops unused static | Very low (declared `const` used by seq_puts) | Gate 8 (embed-in-Image grep) fails closed. |
| Banking app also checks `linux_banner` via a different path | Low | We do not disturb `linux_banner`; only /proc/version reader changes. If some path leaks it, we discover post-flash and address separately. |
| Kernel modules linked at build time embed the wrong banner | Very low | Modules use `UTS_RELEASE`, not `linux_banner`; unaffected. |
| Config JSON `spoof_proc_version_banner` diverges from real stock banner | Low (single-source, from device) | Test asserts stock release token + absence of custom identifier. Post-flash `md5sum /proc/version` compared against captured device file. |

## 8 - Success criteria

- CI green on `spoof-proc-version` branch with new gates 7 and 8 passing.
- Artifact zip flashes successfully on slot B (magiskboot flow unchanged).
- `md5sum /proc/version` on device equals `b0f8d2875a145f0db9eb73611e632b80` (matches captured stock banner) from root, shell, AND app UID.
- YesPayNext launches to its login screen and stays alive past 30s without self-exit.
- No SUSFS OPEN_REDIRECT ioctl needed for /proc/version anymore (module.d overhead reduced by 1 entry, cosmetic).
