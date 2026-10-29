from pathlib import Path

folder_path = Path("/mnt/nvme0n1/database/storage/sluPolicy/readReady")

# Gather file names, replace underscores with spaces, and enforce exact phrase quotes
file_names = []
for file in folder_path.iterdir():
    if file.is_file():
        clean_name = file.stem.replace("_", " ")
        # Force strict exact-match quotes on EVERYTHING to bypass Google's semantic assumptions
        file_names.append(f'-"{clean_name}"')

# Prioritize SELU and Louisiana specific keywords/domains
# We target the specific university site AND require the keyword "louisiana" for broader results
base_target = '(site:southeastern.edu OR "louisiana") filetype:pdf'

# Keep chunk size to 10 to stay safely under Google's word limit
CHUNK_SIZE = 10
exclusion_chunks = [file_names[i:i + CHUNK_SIZE] for i in range(0, len(file_names), CHUNK_SIZE)]

print(f"\nFound {len(file_names)} files. Generating Louisiana/SELU prioritized commands:")

for index, chunk in enumerate(exclusion_chunks, 1):
    # Join exclusions space-separated: -"file one" -"file two" -"file three"
    exclusion_query = " ".join(chunk)

    if exclusion_query:
        formatted_string = f"{base_target} {exclusion_query}"
    else:
        formatted_string = base_target

    print(f"\n--- Batch {index} ---")
    print(f"Your search here! {formatted_string}")
