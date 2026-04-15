content = open(
    r"D:\项目\LovelyERes-main\src\modules\ui\createFolderModal.ts",
    "r",
    encoding="utf-8",
).read()
lines = content.split("\n")

# Map of line indices (0-based) to their correct content
# Only lines that are broken will be replaced
fixes = {
    209: "",  # empty line
    210: "    // ESC key to close listener",
    211: "    document.addEventListener('keydown', (e) => {",
    212: "      if (e.key === 'Escape' && this.isVisible) {",
    213: "        this.hide();",
    214: "      }",
    215: "    });",
    216: "    // Click outside modal to close",
    265: "    // Check if empty",
    266: "    if (!folderName) {",
    269: "    } else {",
    276: "      ",  # blank line
    282: "      ",  # blank line
    286: "      ",  # blank line
    295: "    }",
    297: "    // Update button state",
    300: "    // Show or hide error message",
}

for idx, replacement in fixes.items():
    if idx < len(lines):
        lines[idx] = replacement

new_content = "\n".join(lines)
open(
    r"D:\项目\LovelyERes-main\src\modules\ui\createFolderModal.ts",
    "w",
    encoding="utf-8",
).write(new_content)
print(f"Fixed {len(fixes)} lines")
print("Done!")
