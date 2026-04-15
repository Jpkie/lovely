import sys

content = open(
    r"D:\项目\LovelyERes-main\src\modules\ui\createFolderModal.ts",
    "r",
    encoding="utf-8",
).read()
lines = content.split("\n")

# Fix all garbled comment lines that have code on the same line
# Format: '    // [garbled]    [actual code]'
# Strategy: replace the entire line with: comment only (no code), or fix comment + separate line for code
# Since these are all in method bodies, we need to be careful about structure

# Lines with garbled comments followed by code on same line (0-indexed):
# 230: update parent directory display + code
# 235: reset input box + code
# 241: reset state + code (but validateInput() and hideError() are separate calls!)
# 266: check if empty + code (this is OK, keep as is)
# 270: check filename invalid chars + code (this is OK)
# 274: error message + code (this is OK)
# 277: check starts/ends with dot + code (this is OK)
# 280: error message + code (this is OK)
# 283: check length + code (this is OK)
# 285: error message + code (this is OK)
# 288: update full path preview + code (this is OK)
# 297: update button state + code (this is OK)
# 300: show or hide error message + code (this is OK)

# For lines 230, 235, 241 - the code AFTER the garbled comment needs to be on its own line
fixes = {}

for i, line in enumerate(lines):
    # Check if line has '//' followed by garbled text and then code (not just '//' and newline)
    # Look for lines where there's code AFTER what should be a comment
    if "    // " in line:
        # Split at '//'
        parts = line.split("    // ", 1)
        if len(parts) == 2:
            before_comment = parts[0]  # leading whitespace
            comment_and_code = parts[1]
            # Check if there's code after the comment (i.e., not just a comment ending with newline-like content)
            # We detect this by checking if after a reasonable comment length, there's TypeScript code pattern
            if (
                "{" in comment_and_code
                or "const " in comment_and_code
                or "nameInput" in comment_and_code
                or "validateInput" in comment_and_code
                or "hideError" in comment_and_code
            ):
                # This line has comment + code merged
                # Find where the actual code starts (after the garbled comment text)
                # The pattern is: garbled_text    code
                # We need to extract the code portion
                code_start = None
                for pattern in [
                    "const parentDirEl",
                    "const nameInput",
                    "this.validateInput",
                    "this.hideError",
                ]:
                    if pattern in comment_and_code:
                        idx = comment_and_code.find(pattern)
                        # Get just the comment text (everything before the code)
                        comment_text = comment_and_code[:idx].strip()
                        code_text = comment_and_code[idx:]
                        fixes[i] = before_comment + "// " + comment_text
                        # We need to INSERT a new line with the code
                        # This is complex - for now, let's just replace with comment only and handle code separately
                        break

print(f"Found {len(fixes)} lines to fix")

# For a simpler approach: just replace garbled comments with clean ASCII ones
# and ensure the code after is valid
clean_fixes = {
    229: "",  # line 230: empty (was '// update parent dir display')
    230: "    const parentDirEl = document.getElementById('create-folder-parent-dir');",  # was merged
    234: "",  # line 235: empty (was '// reset input box')
    235: "    const nameInput = document.getElementById('create-folder-name') as HTMLInputElement;",  # was merged
    240: "",  # line 241: empty (was '// reset state')
    # line 241: validateInput() is separate
    # line 242: hideError() is separate
}

# Actually let me look at the specific problematic lines more carefully
for i in [229, 230, 234, 235, 240, 241]:
    print(f"Line {i + 1}: {repr(lines[i])[:120]}")

print()
print("Context around line 241:")
for i in range(239, 245):
    print(f"Line {i + 1}: {repr(lines[i])[:120]}")
