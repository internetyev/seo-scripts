import argparse
import csv
import re
import sys
import os
from tqdm import tqdm

# parse logical expression string into a structured format
# Input: "term1 AND term2 OR term3"
# Logic: Split by " OR " for top-level groups. Split by " AND " within groups.
# Returns: List of Lists of strings [ [term1, term2], [term3] ]
# Meaning: (term1 AND term2) OR (term3)
def parse_logic_string(expression):
    or_groups = expression.split(' OR ')
    parsed = []
    for group in or_groups:
        and_terms = [term.strip() for term in group.split(' AND ')]
        parsed.append(and_terms)
    return parsed

def check_conditions(text, rules, is_regex=False):
    # rules is a list of lists: [[t1, t2], [t3]]
    # We need ONE of the inner lists to FULLY match (OR logic at top level)
    
    # Re-implementing cleanly:
    for group in rules:
        # Check if ALL terms in this 'group' are found in 'text'
        if all(check_single_term(text, term, is_regex) for term in group):
            return True
    return False

def check_single_term(text, term, is_regex):
    if is_regex:
        return re.search(term, text) is not None
    else:
        return term in text

def main():
    parser = argparse.ArgumentParser(description='Filter CSV rows based on regex or string patterns.')
    parser.add_argument('input_file', help='Path to input CSV file')
    parser.add_argument('--regex', action='append', help='Regex pattern with optional comparison operators (e.g. "foo AND bar"). Can be used multiple times.')
    parser.add_argument('--string', action='append', help='String pattern with optional comparison operators (e.g. "foo AND bar"). Can be used multiple times.')
    parser.add_argument('--output', help='Path to output CSV file')
    parser.add_argument('--column', help='Specific column name to filter on. If not provided, searches entire row.')

    args = parser.parse_args()

    input_path = args.input_file
    if not os.path.exists(input_path):
        print(f"Error: File {input_path} not found.")
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_filtered{ext}"

    # Parse rules
    regex_rules = []
    if args.regex:
        for r in args.regex:
            regex_rules.extend(parse_logic_string(r))
    
    string_rules = []
    if args.string:
        for s in args.string:
            string_rules.extend(parse_logic_string(s))

    if not regex_rules and not string_rules:
        print("Warning: No filters provided. Copying entire file.")
    
    # Estimate total lines
    print("Counting lines for progress estimation...")
    total_lines = 0
    with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
        for _ in f:
            total_lines += 1
    
    print(f"Processing {input_path}...")
    
    with open(input_path, 'r', encoding='utf-8', errors='replace') as f_in, \
         open(output_path, 'w', encoding='utf-8', newline='') as f_out:
        
        reader = csv.reader(f_in)
        writer = csv.writer(f_out)
        
        try:
            header = next(reader)
            writer.writerow(header)
            total_lines -= 1 # Adjust for header
        except StopIteration:
            pass # Empty file

        # Validate column argument
        target_col_index = None
        if args.column:
            if args.column not in header:
                print(f"Error: Column '{args.column}' not found in CSV header: {header}")
                sys.exit(1)
            target_col_index = header.index(args.column)

        matched_count = 0
        
        # Wrap reader in tqdm
        for row in tqdm(reader, total=total_lines, unit='rows'):
            # Determine text to search
            if target_col_index is not None:
                # Safety check for ragged rows
                if target_col_index < len(row):
                    row_text = row[target_col_index]
                else:
                    row_text = "" # Column missing in this row
            else:
                row_text = " ".join(row)
            
            pass_regex = True
            if args.regex:
                for r_arg in args.regex:
                    parsed_arg = parse_logic_string(r_arg) 
                    if not check_conditions(row_text, parsed_arg, is_regex=True):
                        pass_regex = False
                        break
            
            pass_string = True
            if pass_regex and args.string:
                for s_arg in args.string:
                    parsed_arg = parse_logic_string(s_arg)
                    if not check_conditions(row_text, parsed_arg, is_regex=False):
                        pass_string = False
                        break
            
            if pass_regex and pass_string:
                writer.writerow(row)
                matched_count += 1
                
    print(f"\nDone. Filtered CSV saved to: {output_path}")
    print(f"Matches found: {matched_count}/{total_lines}")

if __name__ == "__main__":
    main()
