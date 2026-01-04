# Language Analyzer Suite - AI Coding Instructions

## Project Overview
This project is a custom Language Analyzer Suite implemented in Python, consisting of a Lexical Analyzer (using `ply.lex`) and a hand-written LL(1) Syntactic Analyzer (Parser). It dynamically loads grammar definitions to parse source code.

## Key Files & Architecture
- **`lex.py`**: The core implementation file. Contains:
  - **Lexer**: Defines tokens and regex rules using `ply.lex`.
  - **Parser**: Implements a stack-based LL(1) parser.
  - **Symbol Table**: Manages scopes and symbol registration (`add_symbol`, `enter_scope`).
  - **Grammar Loader**: Parses `Gramatica.txt` to build the parsing table at runtime.
- **`Gramatica.txt`**: Defines the language grammar (Terminals, NonTerminals, Axiom, Productions).
- **`Esquema_de_traduccion.txt`**: Documentation for the translation scheme.
- **`makefile`**: Simple build script for cleaning output files.

## Workflows

### Running the Analyzer
To analyze a source program, run `lex.py` with the target file:
```bash
python lex.py <source_file>
# Example:
python lex.py programa_myjs.txt
```

### Cleaning Outputs
To remove generated files (`lexed.txt`, `symbols.txt`, `parse.txt`):
```bash
make clean
# Or manually: rm lexed.txt symbols.txt parse.txt
```

## Output Files
The analyzer generates three key output files in the working directory:
1. **`lexed.txt`**: Sequence of tokens identified by the lexer (format: `<TOKEN_TYPE, VALUE>`).
2. **`symbols.txt`**: The symbol table entries (lexemes and attributes).
3. **`parse.txt`**: The sequence of production rule numbers applied during parsing (Top-Down).

## Development Conventions

### Grammar Definition (`Gramatica.txt`)
- **Format**: Custom format with sections `Terminales = { ... }`, `NoTerminales = { ... }`, `Axioma = ...`, `Producciones = { ... }`.
- **Modifications**: Changes to the language syntax should be made here first, then ensure `lex.py` handles the corresponding tokens.

### Lexer (`lex.py`)
- **Tokens**: Defined in the `tokens` list and `reserved` dictionary.
- **Naming**: Token names are uppercase (e.g., `PLUSEQ`, `ID`, `INTCONST`).
- **Regex**: Rules are defined as `t_TOKENNAME` variables or functions.

### Parser (`lex.py`)
- **Logic**: Uses a `stack` and `parsing_table`.
- **Table Generation**: The `build_parsing_table` function computes FIRST and FOLLOW sets dynamically from the loaded grammar.
- **Error Handling**: Prints syntactic errors to stdout.

### Symbol Table
- **Implementation**: Uses a global `symbol_table_stack` to handle scopes.
- **Writing**: `add_symbol` writes directly to `symbols.txt` when a new identifier is encountered.

## Dependencies
- **`ply`**: Python Lex-Yacc (used primarily for the Lexer).
