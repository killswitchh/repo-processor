import os
import argparse
import pathspec
import logging
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('repo_processor.log')
    ]
)
logger = logging.getLogger(__name__)

# Files and directories to always ignore by default
DEFAULT_IGNORE_PATTERNS = ['.git']

def load_gitignore_patterns(repo_path):
    """Loads .gitignore patterns from the repository path."""
    gitignore_file = Path(repo_path) / '.gitignore'
    patterns = list(DEFAULT_IGNORE_PATTERNS) # Start with default ignores
    if gitignore_file.is_file():
        with open(gitignore_file, 'r', encoding='utf-8') as f:
            patterns.extend(f.read().splitlines())
    return patterns

def get_path_specs(repo_path, patterns):
    """Creates pathspec object from patterns."""
    # Pathspec needs paths relative to the .gitignore file (repo_path)
    # and it matches against paths relative to that root.
    spec = pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, patterns)
    return spec

def generate_file_tree(repo_path, spec, output_file_path_abs):
    """Generates a file tree string, ignoring specified patterns."""
    tree_lines = []
    files_to_read = []
    repo_path_obj = Path(repo_path).resolve()
    output_file_path_abs = Path(output_file_path_abs).resolve()
    
    # Initialize counters
    processed_files = 0
    ignored_files = 0
    processed_dirs = 0
    ignored_dirs = 0
    binary_files = 0
    error_files = 0

    for root, dirs, files in os.walk(repo_path_obj, topdown=True):
        current_path_obj = Path(root)
        # Path relative to the repository root for matching against pathspec
        relative_to_repo_root = current_path_obj.relative_to(repo_path_obj)

        # Filter directories: remove ignored ones from dirs to prevent os.walk from traversing them
        original_dirs_copy = list(dirs)
        filtered_dirs = []
        for d in original_dirs_copy:
            # Create path relative to repo root
            dir_path = relative_to_repo_root / d
            # Convert to string with forward slashes for pathspec matching
            dir_path_str = str(dir_path).replace(os.sep, '/')
            # Check both the directory path and the directory name pattern
            if (spec.match_file(dir_path_str) or 
                spec.match_file(f"{dir_path_str}/") or 
                spec.match_file(d)):
                logger.debug(f"Ignoring directory: {dir_path}")
                ignored_dirs += 1
            else:
                filtered_dirs.append(d)
        dirs[:] = filtered_dirs

        # Process current directory if it's not ignored
        if not spec.match_file(str(relative_to_repo_root.as_posix())) or str(relative_to_repo_root) == '.':
            level = len(current_path_obj.relative_to(repo_path_obj).parts)
            indent = '    ' * level
            if str(relative_to_repo_root) != '.': # Don't add root dir name itself to tree, walk starts inside it
                tree_lines.append(f"{indent}├── {current_path_obj.name}/")
            
            sub_indent = '    ' * (level + 1)
            for f_name in files:
                file_path_obj = current_path_obj / f_name
                relative_file_path_to_repo = file_path_obj.relative_to(repo_path_obj)
                
                # Skip the output file itself
                if file_path_obj == output_file_path_abs:
                    logger.debug(f"Skipping output file: {file_path_obj}")
                    continue

                # Convert to string with forward slashes for pathspec matching
                file_path_str = str(relative_file_path_to_repo).replace(os.sep, '/')
                # Check both full path and filename patterns
                if spec.match_file(file_path_str) or spec.match_file(f_name):
                    logger.debug(f"Ignoring file (gitignore match): {file_path_obj}")
                    ignored_files += 1
                    continue

                tree_lines.append(f"{sub_indent}├── {f_name}")
                # Check if file is likely text-based before adding to read list
                try:
                    with open(file_path_obj, 'r', encoding='utf-8') as temp_f:
                        temp_f.read(1024)  # Try reading a bit
                    files_to_read.append(str(file_path_obj))  # Store absolute path
                    processed_files += 1
                    logger.info(f"Processing file: {file_path_obj}")
                except UnicodeDecodeError:
                    binary_files += 1
                    tree_lines.append(f"{sub_indent}│   (Skipping binary file: {f_name})")
                    logger.debug(f"Skipping binary file: {file_path_obj}")
                except Exception as e:
                    error_files += 1
                    tree_lines.append(f"{sub_indent}│   (Error reading file {f_name}: {e})")
                    logger.error(f"Error reading file {file_path_obj}: {e}")
        
        processed_dirs += 1
        if processed_dirs % 100 == 0:  # Log progress every 100 directories
            logger.info(f"Processed {processed_dirs} directories so far...")
    
    # Log summary
    logger.info("\n=== Processing Summary ===")
    logger.info(f"Processed directories: {processed_dirs}")
    logger.info(f"Ignored directories: {ignored_dirs}")
    logger.info(f"Processed files: {processed_files}")
    logger.info(f"Ignored files (gitignore): {ignored_files}")
    logger.info(f"Binary files skipped: {binary_files}")
    logger.info(f"Files with read errors: {error_files}")
    
    return "\n".join(tree_lines), files_to_read

def main():
    parser = argparse.ArgumentParser(description='Process a repository and create a combined text file.')
    parser.add_argument('repo_path', type=str, help='Path to the repository to process.')
    parser.add_argument('--output_file', type=str, default='repository_snapshot.txt', 
                       help='Name of the output .txt file.')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Enable verbose logging (shows debug messages)')
    args = parser.parse_args()
    
    # Set log level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    else:
        logger.setLevel(logging.INFO)

    repo_path = Path(args.repo_path).resolve()
    output_file_path = repo_path / args.output_file # Place output in the root of the processed repo
    output_file_path_abs = output_file_path.resolve()

    if not repo_path.is_dir():
        print(f"Error: Repository path '{repo_path}' not found or is not a directory.")
        return

    start_time = datetime.now()
    logger.info(f"Starting repository processing at {start_time}")
    logger.info(f"Repository path: {repo_path}")
    logger.info(f"Output file: {output_file_path_abs}")
    print(f"Processing repository: {repo_path}")
    print(f"Output will be saved to: {output_file_path_abs}")
    print(f"Detailed logs are being written to: {os.path.abspath('repo_processor.log')}")

    gitignore_patterns = load_gitignore_patterns(str(repo_path))
    spec = get_path_specs(str(repo_path), gitignore_patterns)

    tree_structure, files_to_read = generate_file_tree(str(repo_path), spec, str(output_file_path_abs))

    with open(output_file_path_abs, 'w', encoding='utf-8') as outfile:
        outfile.write(f"File Tree for: {repo_path.name}\n")
        outfile.write("=====================================\n")
        outfile.write(tree_structure)
        outfile.write("\n\n=====================================\n")
        outfile.write("Concatenated File Contents\n")
        outfile.write("=====================================\n\n")

        for file_path_str in files_to_read:
            file_path_obj = Path(file_path_str)
            relative_path_to_repo = file_path_obj.relative_to(repo_path)
            try:
                with open(file_path_obj, 'r', encoding='utf-8') as infile:
                    content = infile.read()
                    outfile.write(f"--- Content of {relative_path_to_repo} ---\n")
                    outfile.write(content)
                    outfile.write("\n\n--- End of {relative_path_to_repo} ---\n\n")
            except Exception as e:
                outfile.write(f"--- Error reading {relative_path_to_repo}: {e} ---\n\n")

    end_time = datetime.now()
    duration = end_time - start_time
    logger.info(f"\n=== Processing completed in {duration} ===")
    logger.info(f"Output file: {output_file_path_abs}")
    logger.info(f"Log file: {os.path.abspath('repo_processor.log')}")
    print(f"\nProcessing completed in {duration}")
    print(f"Successfully created '{output_file_path_abs}'")
    print(f"Detailed logs available at: {os.path.abspath('repo_processor.log')}")

if __name__ == '__main__':
    main()
