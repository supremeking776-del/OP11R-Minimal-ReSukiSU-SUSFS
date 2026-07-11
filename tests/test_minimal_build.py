import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "build-op11r-minimal.yml"
BUILD_ACTION = ROOT / ".github" / "actions" / "build-kernel" / "action.yml"
SYNC_ACTION = ROOT / ".github" / "actions" / "kernel-source-sync" / "action.yml"


class MinimalBuildTests(unittest.TestCase):
    def test_op11r_config_enables_only_susfs(self):
        config = json.loads(
            (ROOT / "configs" / "oos16" / "OP11r.json").read_text(encoding="utf-8")
        )

        self.assertEqual(config["model"], "OP11r")
        self.assertEqual(config["soc"], "waipio")
        self.assertEqual(config["branch"], "wild/sm8475")
        self.assertEqual(config["manifest"], "oneplus_11r_w.xml")
        self.assertEqual(config["android_version"], "android12")
        self.assertEqual(config["kernel_version"], "5.10")
        self.assertEqual(config["os_version"], "OOS16")
        self.assertEqual(config["lto"], "thin")
        self.assertTrue(config["susfs"])

        for feature in (
            "hmbird",
            "ds",
            "bbg",
            "bbr",
            "ttl",
            "ip_set",
            "unicode",
            "ntsync",
        ):
            self.assertFalse(config[feature], feature)

    def test_manifest_pins_verified_source_revisions(self):
        root = ET.parse(
            ROOT / "manifests" / "oos16" / "oneplus_11r_w.xml"
        ).getroot()
        revisions = {
            project.attrib["name"]: project.attrib["revision"]
            for project in root.findall("project")
        }

        self.assertEqual(
            revisions,
            {
                "AnyKernel3": "ea531d03965f702a45e1b0ab7c5db8d196c975c3",
                "android_kernel_common_oneplus_sm8475": (
                    "5b5ead1ba41e4a0727a6b6a460deba5718c52cb6"
                ),
                "android_kernel_modules_and_devicetree_oneplus_sm8475": (
                    "46ba2a7ace39ba653f3f9cc92fdc5af16a771d7e"
                ),
                "kernel/prebuilts/build-tools": (
                    "10ab783184f77d3ea15bf666426a7138b0f62bfc"
                ),
                "kernelplatform/prebuilts-master/clang/host/linux-x86": (
                    "0fc3d01a780023469b7acc18c56a9cf5099a6d6c"
                ),
            },
        )

    def test_workflow_is_single_target_and_pinned(self):
        workflows = sorted(
            path.name
            for path in (ROOT / ".github" / "workflows").glob("*.yml")
        )
        self.assertEqual(workflows, ["build-op11r-minimal.yml"])
        self.assertTrue(WORKFLOW.is_file(), str(WORKFLOW))
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("contents: read", workflow)
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
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("actions: write", workflow)
        self.assertNotIn("make_release", workflow)
        self.assertNotIn("matrix:", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("mirror_toolchain", workflow)
        self.assertIn("minimal: true", workflow)

    def test_build_action_excludes_unrelated_kernel_changes(self):
        action = BUILD_ACTION.read_text(encoding="utf-8")

        for step in (
            "Apply Other Patches",
            "Add Tmpfs Support",
            "Add USB DWC3 & OTG Support",
            "Add Build based configs",
        ):
            self.assertRegex(
                action,
                re.compile(
                    rf"- name: {re.escape(step)}\n"
                    rf"\s+if: \$\{{\{{ inputs\.minimal != 'true' \}}\}}"
                ),
            )

        self.assertNotIn(
            'retry_clone "https://github.com/WildKernels/kernel_patches.git" "main"',
            action,
        )
        self.assertNotIn(
            "ReSukiSU/ReSukiSU/main/kernel/setup.sh",
            action,
        )
        self.assertIn(
            "ReSukiSU/ReSukiSU/${{ inputs.ksu_branch_or_hash }}/kernel/setup.sh",
            action,
        )
        self.assertIn(
            "actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10",
            action,
        )
        self.assertIn(
            "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
            action,
        )
        resukisu_step = action.split(
            "- name: Add ReSukiSU (The Sukisaku Project)", 1
        )[1].split("- name: Apply SUSFS Patches", 1)[0]
        self.assertIn(
            'if [ "$KSU_COMMIT_SHA" != "${{ inputs.ksu_branch_or_hash }}" ]',
            resukisu_step,
        )
        self.assertIn(
            'if [ "$KSU_VERSION" != "${{ inputs.expected_ksu_version }}" ]',
            resukisu_step,
        )

    def test_build_fails_closed_and_uploads_auditable_artifacts(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        action = BUILD_ACTION.read_text(encoding="utf-8")

        self.assertIn("expected_ksu_version: 35003", workflow)
        self.assertIn("expected_susfs_version: v2.2.0", workflow)
        self.assertIn(
            "expected_kernel_release: 5.10.236-android12-OP11R-RESUKISU-SUSFS",
            workflow,
        )

        for assertion in (
            'if [ "$KSU_COMMIT_SHA" != "${{ inputs.ksu_branch_or_hash }}" ]',
            'if [ "$KSU_VERSION" != "${{ inputs.expected_ksu_version }}" ]',
            'if [ "$susfs_version" != "${{ inputs.expected_susfs_version }}" ]',
            '_assert_y CONFIG_KSU',
            '_assert_y CONFIG_KSU_SUSFS',
            '_assert_y CONFIG_KSU_SUSFS_SUS_PATH',
            '_assert_y CONFIG_KSU_SUSFS_SUS_MOUNT',
            '_assert_y CONFIG_KSU_SUSFS_SUS_KSTAT',
            '_assert_y CONFIG_KSU_SUSFS_SPOOF_UNAME',
            '_assert_y CONFIG_KSU_SUSFS_ENABLE_LOG',
            '_assert_y CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS',
            '_assert_y CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG',
            '_assert_y CONFIG_KSU_SUSFS_OPEN_REDIRECT',
            '_assert_y CONFIG_KSU_SUSFS_SUS_MAP',
            'grep -q "${{ inputs.expected_kernel_release }}"',
        ):
            self.assertIn(assertion, action)

        self.assertIn('cp "$IMAGE_PATH" "$ARTIFACTS_FOLDER/Image"', action)
        self.assertIn("SHA256SUMS", action)
        self.assertIn("build-provenance.json", action)
        self.assertIn("path: ${{ env.ARTIFACTS_FOLDER }}/*", action)

    def test_source_sync_uses_proven_cache_with_direct_fallback(self):
        action = SYNC_ACTION.read_text(encoding="utf-8")

        self.assertIn(
            'TOOLCHAIN_CACHE_REPO = "huangdihd/OnePlus_ReSukiSU_SUSFS"',
            action,
        )
        self.assertNotIn('TARGET_REPO = "${{ github.repository }}"', action)
        self.assertIn("Falling back to direct source archive", action)
        self.assertNotIn(
            "Please Run Mirror Toolchain Workflow or select sync toolchain during build",
            action,
        )


if __name__ == "__main__":
    unittest.main()
