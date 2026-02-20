import os

path = "orbiter/core/broker/executor.py"

try:
    with open(path, 'r') as f:
        content = f.read()

    # The line to fix
    bad_line = "            return {**future_details, 'dry_run': True, 'side': side, 'lot_size': lot}"
    good_line = "            return {**future_details, 'dry_run': True, 'side': side, 'lot_size': lot, 'ok': True}"

    if bad_line.strip() in content:
        # Simple string replacement might fail if indentation varies slightly
        # Let's try flexible replacement
        new_content = content.replace(bad_line.strip(), good_line.strip())
        
        # If that fails (due to indentation in bad_line string vs file), try line by line
        if new_content == content:
            lines = content.split('\n')
            new_lines = []
            fixed = False
            for line in lines:
                if "return {**future_details, 'dry_run': True, 'side': side, 'lot_size': lot}" in line and "'ok': True" not in line:
                    indent = line[:line.find('return')]
                    new_lines.append(indent + good_line.strip())
                    fixed = True
                else:
                    new_lines.append(line)
            new_content = '\n'.join(new_lines)
            
            if fixed:
                with open(path, 'w') as f:
                    f.write(new_content)
                print("✅ Fixed executor.py (Line replacement)")
            else:
                print("⚠️ Could not find the exact line to fix.")
        else:
            with open(path, 'w') as f:
                f.write(new_content)
            print("✅ Fixed executor.py (String replacement)")

    elif "'ok': True" in content and "future_details" in content:
        print("✅ Already fixed.")
    else:
        print("⚠️ Pattern not found. Dumping relevant section:")
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if "sim_order" in line:
                print(f"Line {i+1}: {line}")
                if i+1 < len(lines):
                    print(f"Line {i+2}: {lines[i+1]}")

except Exception as e:
    print(f"❌ Error: {e}")
