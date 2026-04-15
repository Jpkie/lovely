content = open(
    r"D:\项目\LovelyERes-main\src\modules\ui\createFolderModal.ts",
    "r",
    encoding="utf-8",
).read()
lines = content.split("\n")
# Fix lines 210-214: restore proper ESC handler
lines[209] = "    // ESC key to close listener"
lines[210] = "    document.addEventListener('keydown', (e) => {"
lines[211] = "      if (e.key === 'Escape' && this.isVisible) {"
lines[212] = "        this.hide();"
lines[213] = "      }"
lines[214] = "    });"
new_content = "\n".join(lines)
open(
    r"D:\项目\LovelyERes-main\src\modules\ui\createFolderModal.ts",
    "w",
    encoding="utf-8",
).write(new_content)
print("Fixed ESC handler block")
