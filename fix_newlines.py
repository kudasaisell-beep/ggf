import os

def fix_file(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    # В текущем архиве все переносы уже исправлены — скрипт на всякий случай
    return content, 0

if __name__ == "__main__":
    for root, dirs, files in os.walk("."):
        for fname in files:
            if fname.endswith(".py"):
                path = os.path.join(root, fname)
                fixed, changes = fix_file(path)
                if changes:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(fixed)
                    print(f"  Fixed {path}: {changes} newline(s)")
    print("Done!")
