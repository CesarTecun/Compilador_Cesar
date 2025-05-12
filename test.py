import time
import os
import subprocess
from antlr4 import FileStream, CommonTokenStream, ParseTreeWalker
from ExprLexer import ExprLexer
from ExprParser import ExprParser
from ast_builder import ASTBuilder
from ir_generator import LLVMGenerator
from SemanticListener import SemanticListener
from SintacticValidacion import (
    validar_punto_y_coma,
    validar_parentesis,
    validar_llaves,
    validar_nombres_variables
)

def mostrar_menu():
    print("\nMENÚ DE COMPILACIÓN")
    print("1. Ejecutar flujo completo con optimización (opt)")
    print("2. Ejecutar flujo completo sin optimización")
    print("3. Solo generar código LLVM IR (.ll)")
    print("4. Compilar desde un .ll optimizado manualmente")
    print("5. Renombrar binario a .exe")
    print("6. Comparar desempeño entre variantes (-O1, -O2, -O3, sin optimizar, manual)")
    print("7. Salir")

def validar_sintaxis(input_file):
    errores = []
    errores.extend(validar_punto_y_coma(input_file))
    errores.extend(validar_parentesis(input_file))
    errores.extend(validar_llaves(input_file))
    errores.extend(validar_nombres_variables(input_file))
    return errores

def generar_llvm(input_file, for_windows_exe=False):
    input_stream = FileStream(input_file, encoding='utf-8')
    lexer = ExprLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = ExprParser(token_stream)
    tree = parser.prog()

    print("[INFO] Validando semánticamente...")
    walker = ParseTreeWalker()
    listener = SemanticListener()
    walker.walk(listener, tree)

    if listener.errors:
        print("\n[ERRORES SEMÁNTICOS DETECTADOS]")
        for error in listener.errors:
            print("  -", error)
        return None

    if listener.warnings:
        print("\n[ADVERTENCIAS]")
        for warning in listener.warnings:
            print("  -", warning)

    print("[INFO] Validación semántica completada sin errores.")

    ast_builder = ASTBuilder()
    ast = ast_builder.visit(tree)
    if not ast:
        print("[ERROR] El árbol de sintaxis abstracta (AST) es None.")
        return None

    print("[INFO] Generando código LLVM...")
    llvm_gen = LLVMGenerator(for_windows_exe=for_windows_exe)
    return llvm_gen.generate(ast)

def guardar_llvm(module, path):
    with open(path, "w") as f:
        f.write(str(module))
    print(f"[INFO] Código LLVM guardado en {path}")

def ejecutar_con_lli(output_ll):
    print(f"[INFO] Ejecutando {output_ll} con lli...")
    exec_start = time.time()
    subprocess.run(["lli", output_ll])
    exec_end = time.time()
    duration = exec_end - exec_start
    print(f"[INFO] Tiempo de ejecución con lli: {duration:.2f} segundos")
    return duration

def ejecutar_opcion_6():
    print("\n[COMPARACIÓN DE DESEMPEÑO ENTRE VARIANTES]")
    input_file = input("Ingrese el archivo fuente base (.txt): ").strip()
    if not input_file.endswith('.txt'):
        input_file += '.txt'
    if not os.path.exists(input_file):
        print("[ERROR] Archivo no encontrado.")
        return

    errores = validar_sintaxis(input_file)
    if errores:
        print("\n[ERRORES DE SINTAXIS DETECTADOS]:")
        for e in errores:
            print("  -", e)
        return

    module = generar_llvm(input_file)
    if not module:
        return

    base = os.path.splitext(input_file)[0]
    output_ll = f"{base}.ll"
    guardar_llvm(module, output_ll)

    tiempos = {}

    for nivel in ["-O1", "-O2", "-O3"]:
        opt_file = f"{base}_opt{nivel}.ll"
        print(f"\n[{nivel}] Aplicando optimización y ejecutando...")
        subprocess.run(["opt", nivel, output_ll, "-o", opt_file])
        tiempos[nivel] = ejecutar_con_lli(opt_file)

    print("\n[SIN OPTIMIZACIÓN] Ejecutando...")
    tiempos["sin_opt"] = ejecutar_con_lli(output_ll)

    print("\n[MANUAL] Ejecutando .ll optimizado manualmente...")
    manual_file = input("Ingrese archivo .ll optimizado manualmente (opcional): ").strip()
    if manual_file and not manual_file.endswith('.ll'):
        manual_file += '.ll'
    if manual_file and os.path.exists(manual_file):
        tiempos["manual"] = ejecutar_con_lli(manual_file)
    else:
        tiempos["manual"] = None
        print("[INFO] Archivo manual no proporcionado o no encontrado.")

    print("\n==== RESUMEN DE TIEMPOS ====")
    for key, value in tiempos.items():
        if value is None:
            print(f"  - {key:10}: [no ejecutado]")
        else:
            print(f"  - {key:10}: {value:.2f} seg")

def ejecutar_opcion_1():
    input_file = input("Ingrese el archivo fuente (.txt): ").strip()
    if not input_file.endswith('.txt'):
        input_file += '.txt'
    if not os.path.exists(input_file):
        print("[ERROR] Archivo no encontrado.")
        return

    errores = validar_sintaxis(input_file)
    if errores:
        print("\n[ERRORES DE SINTAXIS DETECTADOS]:")
        for e in errores:
            print("  -", e)
        return

    module = generar_llvm(input_file)
    if not module:
        return

    base = os.path.splitext(input_file)[0]
    output_ll = f"{base}.ll"
    guardar_llvm(module, output_ll)

    print("\nSeleccione nivel de optimización:")
    print("1. -O1\n2. -O2\n3. -O3")
    opt_opcion = input("Opción: ").strip()
    nivel = "-O2"
    if opt_opcion == "1":
        nivel = "-O1"
    elif opt_opcion == "3":
        nivel = "-O3"

    opt_output = f"{base}_opt{nivel}.ll"
    subprocess.run(["opt", nivel, output_ll, "-o", opt_output])
    ejecutar_con_lli(opt_output)

def ejecutar_opcion_2():
    input_file = input("Ingrese el archivo fuente (.txt): ").strip()
    if not input_file.endswith('.txt'):
        input_file += '.txt'
    if not os.path.exists(input_file):
        print("[ERROR] Archivo no encontrado.")
        return

    errores = validar_sintaxis(input_file)
    if errores:
        print("\n[ERRORES DE SINTAXIS DETECTADOS]:")
        for e in errores:
            print("  -", e)
        return

    module = generar_llvm(input_file)
    if not module:
        return

    output_ll = os.path.splitext(input_file)[0] + ".ll"
    guardar_llvm(module, output_ll)
    ejecutar_con_lli(output_ll)

def ejecutar_opcion_3():
    input_file = input("Ingrese el archivo fuente (.txt): ").strip()
    if not input_file.endswith('.txt'):
        input_file += '.txt'
    if not os.path.exists(input_file):
        print("[ERROR] Archivo no encontrado.")
        return

    errores = validar_sintaxis(input_file)
    if errores:
        print("\n[ERRORES DE SINTAXIS DETECTADOS]:")
        for e in errores:
            print("  -", e)
        return

    module = generar_llvm(input_file)
    if not module:
        return

    output_ll = os.path.splitext(input_file)[0] + ".ll"
    guardar_llvm(module, output_ll)

def ejecutar_opcion_4():
    input_ll = input("Ingrese el archivo .ll optimizado manualmente: ").strip()
    if not input_ll.endswith('.ll'):
        input_ll += '.ll'
    if not os.path.exists(input_ll):
        print("[ERROR] Archivo no encontrado.")
        return
    ejecutar_con_lli(input_ll)


def ejecutar_opcion_5():
    input_ll = input("Ingrese el archivo LLVM (.ll) a compilar para Windows: ").strip()
    if not input_ll.endswith('.ll'):
        input_ll += '.ll'

    if not os.path.exists(input_ll):
        print("[ERROR] Archivo .ll no encontrado.")
        return

    # Primero generamos el código LLVM con la pausa habilitada
    input_file = input_ll.replace('.ll', '.txt')  # Asumiendo que el fuente es .txt
    if os.path.exists(input_file):
        print("[INFO] Regenerando código LLVM con pausa para Windows...")
        module = generar_llvm(input_file, for_windows_exe=True)  # <-- Aquí el cambio
        if module:
            guardar_llvm(module, input_ll)  # Sobreescribimos el .ll con la versión con pausa
    else:
        print("[INFO] No se encontró el archivo fuente .txt, usando .ll directamente")

    # Resto del código de compilación a .exe (se mantiene igual)
    output_base = os.path.splitext(input_ll)[0]
    output_obj = output_base + ".o"
    output_exe = output_base + ".exe"

    print("[INFO] Generando archivo objeto en formato Windows con llc...")
    result_llc = subprocess.run(
        [
            "llc",
            "-mtriple=x86_64-pc-windows-gnu",  # Especifica el triplete objetivo
            "-filetype=obj",
            input_ll,
            "-o", output_obj
        ],
        capture_output=True,
        text=True
    )
    
    if result_llc.returncode != 0:
        print("[ERROR] Falló la compilación con llc:")
        print(result_llc.stderr)
        return
    if not os.path.exists(output_obj):
        print("[ERROR] El archivo objeto no se generó.")
        return

    # Paso 2: Enlazar con el compilador cruzado de MinGW
    print("[INFO] Enlazando con x86_64-w64-mingw32-gcc para generar .exe...")
    result_gcc = subprocess.run(
        [
            "x86_64-w64-mingw32-gcc",
            output_obj,
            "-o", output_exe
        ],
        capture_output=True,
        text=True
    )
    
    if result_gcc.returncode != 0:
        print("[ERROR] Falló la compilación cruzada con mingw-w64:")
        print(result_gcc.stderr)
        return
    if not os.path.exists(output_exe):
        print("[ERROR] El archivo .exe no se generó.")
        return

    print(f"[ÉXITO] Binario .exe generado correctamente: {output_exe}")
    print("[INFO] Puedes copiar este archivo a un entorno Windows y ejecutarlo.")



def main():
    while True:
        mostrar_menu()
        opcion = input("Seleccione una opción: ").strip()

        if opcion == "1":
            ejecutar_opcion_1()
        elif opcion == "2":
            ejecutar_opcion_2()
        elif opcion == "3":
            ejecutar_opcion_3()
        elif opcion == "4":
            ejecutar_opcion_4()
        elif opcion == "5":
            ejecutar_opcion_5()
        elif opcion == "6":
            ejecutar_opcion_6()
        elif opcion == "7":
            print("Saliendo del compilador.")
            break
        else:
            print("[ERROR] Opción no válida.")

if __name__ == "__main__":
    main()