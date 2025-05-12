import os
from pathlib import Path
from antlr4 import *
from ExprLexer import ExprLexer
from ExprParser import ExprParser
from Evaluar import Evaluador
from ast_builder import ASTBuilder
from ir_generator import LLVMGenerator
from SemanticListener import SemanticListener, SemanticError


class Interprete:
    def __init__(self):
        self.evaluador = Evaluador()
        self.historial = []
        self.programa_actual = None
        self.llvm_generator = LLVMGenerator()
        
    def _menu(self, opciones):
        print("\nMenú:")
        for key, texto in opciones.items():
            print(f"  {key}. {texto}")
        return input("Selección: ").strip()

    def ejecutar(self):
        self._limpiar_pantalla()
        self._mostrar_banner()
        
        while True:
            opcion = self._menu({
                '1': 'Nuevo programa',
                '2': 'Validar y ejecutar (semántico)',
                '3': 'Ver historial',
                '4': 'Mostrar AST',
                '5': 'Salir'
            })
            
            if opcion == '1': 
                self._nuevo_programa()
            elif opcion == '2': 
                self._ejecutar_programa()
            elif opcion == '3': 
                self._mostrar_historial()
            elif opcion == '4': 
                self._ejecutar_ast()
            elif opcion == '5': 
                break
            else: 
                self._error("Opción inválida")

    def _nuevo_programa(self):
        nombre = input("Nombre del programa: ")
        if codigo := self._leer_codigo():
            self._ejecutar_en_memoria(nombre, codigo)
            self._menu_secundario(nombre, codigo)

    def _leer_codigo(self):
        print("\nEditor (escribe 'fin' para terminar):")
        try:
            return [line for line in iter(lambda: input("» "), 'fin') if line]
        except KeyboardInterrupt:
            self._error("\nEdición cancelada")
            return None

    def _ejecutar_en_memoria(self, nombre, lineas):
        try:
            programa = f"programa {nombre}\ninicio\n" + "\n".join(lineas) + "\nfin"
            self._agregar_historial(nombre, programa)
            self.evaluador.ejecutar(InputStream(programa))
        except Exception as e:
            self._error(str(e))

    def _menu_secundario(self, nombre, codigo):
        while True:
            opcion = self._menu({
                'e': 'Editar',
                'g': 'Guardar',
                'n': 'Nuevo',
                's': 'Salir'
            })
            
            if opcion == 'e': 
                self._editar(nombre, codigo)
            elif opcion == 'g': 
                self._guardar(nombre, codigo)
            elif opcion == 'n': 
                break
            elif opcion == 's': 
                return
            else: 
                self._error("Opción inválida")

    def _editar(self, nombre, codigo):
        if nuevo_codigo := self._leer_codigo():
            self._ejecutar_en_memoria(nombre, nuevo_codigo)

    def _guardar(self, nombre, codigo):
        try:
            archivo = input("Nombre del archivo: ") + ".ea"
            Path(archivo).write_text(f"programa {nombre}\ninicio\n" + "\n".join(codigo) + "\nfin")
            print(f"Guardado en: {archivo}")
        except Exception as e:
            self._error(str(e))

    def _mostrar_historial(self):
        if not self.historial:
            print("\nNo hay programas en el historial")
            return
        
        print("\nHistorial:")
        for idx, (nombre, _) in enumerate(self.historial, 1):
            print(f"  {idx}. {nombre}")

    def _agregar_historial(self, nombre, contenido):
        self.historial.insert(0, (nombre, contenido))
        if len(self.historial) > 5: 
            self.historial.pop()

    def _limpiar_pantalla(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def _mostrar_banner(self):
        print("""
        INTERPRETE INTERMEDIO
        """)

    def _error(self, mensaje):
        print(f"[Error] {mensaje}")

    def _ejecutar_ast(self):
        ruta_codigo = input("Ruta del archivo para generar AST: ")
        try:
            if not Path(ruta_codigo).exists():
                raise FileNotFoundError(f"El archivo '{ruta_codigo}' no existe.")
            input_stream = FileStream(ruta_codigo, encoding="utf-8")
            lexer = ExprLexer(input_stream)
            tokens = CommonTokenStream(lexer)
            parser = ExprParser(tokens)
            tree = parser.prog()
            ast_builder = ASTBuilder()
            ast = ast_builder.visit(tree)
            print("Árbol de Sintaxis Abstracta (AST):")
            print(ast)
        except Exception as e:
            self._error(str(e))

    def _ejecutar_programa(self):
        ruta = input("Ruta del archivo: ")
        try:
            if not Path(ruta).exists():
                raise FileNotFoundError(f"El archivo '{ruta}' no existe.")
            
            print("Realizando análisis semántico...")
            input_stream = FileStream(ruta, encoding="utf-8")
            lexer = ExprLexer(input_stream)
            tokens = CommonTokenStream(lexer)
            parser = ExprParser(tokens)
            tree = parser.prog()

            walker = ParseTreeWalker()
            listener = SemanticListener()
            walker.walk(listener, tree)

            print("✅ Análisis semántico exitoso. Ejecutando programa...")

            self.evaluador = Evaluador(modo_panico=True)
            self.evaluador.ejecutar(ruta)
            self._agregar_historial(Path(ruta).name, Path(ruta).read_text())

        except SemanticError as e:
            self._error(str(e))
        except Exception as e:
            self._error(f"Error: {str(e)}")


if __name__ == '__main__':
    try:
        Interprete().ejecutar()
    except KeyboardInterrupt:
        print("\nEjecución interrumpida")
    except Exception as e:
        print(f"Error crítico: {str(e)}")