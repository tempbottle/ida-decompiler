
from expressions import *
from statements import *

# list of all tokens that can appear in the output. 
CHARACTER = 0       # comma, colon, semicolon, space, etc.
LMATCH = 1          # left matching character (eg. left parenthesis, left bracket, etc)
RMATCH = 2          # right matching character (eg. right parenthesis, right bracket, etc)
KEYWORD = 3         # keywords: if, while, etc.
VAR = 4             # any variable: registers, argument, stack var, function name, etc
STRING = 5          # a zero-terminated C string.
NUMBER = 6          # a number.
GLOBAL = 7          # a location in the database

class token(object):
    """ base class for tokens """
    def __init__(self, id):
        self.id = id
        return

class token_character(token):
    """ character token """
    
    def __init__(self, char):
        token.__init__(self, CHARACTER)
        self.char = char
        return
    
    def __str__(self):
        return self.char

class token_lmatch(token):
    """ matching character token """
    
    def __init__(self, char):
        token.__init__(self, LMATCH)
        self.char = char
        self.rmatch = None
        return
    
    def __str__(self):
        return self.char

class token_rmatch(token):
    """ matching character token """
    
    def __init__(self, char):
        token.__init__(self, RMATCH)
        self.char = char
        self.lmatch = None
        return
    
    def __str__(self):
        return self.char

class token_keyword(token):
    """ keyword token """
    
    def __init__(self, kw):
        token.__init__(self, KEYWORD)
        self.kw = kw
        return
    
    def __str__(self):
        return self.kw

class token_var(token):
    """ variable token """
    
    def __init__(self, name):
        token.__init__(self, VAR)
        self.name = name
        return
    
    def __str__(self):
        return self.name

class token_string(token):
    """ string token """
    
    def __init__(self, value):
        token.__init__(self, STRING)
        self.value = value
        return
    
    def __str__(self):
        return repr(self.value)

class token_number(token):
    """ number token """
    
    def __init__(self, value):
        token.__init__(self, NUMBER)
        self.value = value
        return
    
    def __str__(self):
        return str(self.value)

class token_global(token):
    """ number token """
    
    def __init__(self, value):
        token.__init__(self, GLOBAL)
        self.value = value
        return
    
    def __str__(self):
        return str(self.value)

class tokenizer(object):
    """ Tokenizer class for C.
    
    This class transforms the syntax tree into a flat list of tokens.
    """
    
    def __init__(self, flow):
        self.flow = flow
        self.arch = flow.arch
        return
    
    def flow_tokens(self):
        
        name = self.arch.get_ea_name(self.flow.entry_ea)
        yield token_var(name)
        
        l,r = self.matching('(', ')')
        yield l
        yield r
        yield token_character(' ')
        
        l,r = self.matching('{', '}')
        yield l
        yield token_character('\n')
        
        for block in self.flow.iterblocks():
            
            if block.jump_from:
                yield token_character('\n')
                yield token_global('loc_%x' % (block.ea, ))
                yield token_character(':')
                yield token_character('\n')
            
            for tok in self.statement_tokens(block.container, indent=1):
                yield tok
        
        yield r
        
        return
    
    def regname(self, which):
        """ returns the register name without index """
        return self.arch.get_regname(which)
    
    def matching(self, lchar, rchar):
        ltok = token_lmatch(lchar)
        rtok = token_lmatch(rchar)
        ltok.rmatch = rtok
        rtok.lmatch = ltok
        return ltok, rtok
    
    def parenthesize(self, obj):
        """ parenthesize objects as needed. """
        
        if type(obj) not in (regloc_t, flagloc_t, value_t, var_t, arg_t) or \
                (type(obj) in (regloc_t, flagloc_t) and obj.index is not None):
            l, r = self.matching('(', ')')
            yield l
            for tok in self.expression_tokens(obj):
                yield tok
            yield r
        else:
            for tok in self.expression_tokens(obj):
                yield tok
        
        return
    
    def expression_tokens(self, obj):
        
        if type(obj) in (regloc_t, flagloc_t):
            if obj.name:
                name = obj.name
            else:
                name = self.regname(obj.which)
            if obj.index is not None:
                name += '@%u' % obj.index
            yield token_var(name)
            return
        
        if type(obj) in (deref_t, ):
            yield token_character(obj.operator)
            for tok in self.parenthesize(obj.op):
                yield tok
            if obj.index is not None:
                yield token_character('@%u' % (obj.index, ))
            return
        
        if type(obj) == value_t:
            
            s = self.arch.get_string(obj.value)
            if s:
                yield token_string(s)
                return
            
            s = self.arch.get_ea_name(obj.value)
            if s:
                yield token_global(s)
                return
            
            yield token_number(obj.value)
            return
        
        if type(obj) == var_t:
            yield token_var(obj.name)
            return
        
        if type(obj) == arg_t:
            name = obj.name
            #if type(obj.where) == regloc_t:
                #name += '<%s>' % (self.to_text(obj.where), )
            yield token_var(name)
            return
        
        if type(obj) == call_t:
            
            if type(obj.fct) == value_t:
                name = self.arch.get_ea_name(obj.fct.value)
                if name:
                    yield token_global(name)
                else:
                    yield token_number(obj.fct.value)
            else:
                for tok in self.parenthesize(obj.fct):
                    yield tok
            
            l, r = self.matching('(', ')')
            yield l
            if obj.params is not None:
                for tok in self.expression_tokens(obj.params):
                    yield tok
            yield r
            
            return
        
        if type(obj) == comma_t: # op1, op2
            for tok in self.expression_tokens(obj.op1):
                yield tok
            yield token_character(',')
            yield token_character(' ')
            for tok in self.expression_tokens(obj.op2):
                yield tok
            return
        
        if type(obj) in (not_t, b_not_t, address_t, neg_t, preinc_t, predec_t):
            yield token_character(obj.operator)
            for tok in self.parenthesize(obj.op):
                yield tok
            return
        
        if type(obj) in (postinc_t, postdec_t):
            for tok in self.parenthesize(obj.op):
                yield tok
            yield token_character(obj.operator)
            return
        
        if type(obj) in (assign_t, add_t, sub_t, mul_t, div_t, shl_t, shr_t, xor_t, and_t, \
                            or_t, b_and_t, b_or_t, eq_t, neq_t, leq_t, aeq_t, lower_t, above_t):
            for tok in self.expression_tokens(obj.op1):
                yield tok
            yield token_character(' ')
            yield token_character(obj.operator)
            yield token_character(' ')
            for tok in self.expression_tokens(obj.op2):
                yield tok
            return
        
        if type(obj) == ternary_if_t:
            
            for tok in self.parenthesize(obj.op1):
                yield tok
            yield token_character(' ')
            yield token_character(obj.operator1)
            yield token_character(' ')
            for tok in self.parenthesize(obj.op2):
                yield tok
            yield token_character(' ')
            yield token_character(obj.operator2)
            yield token_character(' ')
            for tok in self.parenthesize(obj.op3):
                yield tok
            
            return
        
        if type(obj) == sign_t:
            yield token_keyword('SIGN')
            l, r = self.matching('(', ')')
            yield l
            for tok in self.expression_tokens(obj.op):
                yield tok
            yield r
            return
        
        if type(obj) == overflow_t:
            yield token_keyword('OVERFLOW')
            l, r = self.matching('(', ')')
            yield l
            for tok in self.expression_tokens(obj.op):
                yield tok
            yield r
            return
        
        if type(obj) == parity_t:
            yield token_keyword('PARITY')
            l, r = self.matching('(', ')')
            yield l
            for tok in self.expression_tokens(obj.op):
                yield tok
            yield r
            return
    
        if type(obj) == adjust_t:
            yield token_keyword('ADJUST')
            l, r = self.matching('(', ')')
            yield l
            for tok in self.expression_tokens(obj.op):
                yield tok
            yield r
            return
        
        if type(obj) == carry_t:
            yield token_keyword('CARRY')
            l, r = self.matching('(', ')')
            yield l
            for tok in self.expression_tokens(obj.op):
                yield tok
            yield r
            return
        
        raise ValueError('cannot display object of type %s' % (obj.__class__.__name__, ))
    
    def statement_tokens(self, obj, indent=0):
        
        if type(obj) == statement_t:
            for tok in self.expression_tokens(obj.expr):
                yield tok
            yield token_character(';')
            return
        
        if type(obj) == container_t:
            for stmt in obj:
                yield token_character('   ' * indent)
                for tok in self.statement_tokens(stmt, indent+1):
                    yield tok
                yield token_character('\n')
            return
        
        if type(obj) == if_t:
            yield token_character('   ' * indent)
            yield token_keyword('if')
            yield token_character(' ')
            l, r = self.matching('(', ')')
            yield l
            for tok in self.expression_tokens(obj.expr):
                yield tok
            yield r
            yield token_character(' ')
            
            l, r = self.matching('{', '}')
            yield l
            yield token_character('\n')
            for tok in self.statement_tokens(obj.then_expr, indent+1):
                yield tok
            yield token_character('   ' * indent)
            yield r
            
            if obj.else_expr:
                yield token_character('\n')
                yield token_character('   ' * indent)
                yield token_keyword('else')
                yield token_character(' ')
                
                if len(obj.else_expr) == 1 and type(obj.else_expr[0]) == if_t:
                    for tok in self.statement_tokens(obj.else_expr, indent):
                        yield tok
                else:
                    l, r = self.matching('{', '}')
                    yield l
                    yield token_character('\n')
                    for tok in self.statement_tokens(obj.else_expr, indent+1):
                        yield tok
                    yield token_character('   ' * indent)
                    yield r
            
            return
        
        if type(obj) == while_t:
            
            yield token_character('   ' * indent)
            yield token_keyword('while')
            yield token_character(' ')
            l, r = self.matching('(', ')')
            yield l
            for tok in self.expression_tokens(obj.expr):
                yield tok
            yield r
            yield token_character(' ')
            
            l, r = self.matching('{', '}')
            yield l
            yield token_character('\n')
            for tok in self.statement_tokens(obj.loop_container, indent+1):
                yield tok
            yield token_character('   ' * indent)
            yield r
            
            return
        
        if type(obj) == do_while_t:
            
            yield token_character('   ' * indent)
            yield token_keyword('do')
            l, r = self.matching('{', '}')
            yield l
            yield token_character('\n')
            for tok in self.statement_tokens(obj.loop_container, indent+1):
                yield tok
            yield token_character('   ' * indent)
            yield r
            
            yield token_character(' ')
            l, r = self.matching('(', ')')
            yield l
            for tok in self.expression_tokens(obj.expr):
                yield tok
            yield r
            yield token_character(' ')
            yield token_character(';')
            
            return
        
        if type(obj) == goto_t:
            yield token_keyword('goto')
            yield token_character(' ')
            
            if type(obj.expr) == value_t:
                yield token_global('loc_%x' % (obj.expr.value, ))
            else:
                for tok in self.expression_tokens(obj.expr):
                    yield tok
            
            yield token_character(';')
            return
        
        if type(obj) == return_t:
            yield token_keyword('return')
            if obj.expr:
                yield token_character(' ')
                for tok in self.expression_tokens(obj.expr):
                    yield tok
            yield token_character(';')
            return

        if type(obj) == break_t:
            yield token_keyword('break')
            yield token_character(';')
            return
        
        if type(obj) == continue_t:
            yield token_keyword('continue')
            yield token_character(';')
            return
        
        raise ValueError('cannot display object of type %s' % (obj.__class__.__name__, ))



