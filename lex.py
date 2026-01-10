import ply.lex as lex
import ply.yacc as yacc
import argparse
import sys

######    SECCIÓN DE ANALIZADOR LÉXICO    ######

# Errores léxicos acumulados: se registran durante el scan y se reportan al final.
lex_errors = []

def lex_error(lineno, msg):
    """Registra un error léxico."""
    lex_errors.append((lineno, msg))

def has_lex_errors():
    """Retorna True si hay errores léxicos."""
    return len(lex_errors) > 0

def print_lex_errors():
    """Imprime todos los errores léxicos acumulados."""
    for lineno, msg in lex_errors:
        print(f"MyJS Lex Error: (línea {lineno}): {msg}")

def clear_lex_errors():
    """Limpia la lista de errores léxicos."""
    global lex_errors
    lex_errors = []

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

        # Palabras reservadas "meta" (solo para poder tokenizar/leer la gramática con este lexer).
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
        lex_error(t.lineno, f"Valor de número real inválido: {t.value}")
        t.lexer.skip(len(str(t.value)))
        return None
    
    if t.value > 117549436.0:
        lex_error(t.lineno, f"Número real fuera de rango: {t.value}")
        return None
    return t

def t_INTCONST(t):
    r'\d+'
    try:
        t.value = int(t.value)
    except ValueError:
        lex_error(t.lineno, f"Valor de entero inválido: {t.value}")
        t.lexer.skip(len(str(t.value)))
        return None

    if t.value > 32767:
        lex_error(t.lineno, f"Entero fuera de rango (máx 32767): {t.value}")
        return None
    return t

def t_STR(t):
    r'\'([^\\\n]|(\\.))*?\''
    try:
        t.value = t.value[1:-1]  # Quitar comillas
    except ValueError:
        lex_error(t.lineno, f"Cadena mal formada: {t.value}")
        return None

    if len(t.value) > 64:
        lex_error(t.lineno, f"Cadena demasiado larga (máx 64 caracteres): '{t.value[:20]}...'")
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
        # El parser trabaja con id.pos: guardamos el lexema en la TS y propagamos su posición.
        t.value = add_symbol(name, t.type, t.value)
    return t

def t_COMMENT(t):
    r'//[^\n]*'
    pass

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    """Manejo de caracteres ilegales."""
    lex_error(t.lineno, f"Carácter ilegal: '{t.value[0]}'")
    t.lexer.skip(1)

def t_eof(t):
    return None

# Crear el lexer sin modo debug
lexer = lex.lex(debug=False)

######    FIN SECCIÓN DE ANALIZADOR LÉXICO    ######

######    SECCIÓN DE TABLA DE SÍMBOLOS    ######
tok_gcounter = -1

# Tabla de símbolos por scopes. Cada scope es un dict: lexema -> atributos.
# La posición (id.pos) es global e incremental, y se usa como "handle" entre fases.
symbol_table = {}
symbol_table_stack = [{}]

symbols_file = None  # Fichero para volcar la tabla de símbolos en tiempo real

def add_symbol(name, type=None, value=None):
    """Agrega o reutiliza un símbolo en la Tabla de Símbolos.
    
    Comportamiento:
    - Si el símbolo existe en cualquier scope visible → reutilizar su posición
    - Si no existe en ningún scope → crear nuevo en scope actual
    
    Esto asegura que las referencias a identificadores ya declarados
    (ej: llamadas a funciones) obtengan la misma posición que la declaración.
    """
    global tok_gcounter, symbols_file

    # Buscar en TODOS los scopes (de más interno a más externo)
    for scope in reversed(symbol_table_stack):
        if name in scope:
            return scope[name]['position']
    
    # No existe en ningún scope: crear nuevo
    tok_gcounter += 1
    symbol_table_stack[-1][name] = {
        'type': type,
        # 'value' aquí NO es un valor en tiempo de ejecución: es el lexema original.
        'value': value,
        'position': tok_gcounter,
        'displacement': None,  # Desplazamiento en memoria
        'lexeme': name         # Guardar el lexema para referencia
    }
    return tok_gcounter

def get_symbol(value):
    for scope in reversed(symbol_table_stack):
        for tok in scope.values():
            if tok['position'] == value:
                return tok
    return None

def get_symbol_by_name(name):
    """Busca un símbolo por nombre en todos los scopes."""
    for scope in reversed(symbol_table_stack):
        if name in scope:
            return scope[name]
    return None

def set_symbol_displacement(pos, disp):
    """Establece el desplazamiento de un símbolo."""
    sym = get_symbol(pos)
    if sym:
        sym['displacement'] = disp

def get_symbol_displacement(pos):
    """Obtiene el desplazamiento de un símbolo."""
    sym = get_symbol(pos)
    if sym:
        return sym.get('displacement')
    return None

def write_symbol_table_to_file(file_handle):
    """Escribe la tabla de símbolos completa al archivo."""
    file_handle.write("CONTENIDOS DE LA TABLA:\n\n")
    
    # Recopilar todos los símbolos de todos los scopes
    all_symbols = {}
    for scope in symbol_table_stack:
        for name, sym in scope.items():
            if sym['position'] not in all_symbols:
                all_symbols[sym['position']] = (name, sym)
    
    # Ordenar por posición y escribir
    for pos in sorted(all_symbols.keys()):
        name, sym = all_symbols[pos]
        file_handle.write(f"* LEXEMA : '{name}'\n")
        file_handle.write("  Atributos:\n")
        
        # Escribir tipo si existe
        if sym.get('type'):
            file_handle.write(f"    + tipo: '{sym['type']}'\n")
        
        # Escribir desplazamiento si existe
        if sym.get('displacement') is not None:
            file_handle.write(f"    + desplazamiento: {sym['displacement']}\n")
        
        file_handle.write("  --------- ---------\n\n")

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

###### SECCIÓN DE ANÁLISIS SEMÁNTICO ######

# Constantes de Tipos
T_INT = 'int'
T_FLOAT = 'float'
T_STRING = 'string'
T_BOOL = 'boolean'
T_VOID = 'void'
T_ERROR = 'tipo_error'
T_OK = 'tipo_ok'

# Estado Global del Semántico
sem_stack = []        
last_id_pos = -1      
current_func_id = -1  # ID de la función que se está declarando
despG = 0             
despL = 0             
in_function = False   
temp_type = None      
global_initialized = False  # Bandera para saber si ya se inicializó el scope global      

# Pila de IDs para expresiones (resuelve el problema de ids anidados en llamadas)
id_stack = []

# Pila de IDs para declaraciones let (preserva el id durante análisis de Asignar)
decl_id_stack = []

# Pila de IDs para LS -> id IdOpt (preserva el id durante análisis de IdOpt)
ls_id_stack = []      

def get_width(type_str):
    """Ancho (bytes) de un tipo para cálculo de desplazamientos (despG/despL).
    
    Per el EdT:
    - int: 2 bytes
    - float: 4 bytes  
    - boolean: 1 byte
    - string: 64 bytes (tamaño máximo permitido por el lexer)
    """
    if type_str == T_INT: return 2
    if type_str == T_FLOAT: return 4
    if type_str == T_BOOL: return 1
    if type_str == T_STRING: return 64  # Tamaño máximo de cadena en MyJS
    return 0

def set_symbol_type(pos, type_val):
    sym = get_symbol(pos)
    if sym:
        sym['type'] = type_val

def get_symbol_type(pos):
    sym = get_symbol(pos)
    if sym:
        return sym['type']
    return None

def get_symbol_name(pos):
    # Recupera el nombre real (lexema) para errores legibles
    sym = get_symbol(pos)
    if sym and 'value' in sym:
        return str(sym['value'])
    return f"ID_{pos}"

def sem_error(msg):
    print(f"MyJS Semantic Error: {msg}")

# --- ACCIONES SEMÁNTICAS ---

def action_init_global():
    """S -> LC S | LF S | eof: Inicialización del scope global.
    
    Per el EdT: if TSG = nulo then TSG := CrearTabla(), despG := 0
    Solo inicializa si no se ha hecho antes.
    """
    global despG, sem_stack, id_stack, decl_id_stack, global_initialized
    
    if not global_initialized:
        despG = 0
        sem_stack = []
        id_stack = []
        decl_id_stack = []
        global_initialized = True

def action_lc_check():
    ls_type = sem_stack.pop()
    res = T_OK if ls_type != T_ERROR else T_ERROR
    sem_stack.append(res)

def action_lc_if():
    # Pila: LE, CuerpoIf, Exp (se poppea en orden inverso a como se sintetiza)
    le_type = sem_stack.pop()
    cuerpo_type = sem_stack.pop()
    exp_type = sem_stack.pop()
    
    if exp_type == T_BOOL:
        if cuerpo_type == T_OK:
            sem_stack.append(le_type)
        else:
            sem_stack.append(T_ERROR)
    else:
        sem_error(f"La condición 'if' requiere boolean. Recibido: {exp_type}")
        sem_stack.append(T_ERROR)

def action_le_else():
    pass 

def action_le_lambda():
    sem_stack.append(T_OK)

def action_fun_init():
    global despL, in_function, current_func_id
    # last_id_pos es el identificador de la función
    current_func_id = last_id_pos 
    
    enter_scope()
    despL = 0
    in_function = True

def action_fun_def():
    # Registra la firma de la función en la Tabla de Símbolos
    args_type = sem_stack.pop()
    ret_type = sem_stack.pop()
    
    # Construir firma: args -> ret
    if args_type == T_VOID:
        sig = f"void -> {ret_type}"
    else:
        sig = f"{args_type} -> {ret_type}"
    
    # Actualizar símbolo (está en el scope padre/global)
    sym = get_symbol(current_func_id)
    if sym:
        sym['type'] = sig
    else:
        # Fallback por si acaso
        sem_error(f"No se pudo registrar la función {get_symbol_name(current_func_id)}")

def action_fun_end():
    global in_function
    exit_scope()
    in_function = False

def action_cuerpo_lc():
    c1 = sem_stack.pop()
    lc = sem_stack.pop()
    res = c1 if lc == T_OK else T_ERROR
    sem_stack.append(res)

def action_cuerpo_lambda():
    sem_stack.append(T_OK)

def action_args_init():
    global temp_type
    temp_type = sem_stack[-1] 

def action_args_id():
    """Args -> Tipo id ArgMore: Acción al procesar 'id' del parámetro.
    
    Per el EdT: AgregarTipo(id.pos, Tipo.tipo), AgregarDesplazamiento(id.pos, despL)
    """
    global despL
    tipo = sem_stack[-1] 
    set_symbol_type(last_id_pos, tipo)
    set_symbol_displacement(last_id_pos, despL)
    despL += get_width(tipo)

def action_args_res():
    am = sem_stack.pop()
    t = sem_stack.pop()
    if am == T_VOID:
        sem_stack.append(t)
    else:
        sem_stack.append(f"{t} x {am}")

def action_args_void():
    sem_stack.append(T_VOID)

def action_argsl_call():
    am = sem_stack.pop()
    e = sem_stack.pop()
    if e == T_ERROR or am == T_ERROR:
        sem_stack.append(T_ERROR)
    elif am == T_VOID:
        sem_stack.append(e)
    else:
        sem_stack.append(f"{e} x {am}")

def action_argsl_lambda():
    sem_stack.append(T_VOID)

def action_argmore_call():
    am1 = sem_stack.pop()
    e = sem_stack.pop()
    if e == T_ERROR or am1 == T_ERROR:
        sem_stack.append(T_ERROR)
    elif am1 == T_VOID:
        sem_stack.append(e)
    else:
        sem_stack.append(f"{e} x {am1}")

def action_argmore_lambda():
    sem_stack.append(T_VOID)

def action_argmore_tipo():
    global temp_type
    temp_type = sem_stack[-1]

def action_argmore_id():
    """ArgMore -> comma Tipo id ArgMore: Acción al procesar 'id' del parámetro adicional.
    
    Per el EdT: AgregarTipo(id.pos, Tipo.tipo), AgregarDesplazamiento(id.pos, despL)
    """
    global despL
    tipo = sem_stack[-1]
    set_symbol_type(last_id_pos, tipo)
    set_symbol_displacement(last_id_pos, despL)
    despL += get_width(tipo)

def action_argmore_res():
    am1 = sem_stack.pop()
    t = sem_stack.pop()
    if am1 == T_VOID:
        sem_stack.append(t)
    else:
        sem_stack.append(f"{t} x {am1}")

def action_ls_let_pre():
    pass 

def action_ls_let_id():
    """LS -> let Tipo id Asignar: Acción al procesar 'id'.
    
    Guarda el id en decl_id_stack para preservarlo durante el análisis de Asignar.
    Per el EdT: AgregarTipo(id.pos, Tipo.tipo), AgregarDesplazamiento(...)
    """
    global despG, despL, decl_id_stack
    tipo = sem_stack[-1] 
    set_symbol_type(last_id_pos, tipo)
    w = get_width(tipo)
    
    # Asignar desplazamiento según el scope
    if in_function:
        set_symbol_displacement(last_id_pos, despL)
        despL += w
    else:
        set_symbol_displacement(last_id_pos, despG)
        despG += w
    
    # Guardar el id para usarlo en action_ls_let_res
    decl_id_stack.append(last_id_pos)

def action_ls_let_res():
    """LS -> let Tipo id Asignar: Acción final (después de Asignar).
    
    Per el EdT:
    LS.tipo := if Asignar.igualacion = tipo_error then
                   if Asignar.tipo = Tipo.tipo then Tipo.tipo
                   else tipo_error
               else Tipo.tipo
    """
    global decl_id_stack
    asign = sem_stack.pop()
    tipo = sem_stack.pop()
    
    # Recuperar el id correcto de la pila
    if decl_id_stack:
        decl_id = decl_id_stack.pop()
    else:
        decl_id = last_id_pos  # Fallback
    name = get_symbol_name(decl_id)
    
    if asign == T_ERROR:
        sem_stack.append(T_ERROR)
    elif asign == T_VOID: 
        # Sin asignación (Asignar -> lambda)
        sem_stack.append(tipo)
    elif asign == tipo:
        sem_stack.append(tipo)
    elif tipo == T_FLOAT and asign == T_INT:
        # Coerción implícita int -> float
        sem_stack.append(tipo)
    else:
        sem_error(f"Asignación incorrecta en 'let {name}'. Esperado {tipo}, recibido {asign}")
        sem_stack.append(T_ERROR)

def action_ls_id_pre():
    """LS -> id IdOpt: Acción PRE al procesar 'id'.
    
    Per el EdT: Guardar id.pos para usarlo en IdOpt (que puede modificar last_id_pos).
    Si el id no existe en TS, se asigna tipo int por defecto (declaración implícita).
    """
    global despG, ls_id_stack
    
    # CRÍTICO: Guardar el id ANTES de que IdOpt lo sobrescriba con otros identificadores
    ls_id_stack.append(last_id_pos)
    
    sym_type = get_symbol_type(last_id_pos)
    if sym_type is None:
        # Declaración implícita de variable no declarada (comportamiento EdT)
        set_symbol_type(last_id_pos, T_INT)
        set_symbol_displacement(last_id_pos, despG)
        despG += 2

def action_ls_id_res():
    """LS -> id IdOpt: Acción final (después de IdOpt).
    
    Per el EdT: Recuperar el id original de ls_id_stack (no usar last_id_pos).
    """
    global ls_id_stack
    
    idopt = sem_stack.pop()
    
    # CRÍTICO: Recuperar el id correcto de la pila (NO usar last_id_pos)
    if ls_id_stack:
        id_pos = ls_id_stack.pop()
    else:
        id_pos = last_id_pos  # Fallback (no debería ocurrir)
    
    sym_type = get_symbol_type(id_pos)
    name = get_symbol_name(id_pos)

    if idopt == T_ERROR:
        sem_stack.append(T_ERROR)
    elif idopt == T_OK: 
        # Llamada a función con retorno void - verificar que es función
        if sym_type and "->" in str(sym_type):
            parts = str(sym_type).split("->")
            ret_type = parts[1].strip()
            sem_stack.append(T_OK if ret_type == T_VOID else ret_type)
        else:
            sem_stack.append(T_OK)
    else:
        # Validación de asignación o retorno función
        if sym_type and "->" in str(sym_type):
             # Es llamada, IdOpt es el retorno
             sem_stack.append(idopt)
        elif sym_type == idopt:
             sem_stack.append(sym_type)
        elif sym_type == T_FLOAT and idopt == T_INT:
             sem_stack.append(sym_type)
        else:
             sem_error(f"Asignación incorrecta a '{name}'. Variable es {sym_type}, valor es {idopt}")
             sem_stack.append(T_ERROR)

def action_ls_read():
    sem_stack.append(T_OK)

def action_ls_write():
    """LS -> write Expresion
    
    Per el EdT:
    LS.tipo := if Expresion.tipo = int then tipo_ok
               else if Expresion.tipo = float then tipo_ok
               else if Expresion.tipo = string then tipo_ok
               else tipo_error
    
    Nota: boolean NO está permitido según el EdT.
    """
    t = sem_stack.pop()
    if t in [T_INT, T_FLOAT, T_STRING]:
        sem_stack.append(T_OK)
    else:
        sem_error(f"write() no soporta el tipo {t}")
        sem_stack.append(T_ERROR)

def action_ls_return():
    t = sem_stack.pop()
    sem_stack.append(t) 

def action_idopt_call():
    """IdOpt -> oppar ArgsLlamada clpar: Llamada a función.
    
    Per el EdT: IdOpt.tipo := ArgsLlamada.tipo, IdOpt.igualacion := tipo_ok
    CRÍTICO: Usar ls_id_stack[-1] (NO last_id_pos) para obtener el id de la función.
    """
    global ls_id_stack
    
    args_llamada = sem_stack.pop()
    
    # CRÍTICO: El id de la función está en ls_id_stack (NO en last_id_pos)
    # last_id_pos ahora contiene el último argumento procesado
    if ls_id_stack:
        func_id = ls_id_stack[-1]  # Peek (no pop, lo hace action_ls_id_res)
    else:
        func_id = last_id_pos  # Fallback
    
    sym_type = get_symbol_type(func_id)
    name = get_symbol_name(func_id)
    
    if not sym_type:
        sem_error(f"Función no declarada: {name}")
        sem_stack.append(T_ERROR)
    elif "->" not in str(sym_type):
        sem_error(f"'{name}' no es una función (es {sym_type})")
        sem_stack.append(T_ERROR)
    else:
        parts = str(sym_type).split("->")
        ret_type = parts[1].strip()
        # Empujar T_OK como marcador de igualacion (llamada válida)
        sem_stack.append(T_OK)

def action_idopt_eq():
    pass 

def action_idopt_pluseq():
    t = sem_stack.pop()
    if t in [T_INT, T_FLOAT]:
        sem_stack.append(t)
    else:
        sem_error("Operador += requiere tipo numérico")
        sem_stack.append(T_ERROR)

# Tipos Primitivos
def action_type_int(): sem_stack.append(T_INT)
def action_type_float(): sem_stack.append(T_FLOAT)
def action_type_string(): sem_stack.append(T_STRING)
def action_type_bool(): sem_stack.append(T_BOOL)
def action_type_void(): sem_stack.append(T_VOID)
def action_type_inherit(): pass 

def action_asign_eq():
    pass 

def action_asign_lambda():
    sem_stack.append(T_VOID)

def action_ret_exp():
    pass 

def action_ret_lambda():
    sem_stack.append(T_VOID)

def action_exp_logic():
    aux = sem_stack.pop()
    e1 = sem_stack.pop()
    if aux == T_VOID: sem_stack.append(e1)
    elif aux == T_BOOL and e1 == T_BOOL: sem_stack.append(T_BOOL)
    elif aux == e1: sem_stack.append(T_BOOL)
    else: 
        sem_stack.append(T_ERROR)

def action_expaux_and():
    t = sem_stack.pop()
    if t == T_BOOL: sem_stack.append(T_BOOL)
    else: sem_stack.append(T_ERROR)

def action_expaux_lambda():
    sem_stack.append(T_VOID)

def action_exp1_rel():
    aux = sem_stack.pop()
    e2 = sem_stack.pop()
    if aux == T_VOID: sem_stack.append(e2)
    elif aux == T_BOOL: sem_stack.append(T_BOOL) 
    else: sem_stack.append(T_ERROR)

def action_exp1aux_min():
    t = sem_stack.pop()
    if t in [T_INT, T_FLOAT]: 
        sem_stack.append(T_BOOL) 
    else: 
        sem_error(f"Operador < requiere numéricos. Recibido: {t}")
        sem_stack.append(T_ERROR)

def action_exp1aux_lambda():
    sem_stack.append(T_VOID)

def action_exp2_arit():
    aux = sem_stack.pop()
    e3 = sem_stack.pop()
    if aux == T_VOID: sem_stack.append(e3)
    elif aux == e3: sem_stack.append(e3)
    elif (e3 == T_FLOAT and aux == T_INT) or (e3 == T_INT and aux == T_FLOAT):
        sem_stack.append(T_FLOAT) 
    else: sem_stack.append(T_ERROR)

def action_exp2aux_sum():
    t = sem_stack.pop()
    if t in [T_INT, T_FLOAT]: sem_stack.append(t)
    else: sem_stack.append(T_ERROR)

def action_exp2aux_lambda():
    sem_stack.append(T_VOID)

def action_exp3_par():
    pass 

def action_exp3_id_pre():
    global id_stack
    id_stack.append(last_id_pos)

def action_exp3_id():
    """Expresion3 -> id Expresion4: Evalúa un identificador en una expresión.
    
    Per el EdT:
    Expresion3.tipo := if BuscaTipoTS(id.pos) := Expresion4.tipo -> t then t
                       else if BuscaTipoTS(id.pos) := s -> t then tipo_error
                       else BuscaTipoTS(id.pos)
    
    REGLA MyJS: Si la variable no ha sido declarada (tipo == 'ID'), se declara
    implícitamente como int global.
    """
    global id_stack, despG
    
    e4 = sem_stack.pop()
    
    # Recuperar el id correcto de la pila (el que empujamos en action_exp3_id_pre)
    if id_stack:
        id_pos = id_stack.pop()
    else:
        id_pos = last_id_pos  # Fallback (no debería ocurrir)
    
    sym_type = get_symbol_type(id_pos)
    name = get_symbol_name(id_pos)
    
    # REGLA MyJS: Si sym_type == 'ID', la variable no fue declarada formalmente.
    # Se declara implícitamente como int global.
    if sym_type is None or sym_type == 'ID':
        # Declaración implícita: variable global de tipo int
        set_symbol_type(id_pos, T_INT)
        set_symbol_displacement(id_pos, despG)
        despG += get_width(T_INT)
        sym_type = T_INT  # Actualizar para el resto de la lógica

    # Caso 1: Expresion4 -> lambda (e4 == T_VOID): id usado como variable
    if e4 == T_VOID:
        if "->" in str(sym_type):
             sem_error(f"Uso de función '{name}' sin paréntesis")
             sem_stack.append(T_ERROR)
        else:
             sem_stack.append(sym_type)
    # Caso 2: Expresion4 -> oppar ArgsLlamada clpar: id usado como llamada a función
    elif isinstance(e4, tuple) and e4[0] == "CALL":
        args_tipo = e4[1]  # Tipos de los argumentos pasados
        
        if "->" not in str(sym_type):
            sem_error(f"'{name}' no es una función (es {sym_type})")
            sem_stack.append(T_ERROR)
        else:
            # sym_type tiene formato: "args_esperados -> ret_type"
            parts = str(sym_type).split("->")
            expected_args = parts[0].strip()
            ret_type = parts[1].strip()
            
            # Validar que los argumentos pasados coincidan con los esperados
            if args_tipo == expected_args:
                # Coincidencia exacta de tipos
                sem_stack.append(ret_type)
            elif args_tipo == T_VOID and expected_args == "":
                # Llamada sin argumentos a función sin parámetros
                sem_stack.append(ret_type)
            else:
                # Error: tipos de argumentos no coinciden
                sem_error(f"Llamada a '{name}': argumentos incompatibles. Esperado ({expected_args}), recibido ({args_tipo})")
                sem_stack.append(T_ERROR)
    else:
        # Fallback inesperado
        sem_error(f"Estado inesperado en expresión con '{name}'")
        sem_stack.append(T_ERROR)

def action_exp4_call():
    # ArgsLlamada.tipo ya está en la pila, solo marcamos que es una llamada
    # Reemplazamos el tipo de ArgsLlamada con un marcador de llamada + los args
    args_tipo = sem_stack.pop()
    sem_stack.append(("CALL", args_tipo))

def action_exp4_lambda():
    # Expresion4 -> lambda (id usado como variable, no como llamada)
    sem_stack.append(T_VOID)

# --- MAPEO COMPLETO DE REGLAS ---

SEMANTIC_RULES = {
    ('S', ('LC', 'S')): [(0, action_init_global)],
    ('S', ('LF', 'S')): [(0, action_init_global)],
    ('S', ('eof',)): [(0, action_init_global)],
    
    ('LC', ('LS', 'semicolon')): [(2, action_lc_check)],
    ('LC', ('if', 'oppar', 'Expresion', 'clpar', 'CuerpoIf', 'LE')): [(6, action_lc_if)],
    
    ('LE', ('else', 'CuerpoIf')): [(2, action_le_else)],
    ('LE', ('lambda',)): [(1, action_le_lambda)],
    
    ('LF', ('function', 'TypeFun', 'id', 'oppar', 'Args', 'clpar', 'opbra', 'Cuerpo', 'clbra')): 
        [(3, action_fun_init), (6, action_fun_def), (9, action_fun_end)],
    
    ('Cuerpo', ('LC', 'Cuerpo')): [(2, action_cuerpo_lc)],
    ('Cuerpo', ('lambda',)): [(1, action_cuerpo_lambda)],
    
    ('Args', ('Tipo', 'id', 'ArgMore')): [(1, action_args_init), (2, action_args_id), (3, action_args_res)],
    ('Args', ('void',)): [(1, action_args_void)],
    
    ('ArgMore', ('comma', 'Tipo', 'id', 'ArgMore')): [(2, action_argmore_tipo), (3, action_argmore_id), (4, action_argmore_res)],
    ('ArgMore', ('lambda',)): [(1, action_argmore_lambda)],
    
    ('ArgsLlamada', ('Expresion', 'ArgMoreLlamada')): [(2, action_argsl_call)],
    ('ArgsLlamada', ('lambda',)): [(1, action_argsl_lambda)],
    
    ('ArgMoreLlamada', ('comma', 'Expresion', 'ArgMoreLlamada')): [(3, action_argmore_call)],
    ('ArgMoreLlamada', ('lambda',)): [(1, action_argmore_lambda)],
    
    ('LS', ('let', 'Tipo', 'id', 'Asignar')): [(2, action_ls_let_pre), (3, action_ls_let_id), (4, action_ls_let_res)],
    ('LS', ('id', 'IdOpt')): [(1, action_ls_id_pre), (2, action_ls_id_res)],
    ('LS', ('read', 'id')): [(2, action_ls_read)],
    ('LS', ('write', 'Expresion')): [(2, action_ls_write)],
    ('LS', ('return', 'ExpReturn')): [(2, action_ls_return)],
    
    ('IdOpt', ('oppar', 'ArgsLlamada', 'clpar')): [(3, action_idopt_call)],
    ('IdOpt', ('eq', 'Expresion')): [(2, action_idopt_eq)],
    ('IdOpt', ('pluseq', 'Expresion')): [(2, action_idopt_pluseq)],
    
    ('TypeFun', ('void',)): [(1, action_type_void)],
    ('TypeFun', ('Tipo',)): [(1, action_type_inherit)],
    
    ('Tipo', ('int',)): [(1, action_type_int)],
    ('Tipo', ('float',)): [(1, action_type_float)],
    ('Tipo', ('string',)): [(1, action_type_string)],
    ('Tipo', ('boolean',)): [(1, action_type_bool)],
    
    ('Asignar', ('eq', 'Expresion')): [(2, action_asign_eq)],
    ('Asignar', ('lambda',)): [(1, action_asign_lambda)],
    
    ('ExpReturn', ('Expresion',)): [(1, action_ret_exp)],
    ('ExpReturn', ('lambda',)): [(1, action_ret_lambda)],
    
    ('Expresion', ('Expresion1', 'ExpresionAux')): [(2, action_exp_logic)],
    
    ('ExpresionAux', ('and', 'Expresion')): [(2, action_expaux_and)],
    ('ExpresionAux', ('lambda',)): [(1, action_expaux_lambda)],
    
    ('Expresion1', ('Expresion2', 'Expresion1Aux')): [(2, action_exp1_rel)],
    
    ('Expresion1Aux', ('minorthan', 'Expresion1')): [(2, action_exp1aux_min)],
    ('Expresion1Aux', ('lambda',)): [(1, action_exp1aux_lambda)],
    
    ('Expresion2', ('Expresion3', 'Expresion2Aux')): [(2, action_exp2_arit)],
    
    ('Expresion2Aux', ('sum', 'Expresion2')): [(2, action_exp2aux_sum)],
    ('Expresion2Aux', ('lambda',)): [(1, action_exp2aux_lambda)],
    
    ('Expresion3', ('oppar', 'Expresion', 'clpar')): [(3, action_exp3_par)],
    ('Expresion3', ('intconst',)): [(1, action_type_int)],
    ('Expresion3', ('realconst',)): [(1, action_type_float)],
    ('Expresion3', ('str',)): [(1, action_type_string)],
    ('Expresion3', ('true',)): [(1, action_type_bool)],
    ('Expresion3', ('false',)): [(1, action_type_bool)],
    ('Expresion3', ('id', 'Expresion4')): [(1, action_exp3_id_pre), (2, action_exp3_id)],
    
    ('Expresion4', ('oppar', 'ArgsLlamada', 'clpar')): [(3, action_exp4_call)],
    ('Expresion4', ('lambda',)): [(1, action_exp4_lambda)],
}

###### FIN SECCIÓN DE ANÁLISIS SEMÁNTICO ######

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
    """Construye la tabla de análisis sintáctico LL(1)."""
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
                    # Importante LL(1): al propagar por FOLLOW en anulables, no se debe
                    # sobrescribir una entrada ya ocupada por una producción no-lambda.
                    if terminal not in parsing_table[nt]:
                        parsing_table[nt][terminal] = production

def token_type_to_grammar_symbol(token):
    """Mapea `token.type` (PLY) al nombre de terminal usado por la gramática LL(1)."""
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

    if line == 0:
        line = prev_lineno  

    # Tratamiento del símbolo a mostrar
    token_info = get_symbol(token.value)

    if token_info is None:
        showID = terminal
    else:
        showID = token_info['value']

    # Mensajes de error específicos por no terminal
    print(f"MyJS Syntactic Error: En la línea {line}", end=' ')

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
    else:
        print(f"se esperaba '{no_terminal}', pero se encontró '{showID}'")

current_token = None
prev_token = None
lexed_file = None

def init_lexer_for_parser(code):
    global current_token, prev_token
    lexer.input(code)
    # Primer token: se escribe en `lexed.txt` y queda listo como lookahead del parser.
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

    # Volcado de tokens para inspección externa (formato de la práctica).
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
    """Ejecuta el análisis LL(1) con pila.

    La pila mezcla símbolos de gramática (terminales/no terminales) y callbacks Python.
    Las callbacks implementan el EdT: consumen/produces atributos vía `sem_stack`.
    """
    global stack, production_sequence, current_token, last_id_pos, global_initialized

    stack = ['eof', grammar['axiom']]
    production_sequence = []
    
    # Resetear estado global para nueva ejecución
    global_initialized = False
    
    # Inicialización forzada del semántico
    action_init_global()

    while stack:
        top = stack[-1]
        
        # 1. Ejecutar Acción Semántica (Si hay una función en el tope)
        if callable(top):
            top()
            stack.pop()
            continue
            
        current_symbol = token_type_to_grammar_symbol(current_token)

        # 2. Match de terminal: consume el lookahead si coincide.
        if top in grammar['terminals'] or top == 'eof':
            if top == current_symbol:
                # Capturar id.pos para las acciones semánticas asociadas al identificador.
                if top == 'id':
                    last_id_pos = current_token.value # Guardar posición TS
                
                stack.pop()
                # EOF es un terminal “sentinela”: se consume en la pila pero no se avanza
                # el lexer, para evitar lecturas repetidas de EOF y duplicados en `lexed.txt`.
                if top != 'eof':
                    advance_token()
            else:
                handle_syntactic_error(top, current_symbol, current_token)
                return False
        
        # 3. Expandir No Terminal
        elif top in grammar['non_terminals']:
            rules_for_top = parsing_table.get(top, {})
            
            if current_symbol in rules_for_top:
                production = rules_for_top[current_symbol]
                production_key = (top, tuple(production))
                
                if production_key in grammar['production_numbers']:
                    production_sequence.append(grammar['production_numbers'][production_key])
                
                stack.pop()
                
                # Inyección de símbolos + acciones en la pila.
                # Convención: las acciones vienen indexadas por “posición” dentro de la
                # producción para poder ejecutarlas en el punto exacto del EdT.
                if production and production[0] != 'lambda':
                    actions = SEMANTIC_RULES.get(production_key, [])
                    # Necesitamos empujar en orden inverso: C, B, A
                    # E intercalar acciones.
                    # Producción: A (1) B (2) C (3)
                    
                    items_to_push = []
                    
                    # Recorrer símbolos de derecha a izquierda (len..1)
                    for i in range(len(production), 0, -1):
                        # Acciones después del símbolo i
                        for idx, act in actions:
                            if idx == i: items_to_push.append(act)
                        
                        items_to_push.append(production[i-1])
                    
                    # Acciones antes del primer símbolo (0)
                    for idx, act in actions:
                        if idx == 0: items_to_push.append(act)
                        
                    # Empujar todo a la pila (como append añade al final, y stack es LIFO,
                    # el último append es el tope. items_to_push[0] debe ser lo más profundo.
                    # Pero hemos construido items_to_push en orden inverso (C, B, A).
                    # Ejemplo: A, B. items = [Act2, B, Act1, A, Act0].
                    # Al hacer append en ese orden: stack... Act2, B, Act1, A, Act0(tope).
                    # Correcto.
                    
                    for item in items_to_push:
                        stack.append(item)
                        
                else:
                    # Caso Lambda
                    actions = SEMANTIC_RULES.get(production_key, [])
                    # Solo acciones índice 1 (o 0/1, lambda cuenta como 1 posición abstracta)
                    for idx, act in actions:
                        stack.append(act)
                        
            else:
                handle_syntactic_error(top, current_symbol, current_token)
                return False
        else:
            print(f"Error: Símbolo desconocido {top}")
            return False

    return token_type_to_grammar_symbol(current_token) == 'eof'

######    FIN SECCIÓN DE ANALIZADOR SINTÁCTICO    ######

def main():
    """Función principal del analizador."""
    parser = argparse.ArgumentParser(
        description='Analizador Léxico, Sintáctico y Semántico para MyJS',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("file", help="Archivo fuente MyJS a analizar")
    args = parser.parse_args()

    # Verificar que el archivo existe
    try:
        with open(args.file, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{args.file}'")
        sys.exit(1)
    except IOError as e:
        print(f"Error al leer el archivo: {e}")
        sys.exit(1)

    # Verificar que existe el archivo de gramática
    try:
        with open('Gramatica.txt', 'r') as f:
            pass
    except FileNotFoundError:
        print("Error: No se encontró el archivo 'Gramatica.txt'")
        sys.exit(1)

    global lexed_file, symbols_file
    
    # Limpiar errores de ejecuciones anteriores
    clear_lex_errors()

    # `lexed.txt` se genera durante el análisis (streaming). La TS se vuelca al final.
    try:
        with open('lexed.txt', 'w', encoding="utf-8") as lf:
            lexed_file = lf
            symbols_file = None

            load_grammar('Gramatica.txt')
            build_parsing_table()

            # Inicializar lexer (lookahead listo) y ejecutar parser+semántico.
            init_lexer_for_parser(content)

            # Ejecutar análisis sintáctico y semántico
            ok = parse()

    except IOError as e:
        print(f"Error al escribir archivos de salida: {e}")
        sys.exit(1)

    # Reportar errores léxicos acumulados (si existen).
    if has_lex_errors():
        print_lex_errors()

    # Escribir tabla de símbolos al final con todos los atributos
    try:
        with open('symbols.txt', 'w', encoding='utf-8') as sf:
            write_symbol_table_to_file(sf)
    except IOError as e:
        print(f"Error al escribir tabla de símbolos: {e}")

    # Generar parse.txt
    if ok and not has_lex_errors():
        try:
            with open('parse.txt', 'w') as f:
                f.write("Descendente ")
                for production_num in production_sequence:
                    f.write(f"{production_num} ")
            print("Análisis completado exitosamente.")
            print("Archivos generados: lexed.txt, symbols.txt, parse.txt")
        except IOError as e:
            print(f"Error al escribir parse.txt: {e}")
            sys.exit(1)
    else:
        print("\nAnálisis finalizado con errores.")
        print("Archivos generados: lexed.txt, symbols.txt")
        sys.exit(1)

if __name__ == "__main__":
    main()
