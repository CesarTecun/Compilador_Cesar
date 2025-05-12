from antlr4 import *
from ExprParser import ExprParser
from ExprListener import ExprListener
from collections import deque

class SemanticError(Exception):
    pass

#TABLA DE SIMBOLOS VARIABLES Y FUNCIONES
class Scope:
    def __init__(self):
        self.variables = {}  # name -> { tipo, "usadas": False}
        self.functions = {}

#MANEJO DE LA SEMANTICA DE FUNCIONES ERRORES TIPOS FUNCIONES.
class SemanticListener(ExprListener):
    def __init__(self):
        self.scopes = deque([Scope()])
        self.current_function_return_type = None
        self.errors = []
        self.warnings = []
        self.called_functions = set() #name funciones
        self.has_return = True


    #CONTROL DE AMBITOS MANEJO DE PILA SCOPES
    def enterBloque(self, ctx: ExprParser.BloqueContext):
        self.scopes.append(Scope())

    def exitBloque(self, ctx: ExprParser.BloqueContext):
        scope = self.scopes.pop()



        # Advertencia por variables no usadas
        for name, meta in scope.variables.items():
            msg_ctx = meta.get("ctx", ctx)  # usar contexto de declaración si está
            if not meta.get("read", False) and not meta.get("assigned", False):
                self._warn(msg_ctx, f"Variable '{name}' fue declarada pero nunca utilizada.")
            elif meta.get("assigned", False) and not meta.get("read", False):
                self._warn(msg_ctx, f"Variable '{name}' fue asignada pero nunca leída.")

        # Si estamos saliendo del bloque global (es el primero en salir)
        if len(self.scopes) == 0:
            for name in scope.functions:
                if name not in self.called_functions:
                    self._warn(ctx, f"Función '{name}' fue definida pero nunca llamada.")
    

    def _has_guaranteed_return(self, ctx):
        """
        Verifica si un bloque o sentencia garantiza retorno en todos los caminos.
        """
        if ctx is None:
            return False

        # Caso 1: bloque con varias sentencias
        if hasattr(ctx, "sentencia"):
            for stmt in ctx.sentencia():
                if self._has_guaranteed_return(stmt):
                    return True
            return False

        # Caso 2: retorno directo
        if isinstance(ctx, ExprParser.RetornarSentenciaContext):
            return True

        # Caso 3: si-sino con retorno en ambas ramas
        if isinstance(ctx, ExprParser.SiSentenciaContext):
            then_stmt = ctx.sentencia(0)
            else_stmt = ctx.sentencia(1) if ctx.getChildCount() > 5 else None  # puede no tener sino

            then_ret = self._has_guaranteed_return(then_stmt)
            else_ret = self._has_guaranteed_return(else_stmt) if else_stmt else False

            return then_ret and else_ret

        # Otras sentencias no garantizan retorno
        return False



    #Funcion para detectar distintos caracteres en funciones
    #LLamar a las funciones
    def _check_function_call(self, ctx, name, args):
        # Verifica si la función existe
        for scope in reversed(self.scopes):
            if name in scope.functions:
                return_type, expected_params = scope.functions[name]
                break
        else:
            self._error(ctx, f"Función '{name}' no definida.")
            return "entero"

        # Verifica número de argumentos
        if len(args) != len(expected_params):
            self._error(ctx, f"La función '{name}' espera {len(expected_params)} argumento(s), pero se proporcionaron {len(args)}.")
            return return_type

        # Verifica tipo de cada argumento
        for i, (arg_expr, (param_name, expected_type)) in enumerate(zip(args, expected_params)):
            actual_type = self._infer_expr_type(arg_expr)
            if actual_type != expected_type:
                self._error(arg_expr, f"Tipo incorrecto para el argumento {i+1} en llamada a '{name}': se esperaba '{expected_type}', pero se recibió '{actual_type}'.")

        return return_type

    #CONTROL DE TIPO Y AMBITO PARA LA REDIFINICION
    #declaracion de funciones
    def enterFuncionDef(self, ctx: ExprParser.FuncionDefContext):
        self.has_return = False  # ← asumimos que no hay retorno aún
        scope = self.scopes[-1]
        name = ctx.ID().getText()
        return_type = ctx.tipo().getText().lower() if ctx.tipo() else "void"

        if name in scope.functions:
            self._error(ctx, f"Función '{name}' ya fue definida.")

        params = []
        if ctx.params() and hasattr(ctx.params(), "param"):
            param_list = ctx.params().param()
            for p in param_list:
                tipo = p.tipo().getText().lower()
                ident = p.ID().getText()
                params.append((ident, tipo))

        scope.functions[name] = (return_type, params)
        self.current_function_return_type = return_type
        self.scopes.append(Scope())
        for ident, tipo in params:
            self._declare_variable(ctx, ident, tipo)



    def exitDeclaracionGlobalSimple(self, ctx: ExprParser.DeclaracionGlobalSimpleContext):
        tipo = ctx.tipo().getText().lower()
        ident = ctx.ID().getText()
        self._declare_variable(ctx, ident, tipo)


    #DECLARACION CON TIPO EXPLICITO
    def exitDeclaracionSimple(self, ctx: ExprParser.DeclaracionSimpleContext):
        tipo = ctx.tipo().getText().lower()  # Tipo de la variable
        ident = ctx.ID().getText()  # Nombre de la variable
        expr_type = self._infer_expr_type(ctx.expr()) if ctx.expr() else None  # Tipo de la expresión asignada, si existe

        # Verificación de tipo incompatible
        if expr_type and tipo != expr_type:
            self._error(ctx, f"Tipo incompatible en inicialización de '{ident}': declarado '{tipo}', pero la expresión es '{expr_type}'.")

        # Verificar si la declaración termina con un punto y coma
        declaration_text = ctx.getText().strip()  # Obtener el texto completo de la declaración
        if not declaration_text.endswith(";"):
            self._error(ctx, f"Falta el punto y coma ';' al final de la declaración de '{ident}'.")

        # Declarar la variable después de la verificación
        self._declare_variable(ctx, ident, tipo)

        # Si hay inicialización, marcarla como asignada
        if ctx.expr():  # Si hay inicialización
            for scope in reversed(self.scopes):
                if ident in scope.variables:
                    scope.variables[ident]["assigned"] = True
                    break

    def exitDeclaracionInferida(self, ctx: ExprParser.DeclaracionInferidaContext):
        ident = ctx.ID().getText()
        tipo = self._infer_expr_type(ctx.expr())
        self._declare_variable(ctx, ident, tipo)


    #ASIGNACIONES
    def exitAsignacionExp(self, ctx: ExprParser.AsignacionExpContext):
        name = ctx.ID().getText()
        expr_type = self._infer_expr_type(ctx.asignacion())
        var_type = self._resolve_variable_type(ctx, name)

        if var_type != expr_type:
            self._error(ctx, f"Tipo incompatible en asignación a '{name}': esperado '{var_type}', encontrado '{expr_type}'.")

        # Marcar que fue asignada (independientemente del tipo)
        for scope in reversed(self.scopes):
            if name in scope.variables:
                scope.variables[name]["assigned"] = True
                break

    def exitPintarSentencia(self, ctx: ExprParser.PintarSentenciaContext):
        # Procesar las expresiones dentro de la sentencia
        if ctx.args():
            for expr in ctx.args().expr():
                self._infer_expr_type(expr)

        # Verificar si la sentencia termina con un punto y coma
        # Aquí verificamos que la sentencia completa de 'pintar' termine con ';'
        sentencia_text = ctx.getText().strip()  # Obtener el texto de la sentencia
        if not sentencia_text.endswith(";"):
            self._error(ctx, "Falta el punto y coma ';' al final de la sentencia 'pintar'.")

    #RETORNOS DE FUNCIONES
    def exitRetornarSentencia(self, ctx: ExprParser.RetornarSentenciaContext):
        self.has_return = True
        if self.current_function_return_type is None:
            self._error(ctx, "Sentencia 'ret' fuera de una función.")
        expr_type = self._infer_expr_type(ctx.expr()) if ctx.expr() else "void"
        if expr_type != self.current_function_return_type:
            self._error(
                ctx,
                f"Tipo de retorno incorrecto: se esperaba '{self.current_function_return_type}', pero se retornó '{expr_type}'."
            )

    # ========================
    # MÉTODOS AUXILIARES
    # ========================

    #Declaracion de variables en el scope actual
    #Aqui utilizamos la tabla en las declaraciones
    def _declare_variable(self, ctx, name, tipo):
        current_scope = self.scopes[-1]

        # Error si ya fue declarada en el mismo ámbito
        if name in current_scope.variables:
            self._error(ctx, f"Variable '{name}' ya fue declarada en este ámbito.")

        # Advertencia si está declarada en un scope exterior (sombreado)
        for scope in list(self.scopes)[:-1]:  # revisa scopes exteriores
            if name in scope.variables:
                self._warn(ctx, f"Variable '{name}' en este bloque oculta una declaración anterior en un ámbito externo.")
                break

        # Registrar la nueva variable
        current_scope.variables[name] = {
            "type": tipo,
            "assigned": False,
            "read": False,
            "ctx": ctx
        }

    #RESOLUCION DE LAS VARIABLES
    #lectura o validacion
    def _resolve_variable_type(self, ctx, name):
        for scope in reversed(self.scopes):
            if name in scope.variables:
                scope.variables[name]["read"] = True
                return scope.variables[name]["type"]
        self._error(ctx, f"Variable '{name}' no declarada.")
        return "entero"



    def _infer_expr_type(self, ctx):
        if ctx is None:
            return "void"

        if hasattr(ctx, "NUMERO") and ctx.NUMERO():
            text = ctx.NUMERO().getText()
            return "decimal" if '.' in text else "entero"

        if hasattr(ctx, "BOOL_LIT") and ctx.BOOL_LIT():
            return "bool"

        if hasattr(ctx, "TEXTO") and ctx.TEXTO():
            return "cadena"

        if hasattr(ctx, "ID") and ctx.ID():
            return self._resolve_variable_type(ctx, ctx.ID().getText())

        if hasattr(ctx, "expr") and callable(ctx.expr):
            return self._infer_expr_type(ctx.expr())

        if hasattr(ctx, "unario"):
            return self._infer_expr_type(ctx.unario())

        if ctx.getChildCount() == 3:
            op = ctx.getChild(1).getText()
            tipo_izq = self._infer_expr_type(ctx.getChild(0))
            tipo_der = self._infer_expr_type(ctx.getChild(2))

            if op in ["==", "!=", "<", ">", "<=", ">="]:
                return "bool"
            if op == "+" and tipo_izq == "cadena" and tipo_der == "cadena":
                return "cadena"
            if "decimal" in [tipo_izq, tipo_der]:
                return "decimal"
            return "entero"

        if ctx.getChildCount() == 1:
            return self._infer_expr_type(ctx.getChild(0))
        
        # Si es llamada a función con o sin argumentos
        if ctx.getChildCount() >= 3 and ctx.getChild(1).getText() == '(':
            # Obtener nombre de función
            if hasattr(ctx.getChild(0), "getText"):
                name = ctx.getChild(0).getText()
            else:
                return "entero"  # fallback

            # Obtener lista de argumentos
            arg_node = ctx.getChild(2)
            args = arg_node.expr() if hasattr(arg_node, "expr") else []
            self.called_functions.add(name)
            return self._check_function_call(ctx, name, args)


        # Si es llamada a función sin argumentos
        if hasattr(ctx, "primary") and ctx.primary().ID():
            return self._infer_function_return_type(ctx)
        
        return "entero"
    



    def _infer_function_return_type(self, ctx):
        if hasattr(ctx, "primary") and ctx.primary().ID():
            name = ctx.primary().ID().getText()
            self.called_functions.add(name)  # ← marcar como llamada

        else:
            return "entero"

        for scope in reversed(self.scopes):
            if name in scope.functions:
                return scope.functions[name][0]
        self._error(ctx, f"Función '{name}' no definida.")
        return "entero"

    def _error(self, ctx, msg):
        line = ctx.start.line if ctx.start else "desconocida"
        self.errors.append(f"[Línea {line}] Error semántico: {msg}")

    def _warn(self, ctx, msg):
        line = ctx.start.line if ctx.start else "desconocida"
        self.warnings.append(f"[Línea {line}] Advertencia: {msg}")