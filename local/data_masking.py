
import re
import random


# This script is used for masking data from a DML files 


def generate_random_16_digits():
    return ''.join([str(random.randint(0,9)) for _ in range(16)])

def split_values(group):
    """
    Split the values in a tuple, considering commas within quotes and escaped quotes.
    """
    # Updated regex to handle SQL-style escaped single quotes and other complex scenarios
    pattern = re.compile(r"""
        \s*                                     # Optional whitespace
        (
            '(?:''|[^'])*'                      # Single quoted string with escaped single quotes
            |"(?:\\"|[^"])*"                    # Double quoted string with escaped double quotes
            |[^,()]+                            # Unquoted value (no commas or parentheses)
        )
        \s*
        (?:,|$)                                 # Separator comma or end of string
    """, re.VERBOSE)
    
    values = []
    for match in pattern.finditer(group):
        value = match.group(1).strip()
        if value:
            # Remove surrounding quotes if present
            if value.startswith("'") and value.endswith("'"):
                # Replace doubled single quotes with a single quote and remove extra quotes
                value = value[1:-1].replace("''", "'")
            elif value.startswith('"') and value.endswith('"'):
                # Replace escaped double quotes with a single double quote
                value = value[1:-1].replace('\\"', '"')
        else:
            value = ''
        values.append(value)
    return values

def clean_value(value):
    """
    Clean and properly quote a value, handling escaped quotes and extra quote marks
    """
    if value.lower() == 'null':
        return value
    
    # Remove surrounding quotes if they exist
    if (value.startswith("'") and value.endswith("'")) or \
       (value.startswith('"') and value.endswith('"')):
        value = value[1:-1]
    
    # Remove any extra single quotes in the middle of the string
    # This handles cases like HE'R*****
    value = value.replace("'", "")
    
    # Escape any remaining single quotes
    value = value.replace("'", "''")
    
    return f"'{value}'"

def mask_value(value, mask_char='*'):
    """
    Mask a value while preserving the first 3 characters
    """
    if value is None or len(value.strip()) == 0:
        return value
        
    value = value.strip()
    
    # If the value doesn't start with a quote, return as is
    if not value.startswith("'"):
        return value
        
    # Remove outer quotes
    inner_value = value[1:-1]
    
    if len(inner_value) <= 3:
        return value
    
    # Mask the value
    masked = inner_value[:3] + mask_char * 5
    
    # Return the masked value with single quotes
    return f"'{masked}'"

def process_insert_statement(statement):
    # Updated regex to handle parentheses inside quoted strings
    insert_regex = re.compile(
        r"^(INSERT\s+INTO\s+[^()]+\s*\([^()]+\))\s+VALUES\s*(.+);?$",
        re.IGNORECASE | re.DOTALL
    )
    
    match = insert_regex.match(statement)
    if not match:
        return statement
    
    header = match.group(1)
    values_part = match.group(2)
    
    # Updated regex to match value groups while ignoring parentheses within quotes
    value_group_regex = re.compile(r"""
        \(
            (                           # Start capturing group
                (?:                     # Non-capturing group for content
                    [^()'"]+            # Non-parenthesis and non-quote characters
                    |'[^']*'            # Single-quoted strings
                    |"[^"]*"            # Double-quoted strings
                )*
            )
        \)
    """, re.VERBOSE | re.DOTALL)
    
    value_groups = value_group_regex.findall(values_part)
    
    if not value_groups:
        return statement  # Return original statement if no value groups are found
    
    new_values = []
    for group in value_groups:
        values = split_values(group)
        new_group_values = []
        
        for i, value in enumerate(values):
            value = value.strip()
            
            if value.lower() == 'null':
                new_group_values.append('NULL')
                continue
            
            # Handle fields based on their index
            if i == 18:  # nomor_identitas
                new_value = f"'{generate_random_16_digits()}'"
            
            elif i == 0:  # npwp
                npwp = generate_random_16_digits()
                new_value = f"'{npwp[:15]}'"
        
            elif i in [1,10,22,24,25,52,53,72]:  # Fields to mask
                # First clean the value, then mask it
                cleaned_value = clean_value(value)
                masked = mask_value(cleaned_value)
                new_value = masked
            
            else:
                # For other fields, just ensure proper quoting
                new_value = clean_value(value)
            
            new_group_values.append(new_value)
           
        new_values.append(f"({','.join(new_group_values)})")
        
    new_sql = f"{header} VALUES\n" + ',\n'.join(new_values) + ';'
    return new_sql

def process_sql_file(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    insert_statements = re.findall(r"(INSERT INTO [^(]+\([^)]+\)\s+VALUES\s*\(.*?\);)", content, re.IGNORECASE | re.DOTALL)
    
    new_statements = []
    for stmt in insert_statements:
        processed_stmt = process_insert_statement(stmt)
        new_statements.append(processed_stmt)
    
    remaining_content = re.sub(r"(INSERT INTO [^(]+\([^)]+\)\s+VALUES\s*\(.*?\);)", "", content, flags=re.IGNORECASE | re.DOTALL).strip()
    if remaining_content:
        new_statements.append(remaining_content)
    
    new_sql = '\n'.join(new_statements)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(new_sql)

# Usage
input_file = 'individu.sql'
output_file = 'output.sql'
process_sql_file(input_file, output_file)