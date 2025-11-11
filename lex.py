import ply.lex as lex
import ply.yacc as yacc
import argparse

######    SECCIÓN DE ANALIZADOR LÉXICO    ######
noattr = [
        "PLUSEQ",
        "EQ",
        "COMMA",
        "SEMICOLON",
        "OPPAR",
        "CLPAR",
        "OPBRA",
        "CLBRA",
        "SUM",
        "AND",
        "MINORTHAN",
        "EOF"
        ]

reserved = {
        "boolean":  "BOOLEAN",
        "else":     "ELSE",
        "float":    "FLOAT",
        "function": "FUNCTION",
        "if":       "IF",
        "int":      "INT",
        "let":      "LET",
        "read":     "READ",
        "return":   "RETURN",
        "string":   "STRING",
        "void":     "VOID",
        "write":    "WRITE",
        "false":    "FALSE",
        "true":     "TRUE"
        }

# Grammar-specific reserved words used by the parser
reserved.update({
    "terminales": "PETERMINALES",
    "noterminales": "PENO_TERMINALES",
    "axioma": "PEAXIOMA",
    "producciones": "PEPRODUCCIONES",
    "lambda": "SIMBLAMBDA",
})

tokens = [
        "REALCONST", "INTCONST", "STR", "ID",
        ] + noattr + list(reserved.values())

t_PLUSEQ     = r'\+='
t_EQ         = r'='
t_COMMA      = r','
t_SEMICOLON  = r';'
t_OPPAR      = r'\('
t_CLPAR      = r'\)'
t_OPBRA      = r'\{'
t_CLBRA      = r'\}'
t_SUM        = r'\+'
t_AND        = r'&&'
t_MINORTHAN  = r'<'

t_ignore = ' \t'

#TODO: revisar el comportamiento cuando nos encontramos un token invalido: se genera o no? Se devuelve none o un código?

def t_REALCONST(t):
    r'-?\d+\.\d+'
    try:
        t.value = float(t.value)
    except ValueError:
        print("Real number value error: ", t.value)
    
    if t.value > 117549436.0:
        print(f"Real fuera de rango {t.value!r} en línea {t.lineno}")
        return None
    return t

def t_INTCONST(t):
    r'\d+'
    try:
        t.value = int(t.value)
    except ValueError:
        print("Integer number value error:", t.value)

    if t.value > 32767:
        print(f"Entero fuera de rango {t.value!r} en línea {t.lineno}")
        return None
    return t

def t_STR(t):
    r'\'([^\\\n]|(\\.))*?\''
    try:
        #TODO: revisar que realmente queremos que "'hola'" sea "hola"
        t.value = t.value[1:-1]
    except ValueError:
        print("String value error: ", t.value)

    if len(t.value) > 64:
        print(f"Cadena demasiado larga {t.value!r} en línea {t.lineno}")
        return None
    return t

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    lower = t.value.lower()
    if lower in reserved:
        t.type = reserved[lower]
        t.value = ''
    else:
        t.type = "ID"
        name = t.value
        t.value = tok_gcounter

        add_symbol(name, t.type, t.value)
    return t

def t_COMMENT(t):
    r'//.*'
    pass

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    print(f"Carácter ilegal {t.value[0]!r} en línea {t.lineno}")
    t.lexer.skip(1)

def t_eof(t):
    return None

lexer = lex.lex()

######    FIN SECCIÓN DE ANALIZADOR LÉXICO    ######


######    SECCIÓN DE TABLA DE SÍMBOLOS    ######
tok_gcounter = 0

symbol_table = {}
symbol_table_stack = [{}]

def add_symbol(name, type=None, value=None):
    global tok_gcounter
    if name not in symbol_table_stack:
        symbol_table_stack[-1][name] = {
            'type': type,
            'value': value,
        }
        tok_gcounter += 1

def get_symbol(name):
    for scope in reversed(symbol_table_stack):
        if name in scope:
            return scope[name]
    return None

def enter_scope():
    symbol_table_stack.append({})

def exit_scope():
    symbol_table_stack.pop()

######    FIN SECCIÓN DE TABLA DE SÍMBOLOS    ######

######    SECCIÓN DE ANALIZADOR SINTÁCTICO (MyJS - LL(1) friendly)    ######

# ------------------------------
# Símbolo inicial
# ------------------------------
def p_program(p):
    "program : function_list"
    pass

def p_function_list_rec(p):
    "function_list : function function_list"
    pass

def p_function_list_empty(p):
    "function_list : empty"
    pass

# ------------------------------
# Funciones
# function : FUNCTION ID ( parameters ) { declarations statements }
# ------------------------------
def p_function(p):
    "function : FUNCTION ID OPPAR parameters CLPAR OPBRA declarations statements CLBRA"
    pass

# parameters -> parameter_list | empty
def p_parameters_list(p):
    "parameters : parameter parameter_list_tail"
    pass

def p_parameters_empty(p):
    "parameters : empty"
    pass

def p_parameter(p):
    "parameter : type ID"
    pass

def p_parameter_list_tail_rec(p):
    "parameter_list_tail : COMMA parameter parameter_list_tail"
    pass

def p_parameter_list_tail_empty(p):
    "parameter_list_tail : empty"
    pass

# ------------------------------
# Types (as tokens from lexer)
# ------------------------------
def p_type(p):
    """type : INT
            | FLOAT
            | BOOLEAN
            | STRING
            | VOID"""
    pass

# ------------------------------
# Declarations: accepts 'let id[,id]*;' and 'type id[,id]*;'
# ------------------------------
def p_declarations_rec(p):
    "declarations : declaration declarations"
    pass

def p_declarations_empty(p):
    "declarations : empty"
    pass

def p_declaration_let(p):
    "declaration : LET id_list SEMICOLON"
    pass

def p_declaration_type(p):
    "declaration : type id_list SEMICOLON"
    pass

def p_id_list_rec(p):
    "id_list : ID COMMA id_list"
    pass

def p_id_list_single(p):
    "id_list : ID"
    pass

# ------------------------------
# Statements (LL(1) entry tokens distinguished)
# statement can start with: LET, type, ID, WRITE, READ, RETURN, OPBRA, IF
# ------------------------------
def p_statements_rec(p):
    "statements : statement statements"
    pass

def p_statements_empty(p):
    "statements : empty"
    pass

def p_statement_let_or_type(p):
    # handled via declaration syntax above, but allow in statements sequence
    "statement : LET id_list SEMICOLON"
    pass

def p_statement_type_decl(p):
    "statement : type id_list SEMICOLON"
    pass

# ID starts either an assignment or a call (disambiguated by lookahead token: EQ or OPPAR)
def p_statement_id(p):
    "statement : ID statement_suffix"
    pass

def p_statement_suffix_assign(p):
    "statement_suffix : EQ expression SEMICOLON"
    pass

def p_statement_suffix_call(p):
    "statement_suffix : OPPAR arg_list CLPAR SEMICOLON"
    pass

# write, read, return, block, if-else
def p_statement_write(p):
    "statement : WRITE OPPAR expression CLPAR SEMICOLON"
    pass

def p_statement_read(p):
    "statement : READ OPPAR ID CLPAR SEMICOLON"
    pass

def p_statement_return(p):
    "statement : RETURN expression SEMICOLON"
    pass

def p_statement_block(p):
    "statement : OPBRA statements CLBRA"
    pass

def p_statement_if(p):
    "statement : IF OPPAR expression CLPAR statement else_opt"
    pass

def p_else_opt(p):
    "else_opt : ELSE statement"
    pass

def p_else_opt_empty(p):
    "else_opt : empty"
    pass

# ------------------------------
# Expressions — rewritten to remove left recursion (LL(1) friendly)
#
# expression -> term exprp
# exprp -> ('+' | '&&' | '<') term exprp | empty
# term -> factor
# factor -> ID | INTCONST | REALCONST | STR | TRUE | FALSE | ID(args) | ( expression )
# ------------------------------
def p_expression(p):
    "expression : term exprp"
    pass

def p_exprp_binop(p):
    """exprp : SUM term exprp
             | AND term exprp
             | MINORTHAN term exprp"""
    pass

def p_exprp_empty(p):
    "exprp : empty"
    pass

def p_term(p):
    "term : factor"
    pass

def p_factor_id(p):
    "factor : ID"
    pass

def p_factor_id_call(p):
    "factor : ID OPPAR arg_list CLPAR"
    pass

def p_arg_list_multi(p):
    "arg_list : expression COMMA arg_list"
    pass

def p_arg_list_single(p):
    "arg_list : expression"
    pass

def p_arg_list_empty(p):
    "arg_list : empty"
    pass

def p_factor_intconst(p):
    "factor : INTCONST"
    pass

def p_factor_realconst(p):
    "factor : REALCONST"
    pass

def p_factor_str(p):
    "factor : STR"
    pass

def p_factor_bool(p):
    """factor : TRUE
              | FALSE"""
    pass

def p_factor_paren(p):
    "factor : OPPAR expression CLPAR"
    pass

# ------------------------------
# Empty production
# ------------------------------
def p_empty(p):
    "empty :"
    pass

# ------------------------------
# Error handler
# ------------------------------
def p_error(p):
    if p:
        print(f"Error sintáctico en token {p.type!r} con valor {p.value!r} en línea {getattr(p, 'lineno', '?')}")
        # No recovery by default for table-driven; just report
    else:
        print("Error sintáctico: fin de fichero inesperado")

# Build parser (start symbol 'program')
parser = yacc.yacc(start='program', optimize=False)
######    FIN SECCIÓN DE ANALIZADOR SINTÁCTICO (MyJS - LL(1) friendly)    ######

def main():
    tok_counter = 0

    parser = argparse.ArgumentParser()
    parser.add_argument("file") #args.file es el "puntero" a la file
    args = parser.parse_args()

    with open(args.file, 'r') as f:
        content = f.read()

    lexer.input(content)

    with open('lexed.txt', 'w', encoding="utf-8") as f:
        for tok in lexer:
            if tok.type in noattr:
                f.write(f'<{tok.type},>\n')
            elif tok.type == 'STR':
                f.write(f'<{tok.type},\"{tok.value}\">\n')
            else:
                f.write(f'<{tok.type},{tok.value}>\n')
        f.write(f'<EOF,>')

    with open('symbols.txt', 'w', encoding='utf-8') as f_sym:
        for i, scope in enumerate(symbol_table_stack):
            f_sym.write(f"CONTENIDOS DE LA TABLA # {i+1}:\n")  # sumamos 1 aquí
            for j, (name, info) in enumerate(scope.items()):
                f_sym.write(f"* LEXEMA : '{name}'\n")
                f_sym.write("  Atributos:\n")
                f_sym.write("--------- ---------\n") # Además, hay que escribir cosas distintas si es variable o función
            f_sym.write("\n")

    sintactico(args.file)

def sintactico(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        data = f.read()
    lexer.input(data)
    parser.parse(data, lexer=lexer)

if __name__ == "__main__":
    main()
