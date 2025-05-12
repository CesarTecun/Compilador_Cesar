#ARCHIVO GENERADOR DE IR EN BASE A NUESTRO AST
from llvmlite import ir
import llvmlite.binding as llvm
from ast_builder import *
from llvmlite.ir._utils import DuplicatedNameError 


from ast_builder import (
    ASTNode,
    ProgramNode,
    DeclarationNode,
    FunctionNode,
    ParameterNode,
    BlockNode,
    IfNode,
    ForNode,
    WhileNode,
    DoWhileNode,
    ReturnNode,
    PrintNode,
    BinaryOpNode,
    UnaryOpNode,
    NumberNode,
    BooleanNode,
    StringNode,
    VariableNode,
    AssignmentNode,
    FunctionCallNode,
    ASTBuilder
)

class LLVMGenerator:
    def __init__(self, for_windows_exe=False):
        # Inicializar LLVM
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()
        self.for_windows_exe = for_windows_exe  # Bandera para EXE
        
        # Crear módulo para almacenar
        self.module = ir.Module(name="mi_programa")
        self.module.triple = "x86_64-pc-linux-gnu" #para linux 64bits
        self.builder = None
        self.symbol_tables = [{}]  # Pila de tablas de símbolos
        self.functions = {}
        self.current_function = None
        
        # Configurar tipos
        self.llvm_types = {
            'entero': ir.IntType(32),
            'decimal': ir.DoubleType(),
            'bool': ir.IntType(1),
            'cadena': ir.PointerType(ir.IntType(8)),
            'void': ir.VoidType()
        }
        
        # Configurar funciones built-in
        self._setup_builtins()
    
    def _setup_builtins(self):
        # printf para soportar pintar()
        printf_type = ir.FunctionType(
            ir.IntType(32), 
            [ir.PointerType(ir.IntType(8))], 
            var_arg=True
        )
        ir.Function(self.module, printf_type, "printf")
        self.concat_func = define_concat_function(self.module, self.llvm_types)
        
        # Declarar getchar para la pausa final (AGREGADO)
        getchar_type = ir.FunctionType(ir.IntType(32), [])
        ir.Function(self.module, getchar_type, name="getchar")
    
    def generate(self, ast_node):
        """Genera código LLVM a partir del AST"""
        if isinstance(ast_node, ProgramNode):
            self._generate_program(ast_node)
        return self.module
    
    def _generate_program(self, program_node):
        # 1. Procesar declaraciones globales
        for decl in program_node.globals:
            self._generate_declaration(decl, is_global=True)
        
        # 2. Procesar funciones
        for func in program_node.functions:
            self._generate_function(func)
        
        # 3. Generar función main
        self._generate_main_function(program_node.block)
    
    def _generate_main_function(self, block_node):
        """Genera la función main que encapsula el programa"""
        func_type = ir.FunctionType(ir.IntType(32), [])
        function = ir.Function(self.module, func_type, name="main")
        entry_block = function.append_basic_block(name="entry")
        
        # Configurar builder y contexto
        old_builder = self.builder
        self.builder = ir.IRBuilder(entry_block)
        self.current_function = function
        
        # Generar código del bloque principal
        self._generate_block(block_node)
        
        # Asegurar retorno (con pausa condicional)
        if not self.builder.block.terminator:
            if self.for_windows_exe:  # Solo para compilación a EXE
                getchar_func = self.module.get_global("getchar")
                self.builder.call(getchar_func, [])
            self.builder.ret(ir.Constant(ir.IntType(32), 0))
        
        # Restaurar contexto
        self.builder = old_builder
        self.current_function = None
    
    def _generate_function(self, func_node):
        """Genera código para una función definida por el usuario"""
        # Determinar tipos
        return_type = self.llvm_types[func_node.return_type]
        param_types = [self.llvm_types[p.var_type] for p in func_node.parameters]
        
        # Crear función
        func_type = ir.FunctionType(return_type, param_types)
        function = ir.Function(self.module, func_type, name=func_node.name)
        self.functions[func_node.name] = function
        
        # Crear bloques
        entry_block = function.append_basic_block(name="entry")
        
        # Guardar contexto actual
        old_builder = self.builder
        old_function = self.current_function
        
        # Configurar nuevo contexto
        self.builder = ir.IRBuilder(entry_block)
        self.current_function = function
        self.symbol_tables.append({})
        
        # Asignar parámetros
        for i, arg in enumerate(function.args):
            arg_name = func_node.parameters[i].identifier
            alloca = self.builder.alloca(arg.type, name=arg_name)
            self.builder.store(arg, alloca)
            self.symbol_tables[-1][arg_name] = alloca
        
        # Generar cuerpo
        self._generate_block(func_node.block)
        
        # Asegurar retorno si falta
        if not self.builder.block.terminator:
            if func_node.return_type == 'void':
                self.builder.ret_void()
            else:
                self.builder.unreachable()
        
        # Restaurar contexto
        self.builder = old_builder
        self.current_function = old_function
        self.symbol_tables.pop()
    
    def _generate_block(self, block_node):
        """Genera código para un bloque de sentencias"""
        for stmt in block_node.statements:
            self._generate_statement(stmt)
    
    def _generate_statement(self, stmt_node):
        """Distribuye la generación según el tipo de sentencia"""
        if isinstance(stmt_node, DeclarationNode):
            self._generate_declaration(stmt_node)
        elif isinstance(stmt_node, AssignmentNode):
            self._generate_assignment(stmt_node)
        elif isinstance(stmt_node, PrintNode):
            self._generate_print(stmt_node)
        elif isinstance(stmt_node, IfNode):
            self._generate_if(stmt_node)
        elif isinstance(stmt_node, WhileNode):
            self._generate_while(stmt_node)
        elif isinstance(stmt_node, DoWhileNode):
            self._generate_do_while(stmt_node)
        elif isinstance(stmt_node, ForNode):
            self._generate_for(stmt_node)
        elif isinstance(stmt_node, ReturnNode):
            self._generate_return(stmt_node)
        elif isinstance(stmt_node, FunctionCallNode):
            self._generate_function_call(stmt_node)
        elif isinstance(stmt_node, BlockNode):
            self._generate_block(stmt_node)
    
    def _generate_declaration(self, decl_node, is_global=False):
        var_name = decl_node.identifier
        var_type = decl_node.var_type

        # Genera la expresión (para obtener valor y tipo real)
        expr_value = self._generate_expression(decl_node.expr)

        # Inferir tipo si es necesario
        if var_type in ("inferido", "auto"):
            llvm_type = expr_value.type  # Usa directamente el tipo LLVM inferido
        else:
            llvm_type = self.llvm_types.get(var_type, ir.IntType(32))

            # Asegurar compatibilidad de tipos (casting simple si es necesario)
            expr_value = self._cast_value(expr_value, llvm_type)

        if is_global:
            global_var = ir.GlobalVariable(self.module, llvm_type, var_name)
            global_var.initializer = expr_value
            self.symbol_tables[0][var_name] = global_var
        else:
            alloca = self.builder.alloca(llvm_type, name=var_name)
            self.symbol_tables[-1][var_name] = alloca
            self.builder.store(expr_value, alloca)

            
    def _cast_value(self, value, target_type):
        if value.type == target_type:
            return value

        if isinstance(value.type, ir.IntType) and isinstance(target_type, ir.DoubleType):
            return self.builder.sitofp(value, target_type)

        if isinstance(value.type, ir.DoubleType) and isinstance(target_type, ir.IntType):
            return self.builder.fptosi(value, target_type)

        if isinstance(value.type, ir.IntType) and isinstance(target_type, ir.PointerType):
            raise TypeError("Cannot cast integer to pointer directly.")

        if isinstance(value.type, ir.PointerType) and isinstance(target_type, ir.PointerType):
            return self.builder.bitcast(value, target_type)

        raise TypeError(f"No suitable cast from {value.type} to {target_type}")


    
    def _generate_assignment(self, assign_node):
        """Genera código para asignación de variables"""
        var_name = assign_node.name
        ptr = self._lookup_variable(var_name)
        value = self._generate_expression(assign_node.expr)
        self.builder.store(value, ptr)
    
    def _generate_print(self, print_node):
        """Genera código para la función pintar()"""
        printf = self.module.get_global("printf")
        format_parts = []
        values = []

        for arg in print_node.args:
            value = self._generate_expression(arg)
            llvm_type = value.type

            if isinstance(llvm_type, ir.PointerType) and llvm_type.pointee == ir.IntType(8):
                format_parts.append("%s")
            elif isinstance(llvm_type, ir.DoubleType):
                format_parts.append("%f")
            elif isinstance(llvm_type, ir.IntType):
                format_parts.append("%d")
                if llvm_type.width == 1:
                    value = self.builder.zext(value, ir.IntType(32))
                elif llvm_type.width != 32:
                    value = self.builder.sext(value, ir.IntType(32))
            else:
                raise RuntimeError(f"Tipo no soportado para imprimir: {llvm_type}")

            values.append(value)

        format_str = " ".join(format_parts) + "\n\0"
        fmt_name = ".fmt." + str(hash(format_str))
        fmt_type = ir.ArrayType(ir.IntType(8), len(format_str))

        if fmt_name in self.module.globals:
            fmt_global = self.module.get_global(fmt_name)
        else:
            fmt_global = ir.GlobalVariable(self.module, fmt_type, name=fmt_name)
            fmt_global.linkage = 'internal'
            fmt_global.global_constant = True
            fmt_global.initializer = ir.Constant(fmt_type, bytearray(format_str.encode('utf-8')))

        fmt_ptr = self.builder.bitcast(fmt_global, ir.PointerType(ir.IntType(8)))
        self.builder.call(printf, [fmt_ptr] + values)




    
    def _generate_if(self, if_node):
        """Genera código para la estructura if-else"""
        cond = self._generate_expression(if_node.condition)

        then_block = self.current_function.append_basic_block("if.then")
        else_block = self.current_function.append_basic_block("if.else") if if_node.else_stmt else None
        merge_block = self.current_function.append_basic_block("if.merge")

        bool_cond = self._convert_to_bool(cond)

        # Redirige a then o else (o merge si no hay else)
        if else_block:
            self.builder.cbranch(bool_cond, then_block, else_block)
        else:
            self.builder.cbranch(bool_cond, then_block, merge_block)

        # THEN
        self.builder.position_at_end(then_block)
        self._generate_statement(if_node.then_stmt)
        then_has_terminator = self.builder.block.terminator is not None
        if not then_has_terminator:
            self.builder.branch(merge_block)

        # ELSE (si existe)
        if else_block:
            self.builder.position_at_end(else_block)
            self._generate_statement(if_node.else_stmt)
            else_has_terminator = self.builder.block.terminator is not None
            if not else_has_terminator:
                self.builder.branch(merge_block)
        else:
            else_has_terminator = False  # No hay bloque else

        # MERGE
        # Solo posicionarse en el merge si alguno de los dos bloques llega ahí
        if not then_has_terminator or not else_has_terminator:
            self.builder.position_at_end(merge_block)
        else:
            # ⚠️ Elimina el bloque merge si no será usado
            # (Evita que aparezca como bloque vacío en el IR)
            self.current_function.basic_blocks.remove(merge_block)

    
    def _generate_while(self, while_node):
        """Genera código para la estructura while"""
        # Crear bloques
        test_block = self.current_function.append_basic_block("while.test")
        body_block = self.current_function.append_basic_block("while.body")
        end_block = self.current_function.append_basic_block("while.end")
        
        # Saltar al bloque de test
        self.builder.branch(test_block)
        
        # Generar test
        self.builder.position_at_end(test_block)
        cond = self._generate_expression(while_node.condition)
        bool_cond = self._convert_to_bool(cond)
        self.builder.cbranch(bool_cond, body_block, end_block)
        
        # Generar cuerpo
        self.builder.position_at_end(body_block)
        self._generate_statement(while_node.body)
        if not self.builder.block.terminator:
            self.builder.branch(test_block)
        
        # Continuar con el end block
        self.builder.position_at_end(end_block)
    
    def _generate_do_while(self, do_while_node):
        """Genera código para la estructura do-while"""
        # Crear bloques
        body_block = self.current_function.append_basic_block("do.body")
        test_block = self.current_function.append_basic_block("do.test")
        end_block = self.current_function.append_basic_block("do.end")
        
        # Saltar al cuerpo
        self.builder.branch(body_block)
        
        # Generar cuerpo
        self.builder.position_at_end(body_block)
        self._generate_statement(do_while_node.body)
        if not self.builder.block.terminator:
            self.builder.branch(test_block)
        
        # Generar test
        self.builder.position_at_end(test_block)
        cond = self._generate_expression(do_while_node.condition)
        bool_cond = self._convert_to_bool(cond)
        self.builder.cbranch(bool_cond, body_block, end_block)
        
        # Continuar con el end block
        self.builder.position_at_end(end_block)
    
    def _generate_for(self, for_node):
        """Genera código para la estructura for"""
        # Crear bloques para cada parte del for
        init_block = self.current_function.append_basic_block("for.init")
        test_block = self.current_function.append_basic_block("for.test")
        body_block = self.current_function.append_basic_block("for.body")
        update_block = self.current_function.append_basic_block("for.update")
        end_block = self.current_function.append_basic_block("for.end")
        
        # Desde el bloque actual, saltar al bloque de inicialización
        self.builder.branch(init_block)
        
        # Generar inicialización en init_block (puede ser una declaración o una expresión)
        self.builder.position_at_end(init_block)
        if for_node.init:
            self._generate_statement(for_node.init)
        # Finalizar el bloque init con un salto hacia el bloque de test
        self.builder.branch(test_block)
        
        # Generar el bloque de test: evaluar la condición (si existe)
        self.builder.position_at_end(test_block)
        if for_node.condition:
            cond = self._generate_expression(for_node.condition)
            bool_cond = self._convert_to_bool(cond)
            self.builder.cbranch(bool_cond, body_block, end_block)
        else:
            # Si no hay condición, se asume que es verdadera y se salta al cuerpo
            self.builder.branch(body_block)
        
        # Generar el cuerpo del for
        self.builder.position_at_end(body_block)
        self._generate_statement(for_node.body)
        # Si el cuerpo no termina con una instrucción terminadora, saltar a la actualización
        if not self.builder.block.terminator:
            self.builder.branch(update_block)
        
        # Generar el bloque de actualización
        self.builder.position_at_end(update_block)
        if for_node.update:
            self._generate_statement(for_node.update)
        # Después de la actualización, volver al bloque de test para re-evaluar la condición
        self.builder.branch(test_block)
        
        # Posicionar al builder en el bloque final para continuar el resto del código
        self.builder.position_at_end(end_block)


    
    def _generate_return(self, return_node):
        """Genera código para la sentencia return"""
        if return_node.expr:
            value = self._generate_expression(return_node.expr)
            self.builder.ret(value)
        else:
            self.builder.ret_void()
    
    def _generate_function_call(self, call_node):
        """Genera código para llamadas a función"""
        func = self.functions.get(call_node.name)
        if not func:
            raise RuntimeError(f"Función '{call_node.name}' no definida")
        
        # Procesar los argumentos: si se presentan listas anidadas, aplanarlas
        args = [self._generate_expression(arg) for arg in call_node.args]
        return self.builder.call(func, args)

    
    def _generate_expression(self, expr_node):
        """Genera código para expresiones"""
        if isinstance(expr_node, NumberNode):
            if isinstance(expr_node.value, int):
                return ir.Constant(ir.IntType(32), expr_node.value)
            else:
                return ir.Constant(ir.DoubleType(), expr_node.value)
        elif isinstance(expr_node, BooleanNode):
            return ir.Constant(ir.IntType(1), int(expr_node.value))
        elif isinstance(expr_node, StringNode):
            return self._create_string_constant(expr_node.value)
        elif isinstance(expr_node, VariableNode):
            ptr = self._lookup_variable(expr_node.name)
            return self.builder.load(ptr, expr_node.name)
        elif isinstance(expr_node, BinaryOpNode):
            return self._generate_binary_op(expr_node)
        elif isinstance(expr_node, UnaryOpNode):
            return self._generate_unary_op(expr_node)
        elif isinstance(expr_node, FunctionCallNode):
            return self._generate_function_call(expr_node)
        elif isinstance(expr_node, AssignmentNode):  # <- Agrega este bloque
            ptr = self._lookup_variable(expr_node.name)
            value = self._generate_expression(expr_node.expr)
            self.builder.store(value, ptr)
            return value
        else:
            raise RuntimeError(f"Tipo de expresión no soportado: {type(expr_node)}")

    def _generate_binary_op(self, bin_node):
        left = self._generate_expression(bin_node.left)
        right = self._generate_expression(bin_node.right)
        
        # Convertir tipos si es necesario
        left, right = self._match_types(left, right)
        
        op = bin_node.op
        # Detectar concatenación de cadenas:
        if op == '+' and left.type == self.llvm_types['cadena'] and right.type == self.llvm_types['cadena']:
            concat_func = self._get_concat_function()
            return self.builder.call(concat_func, [left, right])

        elif op in ('+', '-', '*', '/','%'):
            return self._generate_arithmetic_op(op, left, right)
        elif op in ('<', '>', '<=', '>=', '==', '!='):
            return self._generate_comparison_op(op, left, right)
        elif op in ('&&', '||'):
            return self._generate_logical_op(op, left, right)
        elif op == '^':
            return self._generate_power_op(left, right)
        else:
            raise RuntimeError(f"Operador binario no soportado: {op}")


    def _get_concat_function(self):
        # Busca o declara la función de concatenación.
        concat_func = self.module.globals.get("concat")
        if not concat_func:
            # Supongamos que la función tiene la siguiente firma:
            # i8* concat(i8* , i8*)
            concat_type = ir.FunctionType(self.llvm_types['cadena'], [self.llvm_types['cadena'], self.llvm_types['cadena']])
            concat_func = ir.Function(self.module, concat_type, name="concat")
        return concat_func

    
    def _generate_arithmetic_op(self, op, left, right):
            if op == '%':
                if isinstance(left.type, ir.IntType):
                    return self.builder.srem(left, right)
                else:
                    fmod_func = self._get_fmod_function()
                    return self.builder.call(fmod_func, [left, right])
            if isinstance(left.type, ir.IntType):
                if op == '+': return self.builder.add(left, right)
                if op == '-': return self.builder.sub(left, right)
                if op == '*': return self.builder.mul(left, right)
                if op == '/': return self.builder.sdiv(left, right)
            else:
                if op == '+': return self.builder.fadd(left, right)
                if op == '-': return self.builder.fsub(left, right)
                if op == '*': return self.builder.fmul(left, right)
                if op == '/': return self.builder.fdiv(left, right)


    def _generate_comparison_op(self, op, left, right):
        """Genera código para operaciones de comparación"""
        if isinstance(left.type, ir.IntType):
            if op == '<': return self.builder.icmp_signed('<', left, right)
            if op == '>': return self.builder.icmp_signed('>', left, right)
            if op == '<=': return self.builder.icmp_signed('<=', left, right)
            if op == '>=': return self.builder.icmp_signed('>=', left, right)
            if op == '==': return self.builder.icmp_signed('==', left, right)
            if op == '!=': return self.builder.icmp_signed('!=', left, right)
        else:
            if op == '<': return self.builder.fcmp_ordered('<', left, right)
            if op == '>': return self.builder.fcmp_ordered('>', left, right)
            if op == '<=': return self.builder.fcmp_ordered('<=', left, right)
            if op == '>=': return self.builder.fcmp_ordered('>=', left, right)
            if op == '==': return self.builder.fcmp_ordered('==', left, right)
            if op == '!=': return self.builder.fcmp_ordered('!=', left, right)
    
    def _generate_logical_op(self, op, left, right):
        """Genera código para operaciones lógicas"""
        left = self._convert_to_bool(left)
        right = self._convert_to_bool(right)
        
        if op == '&&': return self.builder.and_(left, right)
        if op == '||': return self.builder.or_(left, right)
    
    def _generate_power_op(self, left, right):
        # Asegurarse que ambos operandos sean double
        if isinstance(left.type, ir.IntType):
            left = self.builder.sitofp(left, ir.DoubleType())
        if isinstance(right.type, ir.IntType):
            right = self.builder.sitofp(right, ir.DoubleType())

        # Obtener o declarar función pow()
        pow_func = self._get_pow_function()

        # Generar llamada a pow y retornar
        return self.builder.call(pow_func, [left, right])

    
    
    def _get_fmod_function(self):
        """Obtiene o declara la función fmod para decimales"""
        fmod_func = self.module.globals.get("fmod")
        if not fmod_func:
            fmod_type = ir.FunctionType(ir.DoubleType(), [ir.DoubleType(), ir.DoubleType()])
            fmod_func = ir.Function(self.module, fmod_type, name="fmod")
        return fmod_func

    
    def _generate_unary_op(self, unary_node):
        """Genera código para operaciones unarias"""
        operand = self._generate_expression(unary_node.operand)
        op = unary_node.op
        
        if op == '-':
            if isinstance(operand.type, ir.IntType):
                return self.builder.neg(operand)
            else:
                return self.builder.fneg(operand)
        elif op == '!':
            return self.builder.not_(self._convert_to_bool(operand))
        elif op == '+':
            return operand
        else:
            raise RuntimeError(f"Operador unario no soportado: {op}")
    
    def _create_string_constant(self, text):
        """Crea una constante global para un string (evitando duplicados)"""
        text_bytes = text.encode('utf-8') + b'\x00'
        arr_type = ir.ArrayType(ir.IntType(8), len(text_bytes))
        name = ".str." + str(hash(text))

        # Verificar si ya existe
        if name in self.module.globals:
            return self.builder.bitcast(self.module.get_global(name), ir.PointerType(ir.IntType(8)))

        # Crear global si no existe
        global_str = ir.GlobalVariable(self.module, arr_type, name=name)
        global_str.linkage = 'internal'
        global_str.global_constant = True
        global_str.initializer = ir.Constant(arr_type, bytearray(text_bytes))

        return self.builder.bitcast(global_str, ir.PointerType(ir.IntType(8)))

    def _get_pow_function(self):
        """Declara o recupera la función estándar 'pow' (de libm)"""
        pow_func = self.module.globals.get("pow")
        if not pow_func:
            pow_type = ir.FunctionType(ir.DoubleType(), [ir.DoubleType(), ir.DoubleType()])
            pow_func = ir.Function(self.module, pow_type, name="pow")
        return pow_func

    
    def _lookup_variable(self, name):
        """Busca una variable en la tabla de símbolos"""
        for table in reversed(self.symbol_tables):
            if name in table:
                return table[name]
        raise RuntimeError(f"Variable '{name}' no definida")
    
    def _match_types(self, left, right):
        """Convierte operandos a tipos compatibles"""
        if left.type == right.type:
            return left, right
        
        # Si uno es double, convertir ambos a double
        if isinstance(left.type, ir.DoubleType) or isinstance(right.type, ir.DoubleType):
            if isinstance(left.type, ir.IntType):
                left = self.builder.sitofp(left, ir.DoubleType())
            if isinstance(right.type, ir.IntType):
                right = self.builder.sitofp(right, ir.DoubleType())
            return left, right
        
        # Si ambos son enteros y tienen distinto ancho, se extiende el de menor ancho
        if isinstance(left.type, ir.IntType) and isinstance(right.type, ir.IntType):
            if left.type.width > right.type.width:
                right = self.builder.sext(right, left.type)
            else:
                left = self.builder.sext(left, right.type)
            return left, right
        
        return left, right
    
    def _convert_to_bool(self, value):
        """Convierte un valor a booleano (i1)"""
        if isinstance(value.type, ir.IntType) and value.type.width == 1:
            return value
        return self.builder.icmp_signed('!=', value, ir.Constant(value.type, 0))
    
    #PRUEBA
def define_concat_function(module, llvm_types):
        i8ptr = llvm_types['cadena']
        i64 = ir.IntType(64)
        i32 = ir.IntType(32)
        i1 = ir.IntType(1)

        malloc_ty = ir.FunctionType(i8ptr, [i64])
        malloc = ir.Function(module, malloc_ty, name="malloc")

        strlen_ty = ir.FunctionType(i64, [i8ptr])
        strlen = ir.Function(module, strlen_ty, name="strlen")

        memcpy_ty = ir.FunctionType(ir.VoidType(), [i8ptr, i8ptr, i64, i1])
        memcpy = ir.Function(module, memcpy_ty, name="llvm.memcpy.p0i8.p0i8.i64")

        concat_ty = ir.FunctionType(i8ptr, [i8ptr, i8ptr])
        concat_func = ir.Function(module, concat_ty, name="concat")

        entry = concat_func.append_basic_block("entry")
        builder = ir.IRBuilder(entry)

        s1, s2 = concat_func.args

        len1 = builder.call(strlen, [s1])
        len2 = builder.call(strlen, [s2])
        total_len = builder.add(builder.add(len1, len2), ir.Constant(i64, 1))

        result_ptr = builder.call(malloc, [total_len])

        builder.call(memcpy, [result_ptr, s1, len1, ir.Constant(i1, 0)])

        dest_ptr = builder.gep(result_ptr, [len1])
        builder.call(memcpy, [dest_ptr, s2, len2, ir.Constant(i1, 0)])

        final_pos = builder.gep(result_ptr, [builder.add(len1, len2)])
        builder.store(ir.Constant(ir.IntType(8), 0), final_pos)

        builder.ret(result_ptr)

        return concat_func