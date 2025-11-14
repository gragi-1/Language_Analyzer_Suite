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
        t.value = add_symbol(name, t.type, t.value)
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
tok_gcounter = -1

symbol_table = {}
symbol_table_stack = [{}]

def add_symbol(name, type=None, value=None):
    global tok_gcounter
    if name not in symbol_table_stack[-1]:
        tok_gcounter += 1
        symbol_table_stack[-1][name] = {
            'type': type,
            'value': value,
            'position': tok_gcounter
        }
        return tok_gcounter
    else:
        return symbol_table_stack[-1][name]['position']

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

######    SECCIÓN DE ANALIZADOR SINTÁCTICO    ######

######    FIN SECCIÓN DE ANALIZADOR SINTÁCTICO    ######

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

if __name__ == "__main__":
    main()
