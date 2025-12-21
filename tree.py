import os
from pathlib import Path

# --- Configuration ---
# Set the desired directory here. 
# '.' means the current working directory where the script is run.
TARGET_DIR = Path('.') 

# Set the maximum depth to prevent excessively long outputs on large projects
MAX_DEPTH = 5

def print_tree(directory: Path, prefix: str = '', depth: int = 0):
    """Recursively prints the directory structure in a tree-like format."""
    
    # 1. Skip if depth limit reached
    if depth >= MAX_DEPTH:
        print(f"{prefix}├── ... (max depth reached)")
        return
        
    # 2. Collect all items (files and directories)
    # Filter out hidden files/folders (starting with '.')
    contents = [p for p in directory.iterdir() if not p.name.startswith('.')]
    
    # Sort: directories first, then files, both alphabetically
    contents.sort(key=lambda p: (p.is_file(), p.name))
    
    # 3. Iterate and print
    for index, path in enumerate(contents):
        # Determine if it's the last item in the list
        is_last = (index == len(contents) - 1)
        
        # Select the correct branch character
        pointer = '└── ' if is_last else '├── '
        
        print(f"{prefix}{pointer}{path.name}")
        
        # If it's a directory, recurse
        if path.is_dir():
            # Extend the prefix for the next level
            # Use a space filler for a vertical line ('|') or just spaces if it's the last item
            new_prefix = prefix + ('    ' if is_last else '│   ')
            
            # Recurse with the new prefix and increased depth
            print_tree(path, new_prefix, depth + 1)

if __name__ == "__main__":
    print(f"--- Directory Tree: {TARGET_DIR.resolve().name}/ (Max Depth: {MAX_DEPTH}) ---")
    
    # The initial call starts the process
    # Note: We skip the root directory itself in the loop to keep the output clean.
    print_tree(TARGET_DIR)
    print("----------------------------------------------------------")

# How to run:
# 1. Save the code as 'tree_printer.py'
# 2. Navigate to the root of your 'wingman-fastapi' project in your terminal.
# 3. Run: python tree_printer.py