import sys

content = open(
    r"D:\项目\LovelyERes-main\src\modules\ui\createFolderModal.ts",
    "r",
    encoding="utf-8",
).read()
lines = content.split("\n")

# Fix strategy: identify lines where '//' in UTF-8 byte sequence is interpreted as comment start
# These appear as lines with garbled text followed by '    const' or '    this.'
# We split them into two lines: comment line + code line

fixed_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # Detect merged line: '    // [chars that include 0x2F 0x2F bytes]    [code]'
    # We detect this by checking if after '//' there are ≥2 consecutive chars that aren't whitespace
    # followed by more whitespace and then what looks like code
    if "    // " in line:
        # Split at the FIRST '    // ' (4 spaces + comment marker)
        parts = line.split("    // ", 1)
        indent = parts[0]  # leading whitespace
        rest = parts[1] if len(parts) > 1 else ""

        # Check if 'rest' contains code-like patterns after garbled text
        code_indicators = [
            "const ",
            "this.",
            "if (",
            "document.",
            "nameInput",
            "parentDir",
            "validateInput",
        ]
        code_start_idx = -1
        for indicator in code_indicators:
            idx = rest.find(indicator)
            if idx != -1 and idx > 3:  # found after some garbled text
                if code_start_idx == -1 or idx < code_start_idx:
                    code_start_idx = idx

        if code_start_idx > 3:
            # This is a merged line - split into comment + code
            comment_text = rest[:code_start_idx].rstrip()
            code_text = rest[code_start_idx:]
            fixed_lines.append(indent + "// " + comment_text)
            fixed_lines.append(indent + code_text)
            i += 1
            continue

    fixed_lines.append(line)
    i += 1

new_content = "\n".join(fixed_lines)
open(
    r"D:\项目\LovelyERes-main\src\modules\ui\createFolderModal.ts",
    "w",
    encoding="utf-8",
).write(new_content)

# Verify
content2 = open(
    r"D:\项目\LovelyERes-main\src\modules\ui\createFolderModal.ts",
    "r",
    encoding="utf-8",
).read()
lines2 = content2.split("\n")
print(f"Total lines: {len(lines2)}")

# Check the previously problematic area
for idx in [229, 230, 231, 234, 235, 236, 239, 240, 241, 242]:
    if idx < len(lines2):
        sys.stdout.buffer.write(
            f"{idx + 1}: {repr(lines2[idx])[:100]}\n".encode("utf-8")
        )
print("Done!")
