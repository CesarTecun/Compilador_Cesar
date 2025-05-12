# ast_builder.py

from ExprVisitor import ExprVisitor
from ExprParser import ExprParser

# Nodo base del AST
class ASTNode:
    pass

# Nodo para el programa principal
class ProgramNode(ASTNode):
    def __init__(self, name, globals, functions, block):
        self.name = name
        self.globals = globals      # Lista de nodos de declaraciones globales
        self.functions = functions  # Lista de nodos de funciones
        self.block = block          # Nodo del bloque principal

    def __repr__(self):
        return f"ProgramNode(name={self.name}, globals={self.globals}, functions={self.functions}, block={self.block})"

# Nodo para declaraciones (globales, locales o inferidas)
class DeclarationNode(ASTNode):
    def __init__(self, var_type, identifier, expr):
        self.var_type = var_type    # Tipo declarado o "inferido"
        self.identifier = identifier
        self.expr = expr            # Expresión de inicialización (puede ser None)

    def __repr__(self):
        return f"DeclarationNode({self.var_type}, {self.identifier}, {self.expr})"

# Nodo para funciones
class FunctionNode(ASTNode):
    def __init__(self, return_type, name, parameters, block):
        self.return_type = return_type
        self.name = name
        self.parameters = parameters  # Lista de ParameterNode
        self.block = block            # Bloque de la función (BlockNode)

    def __repr__(self):
        return f"FunctionNode({self.return_type}, {self.name}, parameters={self.parameters}, block={self.block})"

# Nodo para parámetros de función
class ParameterNode(ASTNode):
    def __init__(self, var_type, identifier):
        self.var_type = var_type
        self.identifier = identifier

    def __repr__(self):
        return f"ParameterNode({self.var_type}, {self.identifier})"

# Nodo para bloques (lista de sentencias)
class BlockNode(ASTNode):
    def __init__(self, statements):
        self.statements = statements  # Lista de nodos de sentencias

    def __repr__(self):
        return f"BlockNode({self.statements})"

# Nodo para la sentencia if (condicional)
class IfNode(ASTNode):
    def __init__(self, condition, then_stmt, else_stmt):
        self.condition = condition
        self.then_stmt = then_stmt
        self.else_stmt = else_stmt

    def __repr__(self):
        return f"IfNode(condition={self.condition}, then={self.then_stmt}, else={self.else_stmt})"

# Nodo para la sentencia for
class ForNode(ASTNode):
    def __init__(self, init, condition, update, body):
        self.init = init
        self.condition = condition
        self.update = update
        self.body = body

    def __repr__(self):
        return f"ForNode(init={self.init}, condition={self.condition}, update={self.update}, body={self.body})"

# Nodo para la sentencia while
class WhileNode(ASTNode):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def __repr__(self):
        return f"WhileNode(condition={self.condition}, body={self.body})"

# Nodo para la sentencia do-while
class DoWhileNode(ASTNode):
    def __init__(self, body, condition):
        self.body = body
        self.condition = condition

    def __repr__(self):
        return f"DoWhileNode(body={self.body}, condition={self.condition})"

# Nodo para la sentencia return
class ReturnNode(ASTNode):
    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        return f"ReturnNode({self.expr})"

# Nodo para la sentencia de imprimir (pintar)
class PrintNode(ASTNode):
    def __init__(self, args):
        self.args = args  # Lista de expresiones

    def __repr__(self):
        return f"PrintNode({self.args})"

# Nodo para operaciones binarias
class BinaryOpNode(ASTNode):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op      # Operador (por ejemplo, '+', '-', '*', '/', '==', etc.)
        self.right = right

    def __repr__(self):
        return f"BinaryOpNode({self.left} {self.op} {self.right})"

# Nodo para operaciones unarias
class UnaryOpNode(ASTNode):
    def __init__(self, op, operand):
        self.op = op      # Operador unario (por ejemplo, '!', '+', '-')
        self.operand = operand

    def __repr__(self):
        return f"UnaryOpNode({self.op} {self.operand})"

# Nodo para números
class NumberNode(ASTNode):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"NumberNode({self.value})"

# Nodo para booleanos
class BooleanNode(ASTNode):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"BooleanNode({self.value})"

# Nodo para cadenas de texto
class StringNode(ASTNode):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"StringNode({self.value})"

# Nodo para variables
class VariableNode(ASTNode):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"VariableNode({self.name})"

# Nodo para asignaciones
class AssignmentNode(ASTNode):
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr

    def __repr__(self):
        return f"AssignmentNode({self.name} = {self.expr})"

# Nodo para llamadas a función
class FunctionCallNode(ASTNode):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def __repr__(self):
        return f"FunctionCallNode({self.name}, args={self.args})"

# Visitor para construir el AST
class ASTBuilder(ExprVisitor):
    def visitProg(self, ctx: ExprParser.ProgContext):
        name = ctx.ID().getText()
        globals_list = []
        functions = []
        block = None
        # Procesar solo los hijos que sean nodos de regla (no terminales)
        for child in ctx.children:
            if not hasattr(child, "getRuleIndex"):
                continue  # Saltar nodos terminales
            rule_index = child.getRuleIndex()
            if rule_index == ExprParser.RULE_declaracion_global:
                globals_list.append(self.visit(child))
            elif rule_index == ExprParser.RULE_funciones:
                functions = self.visit(child)
            elif rule_index == ExprParser.RULE_bloque_programa:
                block = self.visit(child)
        return ProgramNode(name, globals_list, functions, block)

    def visitDeclaracionGlobalSimple(self, ctx: ExprParser.DeclaracionGlobalSimpleContext):
        var_type = ctx.tipo().getText().lower()
        identifier = ctx.ID().getText()
        expr = self.visit(ctx.expr()) if ctx.expr() else None
        return DeclarationNode(var_type, identifier, expr)

    def visitDeclaracionSimple(self, ctx: ExprParser.DeclaracionSimpleContext):
        var_type = ctx.tipo().getText().lower()
        identifier = ctx.ID().getText()
        expr = self.visit(ctx.expr()) if ctx.expr() else None
        return DeclarationNode(var_type, identifier, expr)

    def visitDeclaracionInferida(self, ctx: ExprParser.DeclaracionInferidaContext):
        # En declaraciones inferidas, el tipo se determina en tiempo de ejecución
        identifier = ctx.ID().getText()
        expr = self.visit(ctx.expr()) if ctx.expr() else None
        return DeclarationNode("inferido", identifier, expr)

    def visitBloque_programa(self, ctx: ExprParser.Bloque_programaContext):
        return self.visit(ctx.bloque())

    def visitBloque(self, ctx: ExprParser.BloqueContext):
        statements = []
        for stmt in ctx.sentencia():
            node = self.visit(stmt)
            if node is not None:
                statements.append(node)
        return BlockNode(statements)

    def visitFunciones(self, ctx: ExprParser.FuncionesContext):
        functions = []
        for f in ctx.funcion():
            functions.append(self.visit(f))
        return functions

    def visitFuncionDef(self, ctx: ExprParser.FuncionDefContext):
        return_type = ctx.tipo().getText().lower() if ctx.tipo() else "void"
        name = ctx.ID().getText()
        parameters = []
        if ctx.params():
            try:
                params_list = ctx.params().param()
                if params_list:
                    for param in params_list:
                        param_type = param.tipo().getText().lower()
                        param_name = param.ID().getText()
                        parameters.append(ParameterNode(param_type, param_name))
            except AttributeError:
                # Sin parámetros explícitos
                pass
        block = self.visit(ctx.bloque())
        return FunctionNode(return_type, name, parameters, block)


    def visitPintarSentencia(self, ctx: ExprParser.PintarSentenciaContext):
        args = self.visit(ctx.args()) if ctx.args() else []
        return PrintNode(args)


    def visitSiSentencia(self, ctx: ExprParser.SiSentenciaContext):
        condition = self.visit(ctx.expr())
        then_stmt = self.visit(ctx.sentencia(0))
        else_stmt = self.visit(ctx.sentencia(1)) if ctx.SINO() else None
        return IfNode(condition, then_stmt, else_stmt)

    def visitMientrasSentencia(self, ctx: ExprParser.MientrasSentenciaContext):
        condition = self.visit(ctx.expr())
        body = self.visit(ctx.sentencia())
        return WhileNode(condition, body)

    def visitHacerMientrasSentencia(self, ctx: ExprParser.HacerMientrasSentenciaContext):
        body = self.visit(ctx.sentencia())
        condition = self.visit(ctx.expr())
        return DoWhileNode(body, condition)

    def visitRetornarSentencia(self, ctx: ExprParser.RetornarSentenciaContext):
        expr = self.visit(ctx.expr()) if ctx.expr() else None
        return ReturnNode(expr)

    def visitParaSentencia(self, ctx: ExprParser.ParaSentenciaContext):
        init = None
        if ctx.declaracion():
            init = self.visit(ctx.declaracion())
        elif ctx.expr(0):
            init = self.visit(ctx.expr(0))
        condition = self.visit(ctx.expr(1)) if ctx.expr(1) else None
        update = self.visit(ctx.expr(2)) if ctx.expr(2) else None
        body = self.visit(ctx.sentencia())
        return ForNode(init, condition, update, body)

    def visitAsignacionExp(self, ctx: ExprParser.AsignacionExpContext):
        name = ctx.ID().getText()
        expr = self.visit(ctx.asignacion())
        return AssignmentNode(name, expr)

    # Expresiones binarias y unarias

    def visitOpLogicaOR(self, ctx: ExprParser.OpLogicaORContext):
        left = self.visit(ctx.logicaOr())
        right = self.visit(ctx.logicaAnd())
        return BinaryOpNode(left, '||', right)

    def visitOpLogicaAND(self, ctx: ExprParser.OpLogicaANDContext):
        left = self.visit(ctx.logicaAnd())
        right = self.visit(ctx.igualdad())
        return BinaryOpNode(left, '&&', right)

    def visitOpIgualdadDiferencia(self, ctx: ExprParser.OpIgualdadDiferenciaContext):
        left = self.visit(ctx.igualdad())
        right = self.visit(ctx.comparacion())
        op = ctx.getChild(1).getText()
        return BinaryOpNode(left, op, right)

    def visitOpComparacion(self, ctx: ExprParser.OpComparacionContext):
        left = self.visit(ctx.comparacion())
        right = self.visit(ctx.suma())
        op = ctx.getChild(1).getText()
        return BinaryOpNode(left, op, right)

    def visitOpSumaResta(self, ctx: ExprParser.OpSumaRestaContext):
        left = self.visit(ctx.suma())
        right = self.visit(ctx.mult())
        op = ctx.getChild(1).getText()
        return BinaryOpNode(left, op, right)

    def visitOpMultDiv(self, ctx: ExprParser.OpMultDivContext):
        left = self.visit(ctx.mult())
        right = self.visit(ctx.potencia())
        op = ctx.getChild(1).getText()
        return BinaryOpNode(left, op, right)

    def visitOpPotencia(self, ctx: ExprParser.OpPotenciaContext):
        left = self.visit(ctx.unario())
        right = self.visit(ctx.potencia())
        return BinaryOpNode(left, '^', right)

    def visitOpUnarioNot(self, ctx: ExprParser.OpUnarioNotContext):
        operand = self.visit(ctx.unario())
        return UnaryOpNode('!', operand)

    def visitOpUnarioPositivo(self, ctx: ExprParser.OpUnarioPositivoContext):
        operand = self.visit(ctx.unario())
        return UnaryOpNode('+', operand)

    def visitOpUnarioNegativo(self, ctx: ExprParser.OpUnarioNegativoContext):
        operand = self.visit(ctx.unario())
        return UnaryOpNode('-', operand)

    def visitLlamadaUnaria(self, ctx: ExprParser.LlamadaUnariaContext):
        return self.visit(ctx.llamada())

    def visitParentesis(self, ctx: ExprParser.ParentesisContext):
        return self.visit(ctx.expr())

    def visitNumero(self, ctx: ExprParser.NumeroContext):
        text = ctx.NUMERO().getText()
        value = float(text) if '.' in text else int(text)
        return NumberNode(value)

    def visitBooleano(self, ctx: ExprParser.BooleanoContext):
        value = ctx.BOOL_LIT().getText() == 'verdad'
        return BooleanNode(value)

    def visitTexto(self, ctx: ExprParser.TextoContext):
        text = ctx.TEXTO().getText()[1:-1]
        return StringNode(text)

    def visitVariable(self, ctx: ExprParser.VariableContext):
        return VariableNode(ctx.ID().getText())

    def visitLlamadaFuncion(self, ctx: ExprParser.LlamadaFuncionContext):
        # Si no hay paréntesis, entonces es solo una expresión base
        if ctx.getChildCount() == 1:
            return self.visit(ctx.primary())

        # Es una llamada a función
        primary = ctx.primary()
        name = primary.ID().getText() if hasattr(primary, "ID") and primary.ID() else self.visit(primary)

        args = []
        for i in range(len(ctx.PAR_IZQ())):
            arg_ctx = ctx.args(i)
            if arg_ctx:
                args += self.visitArgumentos(arg_ctx)

        return FunctionCallNode(name, args)

    def visitArgumentos(self, ctx: ExprParser.ArgumentosContext):
        return [self.visit(expr) for expr in ctx.expr()]


    def visitExprSentencia(self, ctx: ExprParser.ExprSentenciaContext):
        # Simplemente retorna el nodo generado a partir de la expresión.
        return self.visit(ctx.expr())

# Fin del módulo ast_builder.py