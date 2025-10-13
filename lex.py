import ply.lex as lex
import argparse

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
	"MINORTHAN"
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

tokens = [
    "REALCONST", "INTCONST", "STR", "ID", "EOF"
] + noattr + list(reserved.values())

t_PLUSEQ     = r'\+='
t_EQ         = r'='
t_COMMA      = r','
t_SEMICOLON  = r';'
t_OPPAR      = r'\('
t_CLPAR      = r'\)'
t_OPBRA      = r'\['
t_CLBRA      = r'\]'
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
	return t

def t_INTCONST(t):
	r'\d+'
	try:
		t.value = int(t.value)
	except ValueError:
		print("Integer number value error:", t.value)
	return t

def t_STR(t):
	r'\'([^\\\n]|(\\.))*?\''
	try:
		t.value = t.value[1:-1]
	except ValueError:
		print("String value error", t.value)
	return t

def t_ID(t):
	r'[a-zA-Z_][a-zA-Z_0-9]*'
	lower = t.value.lower()
	if lower in reserved:
		t.type = reserved[lower]
		t.value = ''
	else:
		t.type = "ID"
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

def main():

	parser = argparse.ArgumentParser()
	parser.add_argument("file") #args.file es el "puntero" a la file
	args = parser.parse_args()

	with open(args.file, 'r') as f:
		content = f.read()

	lexer.input(content)
	with open('output.txt', 'w', encoding="utf-8") as f:
		for tok in lexer:
			if tok.type in noattr:
				f.write(f'<{tok.type},>\n')
			else:
				f.write(f'<{tok.type},{tok.value}>\n')

if __name__ == "__main__":
	main()