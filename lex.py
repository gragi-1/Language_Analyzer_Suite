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
        "REALCONST", "INTCONST", "ID", "STR"
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
    r'//[^\n]*'
    pass

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# TODO: mejorar manejo de errores léxicos
def t_error(t):
    print(f"Carácter ilegal {t.value[0]!r} en línea {t.lineno}")
    t.lexer.skip(1)

def t_eof(t):
    return None

lexer = lex.lex(debug=True)

######    FIN SECCIÓN DE ANALIZADOR LÉXICO    ######

######    SECCIÓN DE TABLA DE SÍMBOLOS    ######
tok_gcounter = -1

symbol_table = {}
symbol_table_stack = [{}]

symbols_file = None  # Fichero para volcar la tabla de símbolos en tiempo real

def add_symbol(name, type=None, value=None):
    global tok_gcounter, symbols_file

    if name not in symbol_table_stack[-1]:
        tok_gcounter += 1
        symbol_table_stack[-1][name] = {
            'type': type,
            'value': value,
            'position': tok_gcounter
        }

        # ESCRIBIR EN symbols.txt EN EL MOMENTO (dinámicamente), con tu formato
        if symbols_file is not None:
            symbols_file.write(f"* LEXEMA : '{name}'\n")
            symbols_file.write("  Atributos:\n")
            symbols_file.write("  --------- ---------\n\n")

        return tok_gcounter
    else:
        return symbol_table_stack[-1][name]['position']

def get_symbol(value):
    for scope in reversed(symbol_table_stack):
        for tok in scope.values():
            if tok['position'] == value:
                return tok
    return None

def enter_scope():
    symbol_table_stack.append({})

def exit_scope():
    symbol_table_stack.pop()

######    FIN SECCIÓN DE TABLA DE SÍMBOLOS    ######

######    SECCIÓN DE ANALIZADOR SINTÁCTICO    ######
grammar = {}
parsing_table = {}
stack = []
production_sequence = []  # Para almacenar la secuencia de producciones aplicadas
current_token = None      # Token actual del lexer

def load_grammar(filename):
    global grammar
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    terminals = set()
    non_terminals = set()
    axiom = None
    productions = {}
    
    lines = content.split('\n')
    section = None
    in_productions = False
    
    # Para numerar las producciones
    production_counter = 1
    grammar['production_numbers'] = {}
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('////'):
            continue
        
        if 'Terminales' in line and '=' in line and 'NoTerminales' not in line:
            section = 'terminals'
            start = line.find('{')
            end = line.rfind('}')
            if start != -1 and end != -1:
                terms = line[start+1:end].strip().split()
                terminals.update(terms)
            continue
        
        if 'NoTerminales' in line and '=' in line:
            section = 'nonterminals'
            start = line.find('{')
            end = line.rfind('}')
            if start != -1 and end != -1:
                nonterms = line[start+1:end].strip().split()
                non_terminals.update(nonterms)
            continue
        
        if 'Axioma' in line and '=' in line and 'Producciones' not in line:
            section = 'axiom'
            parts = line.split('=')
            if len(parts) > 1:
                axiom = parts[1].strip()
            continue
        
        if 'Producciones' in line and '=' in line:
            section = 'productions'
            in_productions = True
            continue
        
        if section == 'productions' and in_productions:
            if '}' in line and '->' not in line:
                in_productions = False
                continue
            
            if '->' in line:
                line = line.replace('}', '').strip()
                parts = line.split('->')
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()
                    comment_pos = right.find('////')
                    if comment_pos != -1:
                        right = right[:comment_pos].strip()
                    right_symbols = right.split()
                    if left not in productions:
                        productions[left] = []
                    productions[left].append(right_symbols)
                    
                    # Asignar número a la producción
                    grammar['production_numbers'][(left, tuple(right_symbols))] = production_counter
                    production_counter += 1
    
    grammar['terminals'] = terminals
    grammar['non_terminals'] = non_terminals
    grammar['axiom'] = axiom
    grammar['productions'] = productions

def compute_first():
    first = {nt: set() for nt in grammar['non_terminals']}
    
    changed = True
    while changed:
        changed = False
        for nt in grammar['non_terminals']:
            for production in grammar['productions'].get(nt, []):
                if not production or production[0] == 'lambda':
                    if 'lambda' not in first[nt]:
                        first[nt].add('lambda')
                        changed = True
                else:
                    for symbol in production:
                        if symbol in grammar['terminals']:
                            if symbol not in first[nt]:
                                first[nt].add(symbol)
                                changed = True
                            break
                        elif symbol in grammar['non_terminals']:
                            for f in first[symbol]:
                                if f != 'lambda' and f not in first[nt]:
                                    first[nt].add(f)
                                    changed = True
                            if 'lambda' not in first[symbol]:
                                break
                        else:
                            break
                    else:
                        if 'lambda' not in first[nt]:
                            first[nt].add('lambda')
                            changed = True
    
    return first

def compute_follow(first):
    follow = {nt: set() for nt in grammar['non_terminals']}
    follow[grammar['axiom']].add('eof')
    
    changed = True
    while changed:
        changed = False
        for nt in grammar['non_terminals']:
            for production in grammar['productions'].get(nt, []):
                for i, symbol in enumerate(production):
                    if symbol in grammar['non_terminals']:
                        rest = production[i+1:]
                        if not rest:
                            for f in follow[nt]:
                                if f not in follow[symbol]:
                                    follow[symbol].add(f)
                                    changed = True
                        else:
                            all_nullable = True
                            for next_symbol in rest:
                                if next_symbol in grammar['terminals']:
                                    if next_symbol not in follow[symbol]:
                                        follow[symbol].add(next_symbol)
                                        changed = True
                                    all_nullable = False
                                    break
                                elif next_symbol in grammar['non_terminals']:
                                    for f in first[next_symbol]:
                                        if f != 'lambda' and f not in follow[symbol]:
                                            follow[symbol].add(f)
                                            changed = True
                                    if 'lambda' not in first[next_symbol]:
                                        all_nullable = False
                                        break
                            
                            if all_nullable:
                                for f in follow[nt]:
                                    if f not in follow[symbol]:
                                        follow[symbol].add(f)
                                        changed = True
    
    return follow

def build_parsing_table():
    global parsing_table
    
    first = compute_first()
    follow = compute_follow(first)
    
    parsing_table = {}
    
    print("Construyendo tabla de análisis sintáctico...")
    for nt in grammar['non_terminals']:
        parsing_table[nt] = {}
        print(f"Procesando no terminal: {nt}")
        for production in grammar['productions'].get(nt, []):
            first_of_production = set()
            
            print(f"  Producción: {nt} -> {' '.join(production) if production else 'lambda'}")
            if not production or production[0] == 'lambda':
                first_of_production.add('lambda')
            else:
                for symbol in production:
                    print(f"    Analizando símbolo: {symbol}")
                    if symbol in grammar['terminals']:
                        print(f"      Es terminal, añadiendo a FIRST de la producción: {symbol}")
                        first_of_production.add(symbol)
                        break
                    elif symbol in grammar['non_terminals']:
                        print(f"      Es no terminal, añadiendo FIRST({symbol}) a FIRST de la producción")
                        for f in first[symbol]:
                            print(f"        Añadiendo {f} a FIRST de la producción")
                            if f != 'lambda':
                                first_of_production.add(f)
                        if 'lambda' not in first[symbol]:
                            break
                    else:
                        print(f"    Todos los símbolos son anulables, añadiendo 'lambda' a FIRST de la producción")
                        first_of_production.add('lambda')
            
            for terminal in first_of_production:
                print(f"    Añadiendo a la tabla de análisis: M[{nt}, {terminal}] = {' '.join(production) if production else 'lambda'}")
                if terminal != 'lambda':
                    parsing_table[nt][terminal] = production
            
            if 'lambda' in first_of_production:
                for terminal in follow[nt]:
                    print(f"    Producción es anulable, añadiendo a la tabla de análisis: M[{nt}, {terminal}] = {' '.join(production) if production else 'lambda'}")
                    parsing_table[nt][terminal] = production

    print("Parsing Table:")
    for nt, rules in parsing_table.items():
        for term, prod in rules.items():
            print(f"M[{nt}, {term}] = {' '.join(prod)}")

def token_type_to_grammar_symbol(token):
    mapping = {
        'BOOLEAN': 'boolean',
        'STRING': 'string',
        'ELSE': 'else',
        'FLOAT': 'float',
        'FUNCTION': 'function',
        'IF': 'if',
        'INT': 'int',
        'LET': 'let',
        'READ': 'read',
        'RETURN': 'return',
        'VOID': 'void',
        'WRITE': 'write',
        'FALSE': 'false',
        'TRUE': 'true',
        'REALCONST': 'floatconst',
        'INTCONST': 'intconst',
        'STR': 'str',
        'PLUSEQ': 'pluseq',
        'EQ': 'eq',
        'COMMA': 'comma',
        'SEMICOLON': 'semicolon',
        'OPPAR': 'oppar',
        'CLPAR': 'clpar',
        'OPBRA': 'opbra',
        'CLBRA': 'clbra',
        'SUM': 'sum',
        'AND': 'and',
        'MINORTHAN': 'minorthan',
        'EOF': 'eof'
    }
    
    if token.type in mapping:
        return mapping[token.type]
    
    if token.type == 'ID':
        return 'id'
    
    return token.type.lower()

def handle_syntactic_error(no_terminal, terminal, token):
    global prev_token

    # Tratamiento de la línea donde se comete el error
    prev_lineno = getattr(prev_token, 'lineno', 1)

    line = token.lineno
    changed = False

    if token.lineno > prev_lineno:
        line = prev_lineno
        changed = True

    # Tratamiento del símbolo a mostrar
    token_info = get_symbol(token.value)

    if token_info is None:
        showID = terminal
    else:
        showID = token_info['value']

    # Mensajes de error específicos por no terminal
    print(f"\nMyJS Syntactic Error: en la línea {line}", end=' ')

    if no_terminal == 'S':
        print(f"se esperaba el inicio de una sentencia o función, pero se encontró '{showID}'")
    elif no_terminal == 'LC':
        print(f"se esperaba el inicio de una sentencia, pero se encontró '{showID}'")
    elif no_terminal == 'LF':
        print(f"se esperaba 'function', pero se encontró '{showID}'")
    elif no_terminal == 'CuerpoIf':
        print(f"se esperaba el inicio de una sentencia o un '{{', pero se encontró '{showID}'")
    elif no_terminal == 'Cuerpo':
        print(f"se esperaba el inicio de una sentencia o un '}}', pero se encontró '{showID}'")
    elif no_terminal == 'Args':
        print(f"se esperaba un tipo de dato o falta ')', se encontró '{showID}'")
    elif no_terminal == 'ArgsLlamada':
        print(f"hay un argumento no válido o falta ')', se encontró '{showID}'")
    elif no_terminal == 'ArgMoreLlamada':
        print(f"se esperaba ',' para llamar más argumentos o falta ')', se encontró '{showID}'")
    elif no_terminal == 'ArgMore':
        print(f"se esperaba ',' para llamar más argumentos o falta ')', se encontró '{showID}'")
    elif no_terminal == 'LS':
        print(f"se esperaba la llamada a una función o una declaración, pero se encontró '{showID}'")
    elif no_terminal == 'IdOpt':
        print(f"se esperaba '=' o una llamada de función, pero se encontró '{showID}'")
    elif no_terminal == 'TypeFun':
        print(f"se esperaba un tipo de función, pero se encontró '{showID}'")
    elif no_terminal == 'Tipo':
        print(f"se esperaba un tipo de dato, pero se encontró '{showID}'")
    elif no_terminal == 'Asignar':
        print(f"se esperaba '=' , pero se encontró '{showID}'")
    elif no_terminal == 'ExpReturn':
        if changed:
            print(f"se esperaba ';'")
        else:
            print(f"hay una expresión no válida después del return, se encontró '{showID}'")
    elif no_terminal == 'Expresion':
        print(f"hay una expresión mal declarada, se encontró '{showID}'")
    elif no_terminal == 'ExpresionAux':
        if changed:
            print(f"se esperaba ';'")
        else:
            print(f"se esperaba un operador, pero se encontró '{showID}'")
    elif no_terminal == 'Expresion1':
        print(f"hay una expresión mal declarada, se encontró '{showID}'")
    elif no_terminal == 'Expresion1Aux':
        if changed:
            print(f"se esperaba ';'")
        else:
            print(f"se esperaba un operador, pero se encontró '{showID}'")
    elif no_terminal == 'Expresion2':
        print(f"hay una expresión mal declarada, se encontró '{showID}'")
    elif no_terminal == 'Expresion2Aux':
        if changed:
            print(f"se esperaba ';'")
        else:
            print(f"se esperaba un operador, pero se encontró '{showID}'")
    elif no_terminal == 'Expresion3':
        print(f"hay una expresión no válida, se encontró '{showID}'")
    elif no_terminal == 'Expresion4':
        if changed:
            print(f"se esperaba ';'")
        else:
            print(f"hay una función mal llamada o falta ')', pero se encontró '{showID}'")

current_token = None
prev_token = None
lexed_file = None

def init_lexer_for_parser(code):
    global current_token, prev_token
    lexer.input(code)
    # Primer token: se escribe en lexed y luego se pasa al parser
    prev_token = current_token
    current_token = get_next_token()

def get_next_token():
    global lexed_file

    tok = lexer.token()
    if tok is None:
        class EOFToken:
            type = 'EOF'
            value = None
            lineno = 0
        tok = EOFToken()

    # ESCRIBIR EN lexed.txt
    if lexed_file is not None:
        if tok.type in noattr:
            lexed_file.write(f'<{tok.type},>\n')
        elif tok.type == 'STR':
            lexed_file.write(f'<{tok.type},\"{getattr(tok, "value", "")}\">\n')
        else:
            lexed_file.write(f'<{tok.type},{getattr(tok, "value", "")}>\n')

    # 2) DEVOLVER AL SINTÁCTICO
    return tok

def advance_token():
    global current_token, prev_token
    prev_token = current_token
    current_token = get_next_token()

def parse():
    global stack, production_sequence, current_token

    stack = ['eof', grammar['axiom']]
    production_sequence = []

    while stack:
        top = stack[-1]
        current_symbol = token_type_to_grammar_symbol(current_token)

        if top in grammar['terminals'] or top == 'eof':
            if top == current_symbol:
                stack.pop()
                advance_token()
            else:
                handle_syntactic_error(top, current_symbol, current_token)
                return False

        elif top in grammar['non_terminals']:
            rules_for_top = parsing_table.get(top, {})
            if current_symbol in rules_for_top:
                production = rules_for_top[current_symbol]
                production_key = (top, tuple(production))
                if production_key in grammar['production_numbers']:
                    production_sequence.append(grammar['production_numbers'][production_key])
                stack.pop()
                if production and production[0] != 'lambda':
                    for symbol in reversed(production):
                        stack.append(symbol)
            else:
                handle_syntactic_error(top, current_symbol, current_token)
                return False
        else:
            print(f"Error: Símbolo desconocido {top}")
            return False

    return token_type_to_grammar_symbol(current_token) == 'eof'

######    FIN SECCIÓN DE ANALIZADOR SINTÁCTICO    ######

def main():
    tok_counter = 0
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    args = parser.parse_args()

    with open(args.file, 'r') as f:
        content = f.read()

    global lexed_file, symbols_file

    # Abrimos AMBOS ficheros al inicio
    with open('lexed.txt', 'w', encoding="utf-8") as lf, \
         open('symbols.txt', 'w', encoding='utf-8') as sf:
        
        lexed_file = lf
        symbols_file = sf

        # Escribir cabecera en symbols.txt
        sf.write("CONTENIDOS DE LA TABLA:\n\n")

        load_grammar('Gramatica.txt')
        build_parsing_table()

        # Inicializamos lexer (ya escribe dinámicamente en lexed.txt y symbols.txt)
        init_lexer_for_parser(content)

        ok = parse()

    # Generar parse.txt
    if ok:
        with open('parse.txt', 'w') as f:
            f.write("Descendente ")
            for production_num in production_sequence:
                f.write(f"{production_num} ")
        print("Fichero parse.txt generado exitosamente")
    else:
        print("No se generó parse.txt debido a errores en el análisis")

if __name__ == "__main__":
    main()
