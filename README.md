# Repository Processor

A Python utility for processing and analyzing repository contents while respecting `.gitignore` rules.

## Features

- Recursively processes repository files
- Respects `.gitignore` patterns
- Creates a combined text file with file tree and contents
- Handles binary files appropriately
- Detailed logging of processed and ignored files
- Progress tracking and summary statistics

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/repo-processor.git
   cd repo-processor
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Basic usage:
```bash
python repo_processor.py /path/to/repository
```

### Options

- `--output_file FILENAME`: Specify output filename (default: `repository_snapshot.txt`)
- `--verbose`: Enable detailed logging output

Example with options:
```bash
python repo_processor.py /path/to/repository --output_file my_output.txt --verbose
```

## Output

The script generates two files:
1. `repository_snapshot.txt` (or specified output filename): Contains the file tree and contents
2. `repo_processor.log`: Contains detailed logs of the processing

## Logging

Logs are written to both console and `repo_processor.log`. Use the `--verbose` flag for debug-level logging.

## Requirements

- Python 3.7+
- `pathspec` package

## License

MIT
