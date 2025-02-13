import os
import logging

try:
    import chardet
except ImportError:
    raise ImportError("Please install the 'chardet' library using 'pip install chardet'")

try:
    from packaging.requirements import Requirement
except ImportError:
    raise ImportError("Please install the 'packaging' library using 'pip install packaging'")

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(handler)

def read_file_with_detected_encoding(file_path):
    """
    Reads a file by first detecting its encoding using chardet.
    Returns the file's content as a string.
    """
    with open(file_path, 'rb') as f:
        raw_data = f.read()

    detection = chardet.detect(raw_data)
    encoding = detection.get('encoding')
    confidence = detection.get('confidence')
    logger.info(f"Detected encoding for {file_path}: {encoding} (Confidence: {confidence})")

    if encoding is None:
        encoding = 'utf-8'

    try:
        return raw_data.decode(encoding)
    except Exception as e:
        logger.error(f"Error decoding {file_path} with encoding {encoding}: {e}")
        return None

def consolidate_requirements(root_dir):
    """
    Walks through the directory tree from root_dir, finds all 'requirements.txt' files (except in the root),
    detects their encoding, reads their contents, and writes everything to a single output file in the root.
    Also checks for multiple versions of the same package and raises a warning if found.
    """
    output_file = os.path.join(root_dir, 'requirements.txt')
    package_versions = {}  # Dictionary to store package names and a set of their version specifiers.
    consolidated_contents = []  # List to store contents from each file.

    # Walk through the directory tree starting from root_dir.
    for subdir, dirs, files in os.walk(root_dir):
        for file in files:
            if file == 'requirements.txt':
                # Skip the root requirements file.
                if os.path.abspath(subdir) == os.path.abspath(root_dir):
                    continue

                file_path = os.path.join(subdir, file)
                content = read_file_with_detected_encoding(file_path)
                if content is None:
                    logger.error(f"# Error: Could not decode file {file_path}.\n")
                    continue

                # Process each line to detect package version conflicts.
                for line in content.splitlines():
                    stripped_line = line.strip()
                    # Skip comments and empty lines.
                    if not stripped_line or stripped_line.startswith("#"):
                        continue
                    try:
                        # Parse the requirement using packaging.
                        req = Requirement(stripped_line)
                        pkg_name = req.name.lower()
                        # Convert the specifier to string; it will be empty if no version is specified.
                        version_spec = str(req.specifier)
                        if pkg_name not in package_versions:
                            package_versions[pkg_name] = set()
                        package_versions[pkg_name].add(version_spec)
                    except Exception as e:
                        logger.warning(f"Could not parse line '{line}' in {file_path}: {e}")

                # Append the content to the consolidated list.
                consolidated_contents.append(f"# Contents of {file_path}\n{content}\n")

    with open(output_file, 'w', encoding='utf-8') as outfile:
        for content in consolidated_contents:
            outfile.write(content)

    logger.info(f"All requirements.txt contents have been consolidated into {output_file}")

    # Check for version conflicts with the same package
    for pkg, versions in package_versions.items():
        non_empty_versions = {v for v in versions if v}
        if len(non_empty_versions) > 1:
            logger.warning(f"Multiple version specifications found for package '{pkg}': {non_empty_versions}")
        if "" in versions and len(versions) > 1:
            logger.warning(f"Package '{pkg}' is specified without a version in some files and with a version in others: {versions}")

if __name__ == "__main__":
    root_directory = os.getcwd()

    root_req_path = os.path.join(root_directory, 'requirements.txt')
    if os.path.exists(root_req_path):
        os.remove(root_req_path)

    consolidate_requirements(root_directory)
