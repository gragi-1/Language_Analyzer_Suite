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
grammar = {}
parsing_table = {}
stack = []
input_tokens = []
token_pointer = 0
id_types = {}
production_sequence = []  # Para almacenar la secuencia de producciones aplicadas

def first_pass_analyze(tokens_list):
    global id_types
    i = 0
    while i < len(tokens_list):
        tok = tokens_list[i]
        
        if tok.type == 'FUNCTION' and i + 2 < len(tokens_list):
            if tokens_list[i+1].type in ['INT', 'FLOAT', 'STRING', 'BOOLEAN', 'VOID']:
                if tokens_list[i+2].type == 'ID':
                    func_id = tokens_list[i+2].value
                    id_types[func_id] = 'idfun'
                    i += 3
                    continue
        
        if tok.type == 'LET' and i + 2 < len(tokens_list):
            if tokens_list[i+1].type == 'INT' and tokens_list[i+2].type == 'ID':
                var_id = tokens_list[i+2].value
                id_types[var_id] = 'idint'
            elif tokens_list[i+1].type == 'FLOAT' and tokens_list[i+2].type == 'ID':
                var_id = tokens_list[i+2].value
                id_types[var_id] = 'idfl'
            elif tokens_list[i+1].type == 'BOOLEAN' and tokens_list[i+2].type == 'ID':
                var_id = tokens_list[i+2].value
                id_types[var_id] = 'idbool'
            elif tokens_list[i+1].type == 'STRING' and tokens_list[i+2].type == 'ID':
                var_id = tokens_list[i+2].value
                id_types[var_id] = 'idstr'
            i += 3
            continue
        
        if tok.type in ['INT', 'FLOAT', 'BOOLEAN', 'STRING'] and i + 1 < len(tokens_list):
            if tokens_list[i+1].type == 'ID':
                var_id = tokens_list[i+1].value
                if tok.type == 'INT':
                    id_types[var_id] = 'idint'
                elif tok.type == 'FLOAT':
                    id_types[var_id] = 'idfl'
                elif tok.type == 'BOOLEAN':
                    id_types[var_id] = 'idbool'
                elif tok.type == 'STRING':
                    id_types[var_id] = 'idstr'
        
        i += 1

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
    
    for nt in grammar['non_terminals']:
        parsing_table[nt] = {}
        for production in grammar['productions'].get(nt, []):
            first_of_production = set()
            
            if not production or production[0] == 'lambda':
                first_of_production.add('lambda')
            else:
                for symbol in production:
                    if symbol in grammar['terminals']:
                        first_of_production.add(symbol)
                        break
                    elif symbol in grammar['non_terminals']:
                        for f in first[symbol]:
                            if f != 'lambda':
                                first_of_production.add(f)
                        if 'lambda' not in first[symbol]:
                            break
                else:
                    first_of_production.add('lambda')
            
            for terminal in first_of_production:
                if terminal != 'lambda':
                    parsing_table[nt][terminal] = production
            
            if 'lambda' in first_of_production:
                for terminal in follow[nt]:
                    parsing_table[nt][terminal] = production

def token_type_to_grammar_symbol(token):
    mapping = {
        'BOOLEAN': 'boolean',
        'ELSE': 'else',
        'FLOAT': 'float',
        'FUNCTION': 'function',
        'IF': 'if',
        'INT': 'int',
        'LET': 'let',
        'READ': 'read',
        'RETURN': 'return',
        'STRING': 'string',
        'VOID': 'void',
        'WRITE': 'write',
        'FALSE': 'boolconst',
        'TRUE': 'boolconst',
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
        return id_types.get(token.value, 'idint')
    
    return token.type.lower()

def parse():
    global stack, token_pointer, production_sequence
    
    stack = ['eof', grammar['axiom']]
    token_pointer = 0
    production_sequence = []
    
    while stack:
        top = stack[-1]
        
        if token_pointer < len(input_tokens):
            current_token = input_tokens[token_pointer]
            current_symbol = token_type_to_grammar_symbol(current_token)
        else:
            current_symbol = 'eof'
        
        if top in grammar['terminals'] or top == 'eof':
            if top == current_symbol:
                stack.pop()
                token_pointer += 1
            else:
                print(f"Error: Se esperaba {top} pero se encontró {current_symbol}")
                return False
        elif top in grammar['non_terminals']:
            if current_symbol in parsing_table.get(top, {}):
                production = parsing_table[top][current_symbol]
                
                # Registrar la producción aplicada
                production_key = (top, tuple(production))
                if production_key in grammar['production_numbers']:
                    production_sequence.append(grammar['production_numbers'][production_key])
                else:
                    print(f"Advertencia: No se encontró número para la producción {production_key}")
                
                stack.pop()
                if production and production[0] != 'lambda':
                    for symbol in reversed(production):
                        stack.append(symbol)
            else:
                print(f"Error: No hay producción para [{top}, {current_symbol}]")
                return False
        else:
            print(f"Error: Símbolo desconocido {top}")
            return False
    
    if token_pointer >= len(input_tokens):
        print("Análisis completado exitosamente")
        return True
    else:
        print("Error: Quedan tokens sin procesar")
        return False

######    FIN SECCIÓN DE ANALIZADOR SINTÁCTICO    ######

def main():
    tok_counter = 0

    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    args = parser.parse_args()

    with open(args.file, 'r') as f:
        content = f.read()

    lexer.input(content)

    global input_tokens
    input_tokens = []

    for tok in lexer:
        input_tokens.append(tok)
    
    first_pass_analyze(input_tokens)

    with open('lexed.txt', 'w', encoding="utf-8") as f:
        for tok in input_tokens:
            if tok.type in noattr:
                f.write(f'<{tok.type},>\n')
            elif tok.type == 'STR':
                f.write(f'<{tok.type},\"{tok.value}\">\n')
            else:
                f.write(f'<{tok.type},{tok.value}>\n')
        f.write(f'<EOF,>')

    with open('symbols.txt', 'w', encoding='utf-8') as f_sym:
        for i, scope in enumerate(symbol_table_stack):
            f_sym.write(f"CONTENIDOS DE LA TABLA # {i+1}:\n")
            for j, (name, info) in enumerate(scope.items()):
                f_sym.write(f"* LEXEMA : '{name}'\n")
                f_sym.write("  Atributos:\n")
                f_sym.write("--------- ---------\n")
            f_sym.write("\n")
    
    load_grammar('GramaticaLL1.txt')
    build_parsing_table()
    
    if parse():
        # Generar el fichero de parse en el formato requerido
        with open('parse.txt', 'w') as f:
            f.write("Descendente ")
            for production_num in production_sequence:
                f.write(f"{production_num} ")
        print("Fichero parse.txt generado exitosamente")
    else:
        print("No se generó parse.txt debido a errores en el análisis")

if __name__ == "__main__":
    main()