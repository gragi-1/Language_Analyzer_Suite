Summarized conversation history# Documentación del Analizador Semántico de MyJS

## 1. Arquitectura General: Traducción Dirigida por la Sintaxis (TDS)

El analizador semántico de MyJS implementa un esquema de **Traducción Dirigida por la Sintaxis (Syntax-Directed Translation)**. Esto significa que las acciones semánticas se ejecutan en puntos específicos durante el análisis sintáctico LL(1).

### Principio de Funcionamiento

```
Pila del Parser = Símbolos de Gramática + Funciones Python (callbacks)
```

Cuando el parser expande una producción, no solo empuja los símbolos gramaticales a la pila, sino también **funciones Python** en las posiciones exactas donde el Esquema de Traducción (EdT) indica que debe ejecutarse una acción semántica.

**Ejemplo:** Para la producción `LS -> let Tipo id Asignar`:
```
Pila: [..., let, Tipo, action_ls_let_pre, id, action_ls_let_id, Asignar, action_ls_let_res]
```

Las funciones se ejecutan automáticamente cuando llegan al tope de la pila.

---

## 2. Estructuras de Datos Principales

### 2.1. Pila Semántica (`sem_stack`)
```python
sem_stack = []
```
Es la **pila de atributos sintetizados**. Las acciones semánticas:
- **Empujan** (`append`) el tipo/valor calculado de un símbolo.
- **Extraen** (`pop`) los tipos de los hijos para calcular el del padre.

**Flujo típico:**
```
Expresion -> Expresion1 ExpresionAux
             └─ push(T_INT)  └─ push(T_VOID)
                    ↓               ↓
           action_exp_logic() hace:
              aux = pop()  # T_VOID
              e1 = pop()   # T_INT
              push(T_INT)  # resultado
```

### 2.2. Pilas Auxiliares de IDs
El problema: cuando procesamos `id IdOpt` y dentro de `IdOpt` hay una llamada a función con argumentos que son identificadores, `last_id_pos` se sobrescribe.

**Solución:** Pilas específicas para preservar contextos:

| Pila | Uso |
|------|-----|
| `id_stack` | Para `Expresion3 -> id Expresion4` (expresiones) |
| `decl_id_stack` | Para `LS -> let Tipo id Asignar` (declaraciones) |
| `ls_id_stack` | Para `LS -> id IdOpt` (asignaciones/llamadas) |

### 2.3. Variables de Estado Global
```python
last_id_pos = -1       # Posición TS del último 'id' consumido
current_func_id = -1   # ID de la función en declaración
despG = 0              # Desplazamiento global (variables globales)
despL = 0              # Desplazamiento local (parámetros/vars locales)
in_function = False    # ¿Estamos dentro de una función?
temp_type = None       # Tipo temporal para parámetros
```

---

## 3. Constantes de Tipos

```python
T_INT = 'int'
T_FLOAT = 'float'
T_STRING = 'string'
T_BOOL = 'boolean'
T_VOID = 'void'       # Sin valor / función sin retorno
T_ERROR = 'tipo_error' # Error de tipos
T_OK = 'tipo_ok'       # Sentencia válida sin valor
```

---

## 4. Funciones Auxiliares

### Interacción con Tabla de Símbolos
```python
get_width(type_str)           # Bytes de un tipo (int=1, float=2, bool=1, string=64)
set_symbol_type(pos, type)    # Asignar tipo a símbolo
get_symbol_type(pos)          # Obtener tipo de símbolo
get_symbol_name(pos)          # Obtener lexema para errores legibles
get_current_line()            # Línea actual para errores
sem_error(msg)                # Registrar error semántico
```

---

## 5. Acciones Semánticas por Categoría

### 5.1. Inicialización y Scopes

#### `action_init_global()`
**Regla:** `S -> LC S | LF S | eof`

Inicializa el estado global una sola vez:
```python
if not global_initialized:
    despG = 0
    sem_stack = []
    # ... limpiar pilas ...
    global_initialized = True
```

#### `action_fun_init()`
**Regla:** `LF -> function TypeFun id ( Args ) { Cuerpo }`

Al encontrar el `id` de la función:
1. Guarda `current_func_id = last_id_pos`
2. Crea nuevo scope: `enter_scope()`
3. Inicializa desplazamiento local: `despL = 0`
4. Marca: `in_function = True`

#### `action_fun_end()`
**Regla:** Fin de `LF`

1. Guarda la tabla local en `function_tables` para el volcado
2. Destruye el scope: `exit_scope()`
3. Marca: `in_function = False`

---

### 5.2. Declaraciones de Variables

#### `action_ls_let_id()`
**Regla:** `LS -> let Tipo id Asignar` (al procesar `id`)

```python
# 1. Obtener tipo de la pila
tipo = sem_stack[-1]  # Peek (no pop, lo usará action_ls_let_res)

# 2. Si estamos en función y la variable existe globalmente → SHADOWING
if in_function and name not in current_scope:
    new_pos = add_symbol_to_current_scope(name, tipo, name)
    last_id_pos = new_pos

# 3. Asignar tipo y desplazamiento
set_symbol_type(last_id_pos, tipo)
if in_function:
    set_symbol_displacement(last_id_pos, despL)
    despL += get_width(tipo)
else:
    set_symbol_displacement(last_id_pos, despG)
    despG += get_width(tipo)

# 4. Guardar id para la fase final
decl_id_stack.append(last_id_pos)
```

#### `action_ls_let_res()`
**Regla:** `LS -> let Tipo id Asignar` (después de `Asignar`)

Verifica compatibilidad de tipos:
```python
asign = sem_stack.pop()  # Tipo del valor asignado
tipo = sem_stack.pop()   # Tipo declarado

if asign == T_VOID:      # Sin asignación (let x;)
    push(tipo)
elif asign == tipo:      # Tipos coinciden
    push(tipo)
elif tipo == T_FLOAT and asign == T_INT:  # Coerción int→float
    push(tipo)
else:
    sem_error(f"asignación incorrecta...")
    push(T_ERROR)
```

---

### 5.3. Declaración de Funciones

#### `action_fun_def()`
**Regla:** `LF -> function TypeFun id ( Args ) ...`

Construye la firma de la función:
```python
args_type = sem_stack.pop()  # "int x float" o "void"
ret_type = sem_stack.pop()   # "int" o "void"

if args_type == T_VOID:
    sig = f"void -> {ret_type}"
else:
    sig = f"{args_type} -> {ret_type}"

# Guardar en TS (scope padre/global)
sym = get_symbol(current_func_id)
sym['type'] = sig  # Ej: "int x float -> boolean"
```

#### `action_args_id()` / `action_argmore_id()`
**Regla:** `Args -> Tipo id ArgMore`

Al procesar cada parámetro:
```python
tipo = sem_stack[-1]  # Tipo del parámetro
set_symbol_type(last_id_pos, tipo)
set_symbol_displacement(last_id_pos, despL)
despL += get_width(tipo)
```

#### `action_args_res()` / `action_argmore_res()`
Construye la cadena de tipos de argumentos:
```python
# Si hay más argumentos: "int x float x string"
# Si no hay más: solo el tipo
if am == T_VOID:
    push(t)           # Ej: "int"
else:
    push(f"{t} x {am}")  # Ej: "int x float"
```

---

### 5.4. Tipos Primitivos

```python
def action_type_int():   sem_stack.append(T_INT)
def action_type_float(): sem_stack.append(T_FLOAT)
def action_type_string():sem_stack.append(T_STRING)
def action_type_bool():  sem_stack.append(T_BOOL)
def action_type_void():  sem_stack.append(T_VOID)
```

---

### 5.5. Expresiones

#### `action_exp3_id_pre()` y `action_exp3_id()`
**Regla:** `Expresion3 -> id Expresion4`

```python
# PRE: Guardar id antes de que Expresion4 lo sobrescriba
def action_exp3_id_pre():
    id_stack.append(last_id_pos)

# POST: Evaluar según Expresion4
def action_exp3_id():
    e4 = sem_stack.pop()
    id_pos = id_stack.pop()  # Recuperar id correcto
    sym_type = get_symbol_type(id_pos)
    
    # Declaración implícita si no existe
    if sym_type is None or sym_type == 'ID':
        set_symbol_type(id_pos, T_INT)
        # ... asignar desplazamiento ...
    
    if e4 == T_VOID:
        # Es variable, no llamada
        push(sym_type)
    elif e4[0] == "CALL":
        # Es llamada a función
        # Validar argumentos vs firma
        # push(ret_type) o push(T_ERROR)
```

#### `action_exp4_call()`
**Regla:** `Expresion4 -> ( ArgsLlamada )`

```python
args_tipo = sem_stack.pop()
sem_stack.append(("CALL", args_tipo))  # Marcador especial
```

#### Operadores: `action_expaux_and()`, `action_exp1aux_min()`, `action_exp2aux_sum()`

Siguen el patrón:
```python
def action_expaux_and():
    aux = sem_stack.pop()   # Resultado recursivo
    e1 = sem_stack.pop()    # Operando izquierdo
    
    if e1 == T_BOOL:
        if aux == T_VOID or aux == T_BOOL:
            push(T_BOOL)
        else:
            push(T_ERROR)
    else:
        sem_error("&& requiere boolean")
        push(T_ERROR)
```

| Operador | Tipos válidos | Resultado |
|----------|---------------|-----------|
| `&&` | boolean, boolean | boolean |
| `<` | int/float, int/float | boolean |
| `+` | int/float, int/float | int o float (coerción) |

---

### 5.6. Sentencias de Control

#### `action_lc_if()`
**Regla:** `LC -> if ( Expresion ) CuerpoIf LE`

```python
le_type = sem_stack.pop()     # Tipo del else (o T_OK)
cuerpo_type = sem_stack.pop() # Tipo del cuerpo if
exp_type = sem_stack.pop()    # Tipo de la condición

if exp_type == T_BOOL:
    if cuerpo_type == T_OK:
        push(le_type)
    else:
        push(T_ERROR)
else:
    sem_error("condición if requiere boolean")
    push(T_ERROR)
```

---

### 5.7. Sentencias I/O

#### `action_ls_write()`
**Regla:** `LS -> write Expresion`

```python
t = sem_stack.pop()
if t in [T_INT, T_FLOAT, T_STRING]:
    push(T_OK)
else:
    sem_error(f"write() no soporta {t}")  # boolean no permitido
    push(T_ERROR)
```

---

## 6. Mapeo de Reglas: `SEMANTIC_RULES`

El diccionario `SEMANTIC_RULES` asocia cada producción con sus acciones semánticas y el **momento** de ejecución:

```python
SEMANTIC_RULES = {
    # (no_terminal, tupla_produccion): [(posición, función), ...]
    
    ('LS', ('let', 'Tipo', 'id', 'Asignar')): [
        (2, action_ls_let_pre),   # Después de Tipo (pos 2)
        (3, action_ls_let_id),    # Después de id (pos 3)
        (4, action_ls_let_res)    # Después de Asignar (pos 4)
    ],
    
    ('Expresion3', ('id', 'Expresion4')): [
        (1, action_exp3_id_pre),  # Después de id (pos 1)
        (2, action_exp3_id)       # Después de Expresion4 (pos 2)
    ],
    # ...
}
```

**Posiciones:**
- `0` = Antes del primer símbolo
- `1` = Después del primer símbolo
- `n` = Después del n-ésimo símbolo

---

## 7. Flujo de Ejecución Completo

```
1. Parser lee token 'let'
2. Expande LS -> let Tipo id Asignar
3. Pila: [let, Tipo, action_pre, id, action_id, Asignar, action_res]
4. Consume 'let', expande Tipo -> int, ejecuta action_type_int()
   → sem_stack: [T_INT]
5. Ejecuta action_ls_let_pre() (no hace nada)
6. Consume 'id', ejecuta action_ls_let_id()
   → Asigna tipo y desplazamiento al símbolo
   → Guarda id en decl_id_stack
7. Expande Asignar -> eq Expresion, procesa expresión
   → sem_stack: [T_INT, T_INT]  (tipo declarado, tipo expresión)
8. Ejecuta action_ls_let_res()
   → Valida compatibilidad, pop ambos, push resultado
   → sem_stack: [T_INT]
```

---

## 8. Gestión de Errores

Los errores semánticos se acumulan en `sem_errors[]`:

```python
def sem_error(msg):
    lineno = get_current_line()
    add_sem_error(lineno, msg)

# Ejemplo de error:
sem_error(f"asignación incorrecta en 'let {name}'. Tipo: {tipo}, valor: {asign}")
```

Al final del análisis, se imprimen todos con `print_sem_errors()`.

---

## 9. Resumen de Coerciones Implícitas

| Contexto | int → float | Otros |
|----------|-------------|-------|
| Asignación `let float x = 5` | ✅ | ❌ |
| Suma `5 + 3.14` | ✅ (resultado float) | ❌ |
| Comparación `5 < 3.14` | ✅ (resultado bool) | ❌ |

---

## 10. Tablas de Símbolos por Función

Al salir de una función (`action_fun_end`), se guarda una copia de su tabla local:

```python
function_tables.append((func_name, current_scope.copy()))
```

Esto permite generar el archivo symbols.txt con las tablas separadas:
```
CONTENIDOS DE LA TABLA #1:  (global)
CONTENIDOS DE LA TABLA miFuncion #2:  (local de miFuncion)
