#ARCHIVO IMPORTANTE PARA REVISAR LINEA A LINEA
#QUE LA SINTAXIS ESTE BIEN ESTRUCUTRADA CON FUNCIONES
def validar_punto_y_coma(input_file):
    """
    Función para validar que las sentencias y declaraciones terminan con punto y coma
    """
    with open(input_file, "r") as file:
        lines = file.readlines()

    errores = []
    in_comment = False  # Para rastrear comentarios multi-línea /* ... */
    
    for i, line in enumerate(lines):
        original_line = line.strip()
        line_content = original_line
        
        # Manejo de comentarios multi-línea
        if in_comment:
            if '*/' in original_line:
                in_comment = False
                line_content = original_line.split('*/', 1)[1].strip()
            else:
                continue  # Ignorar toda la línea si estamos dentro de un comentario
        elif '/*' in original_line:
            in_comment = True
            line_content = original_line.split('/*', 1)[0].strip()
            if not line_content:
                continue

        # Eliminar comentarios de una línea (//)
        if '//' in line_content:
            line_content = line_content.split('//', 1)[0].strip()

        # Ignorar líneas vacías después de procesar comentarios
        if not line_content:
            continue

        line_lower = line_content.lower()

        # Identificar líneas estructurales que NO requieren ';'
        is_structural = (
            line_lower.startswith(("programa", "inicio", "fin", "funciones", "si", "sino"))
            or line_lower.endswith("{")
            or line_lower in ("{", "}")
            or "fin" in line_lower.split()
            or line_lower.startswith(("para ", "mientras ", "ret "))
        )

        if is_structural:
            continue

        # Verificar punto y coma en líneas no estructurales
        if not line_content.endswith(";"):
            errores.append(f"[Línea {i + 1}] Error: Falta el punto y coma ';' al final de la sentencia: {original_line}")

    return errores

def validar_parentesis(input_file):
    """
    Función para validar que los paréntesis estén balanceados.
    Ignora paréntesis dentro de cadenas y comentarios.
    """
    with open(input_file, "r") as file:
        lines = file.readlines()

    errores = []
    stack = []  # Almacena tuplas (línea, columna) de aperturas '('
    in_string = False
    string_char = None  # ' o "
    in_block_comment = False
    in_single_line_comment = False

    for num_linea, line in enumerate(lines, 1):
        line = line.rstrip('\n')  # Mantener caracteres originales
        current_column = 0

        i = 0
        while i < len(line):
            char = line[i]
            current_column += 1

            # Manejar comentarios de bloque /* ... */
            if not in_string and not in_single_line_comment:
                if char == '/' and i < len(line) - 1 and line[i+1] == '*':
                    in_block_comment = True
                    i += 1  # Saltar el '*'
                elif char == '*' and i < len(line) - 1 and line[i+1] == '/' and in_block_comment:
                    in_block_comment = False
                    i += 1  # Saltar el '/'
            
            # Manejar comentarios de línea //
            if not in_string and not in_block_comment:
                if char == '/' and i < len(line) - 1 and line[i+1] == '/':
                    in_single_line_comment = True
            
            # Manejar cadenas (ignorar paréntesis dentro)
            if not in_block_comment and not in_single_line_comment:
                if char in ('"', "'"):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                        string_char = None

            # Verificar paréntesis solo fuera de comentarios y cadenas
            if not in_block_comment and not in_single_line_comment and not in_string:
                if char == '(':
                    stack.append((num_linea, current_column))
                elif char == ')':
                    if not stack:
                        errores.append(f"[Línea {num_linea}, Columna {current_column}] Paréntesis de cierre ')' sin apertura correspondiente.")
                    else:
                        stack.pop()

            i += 1

        # Resetear comentario de línea al final de cada línea
        in_single_line_comment = False

    # Verificar paréntesis sin cerrar al final del archivo
    for linea, columna in stack:
        errores.append(f"[Línea {linea}, Columna {columna}] Paréntesis de apertura '(' sin cierre correspondiente.")

    return errores

def validar_llaves(input_file):
    """
    Función para validar que las llaves {} estén balanceadas.
    Ignora llaves dentro de cadenas y comentarios.
    """
    with open(input_file, "r") as file:
        lines = file.readlines()

    errores = []
    stack = []  # Almacena tuplas (línea, columna, tipo) de aperturas
    in_string = False
    string_char = None  # ' o "
    in_block_comment = False
    in_single_line_comment = False

    for num_linea, line in enumerate(lines, 1):
        line = line.rstrip('\n')  # Mantener caracteres originales
        current_column = 0

        i = 0
        while i < len(line):
            char = line[i]
            current_column += 1

            # Manejar comentarios de bloque /* ... */
            if not in_string and not in_single_line_comment:
                if char == '/' and i < len(line) - 1 and line[i+1] == '*':
                    in_block_comment = True
                    i += 1  # Saltar el '*'
                elif char == '*' and i < len(line) - 1 and line[i+1] == '/' and in_block_comment:
                    in_block_comment = False
                    i += 1  # Saltar el '/'
            
            # Manejar comentarios de línea //
            if not in_string and not in_block_comment:
                if char == '/' and i < len(line) - 1 and line[i+1] == '/':
                    in_single_line_comment = True
            
            # Manejar cadenas (ignorar llaves dentro)
            if not in_block_comment and not in_single_line_comment:
                if char in ('"', "'"):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                        string_char = None

            # Verificar llaves solo fuera de comentarios y cadenas
            if not in_block_comment and not in_single_line_comment and not in_string:
                if char == '{':
                    stack.append((num_linea, current_column, '{'))
                elif char == '}':
                    if not stack or stack[-1][2] != '{':
                        errores.append(f"[Línea {num_linea}, Columna {current_column}] Llave de cierre '}}' sin apertura correspondiente.")
                    else:
                        stack.pop()

            i += 1

        # Resetear comentario de línea al final de cada línea
        in_single_line_comment = False

    # Verificar llaves sin cerrar al final del archivo
    for linea, columna, _ in stack:
        errores.append(f"[Línea {linea}, Columna {columna}] Llave de apertura '{{' sin cierre correspondiente.")

    return errores

import re

def validar_nombres_variables(input_file):
    """
    Valida que los nombres de variables:
    1. No sean palabras reservadas (case-insensitive)
    2. Sigan el patrón: letra seguida de letras, números o _
    3. No empiecen con número
    """
    # Palabras reservadas (case-insensitive)
    palabras_reservadas = {
        'programa', 'inicio', 'fin', 'si', 'sino', 'para', 
        'mientras', 'hacer', 'ret', 'pintar', 'entero', 
        'decimal', 'bool', 'cadena', 'void', 'var'
    }
    
    # Expresión regular para nombres válidos
    patron_variable = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    
    errores = []
    in_declaration = False
    in_function = False
    current_type = None
    
    with open(input_file, 'r') as file:
        for line_num, line in enumerate(file, 1):
            line = line.strip()
            
            # Detectar inicio/fin de funciones
            if 'funciones' in line.lower():
                in_function = True
                continue
            elif 'inicio' in line.lower():
                in_function = False
            
            # Ignorar líneas que son llamadas a función (contienen '(' y no son declaraciones)
            if '(' in line and ')' in line and not any(palabra in line.lower() for palabra in ['entero', 'decimal', 'bool', 'cadena', 'var']):
                continue
                
            # Ignorar líneas dentro de funciones (excepto declaraciones al inicio)
            if in_function and not line.startswith(('entero ', 'decimal ', 'bool ', 'cadena ', 'var ', 'void ')):
                continue
                
            # Detectar declaraciones de variables
            if any(palabra in line.lower() for palabra in ['entero', 'decimal', 'bool', 'cadena', 'var']):
                in_declaration = True
                parts = line.split()
                current_type = parts[0].lower() if parts[0].lower() in ['entero', 'decimal', 'bool', 'cadena', 'var'] else None
            
            if in_declaration and ';' in line:
                # Extraer la parte de la declaración (ignorando comentarios)
                decl_part = line.split(';')[0].split('//')[0].strip()
                
                # Manejar asignaciones
                if '=' in decl_part:
                    left_side = decl_part.split('=')[0].strip()
                    # Si el lado izquierdo tiene paréntesis, no es declaración simple
                    if '(' in left_side or ')' in left_side:
                        in_declaration = False
                        continue
                    vars_part = left_side
                else:
                    vars_part = decl_part
                
                # Obtener nombres de variables
                if current_type:
                    vars_part = vars_part.replace(current_type, '', 1).strip()
                
                # Filtrar posibles parámetros de función
                if '(' in vars_part or ')' in vars_part:
                    in_declaration = False
                    continue
                
                variables = [v.strip() for v in vars_part.split(',') if v.strip()]
                
                for var in variables:
                    # Verificar si es palabra reservada (solo si no contiene operadores)
                    if any(op in var for op in ['+', '-', '*', '/', '(', ')', '"', "'"]):
                        continue
                        
                    if var.lower() in palabras_reservadas:
                        errores.append(f"[Línea {line_num}] Error: '{var}' es una palabra reservada")
                    
                    # Verificar estructura del nombre (solo para nombres simples)
                    elif not patron_variable.match(var):
                        errores.append(f"[Línea {line_num}] Error: Nombre de variable inválido '{var}'")
                
                in_declaration = False
                current_type = None
    
    return errores