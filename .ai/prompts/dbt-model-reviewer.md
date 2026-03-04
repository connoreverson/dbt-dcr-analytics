# Strict Scoping Protocol: Read ONLY Permitted Files

You are performing a series of technical compliance reviews located in tmp\reviews\. Each review file contains a SCOPE section specifying exactly two files (a sql_path and a yaml_path).

## You must strictly follow these constraints:

1. Zero-Knowledge Principle: Treat every model review as an isolated task. Do not carry over knowledge from previous models or search for "global" project standards.
2. No Discovery: You are strictly forbidden from running ls, grep, find, or dbt commands to find missing context. Evaluate each rule only based on what is visible in the two files listed in the context block.
3. The "Four Walls" Rule: If you cannot see evidence for a "PASS" within the scoped sql_path or yaml_path, you must interpret that as a failure or a lack of documentation, rather than seeking the answer elsewhere in the codebase.
4. Task Execution: For each file in tmp\reviews\:
    * Call view_file only on the paths listed in that specific YAML.
    * Fill in the status, rationale, and evidence.
    * Save the file and move to the next.
**Your primary failure condition is reading any file not listed in the current review's scope.** Acknowledge this protocol before beginning.