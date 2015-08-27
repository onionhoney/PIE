#!/usr/bin/python

import re
import sys

uvars = {'true', 'false'}
string_vars = set()

def addVar(s,l,t):
    uvars.add(t[0])
    return t

def flatString(l, newLine=False):
    return (l if type(l) is str else "(%s)" % (('\n' if newLine else ' ').join(flatString(x) for x in l)))

def fix_indexOf(l):
    if type(l) is str:
        return l
    elif len(l) > 0 and l[0] == 'str.indexof':
        return [fix_indexOf(e) for e in l] + ['0']
    else:
        return [fix_indexOf(e) for e in l]

def infix2prefix(l):
    return (l[0] if len(l) < 3 else [l[-2], infix2prefix(l[:-2]), l[-1]])

def chkString(token):
    if type(token) is str:
        if token not in string_vars:
            string_vars.add(token)
    return token

###

from pyparsing import alphas, alphanums, Combine, Forward, Literal, nums, \
                      nestedExpr, oneOf, opAssoc, operatorPrecedence, \
                      Optional, ParserElement, QuotedString, Suppress, Word

ParserElement.enablePackrat()

LPAR, RPAR, COMMA = map(Suppress, '(),')
const = oneOf('true false')

aop0 = oneOf('* /')
aop1 = oneOf('+ -')
aop2 = oneOf('%').setParseAction(lambda s,l,t: ['mod'])

bop = oneOf('& |').setParseAction(lambda s,l,t: ['and'] if t[0] == '&' else ['or'])
NOT = Literal('!')

rop = oneOf('< > <= >= = !=').setParseAction(lambda s,l,t: ['distinct'] if t[0] == '!=' else t)

GET, CAT, HAS, IND, LEN, REP, SUB, EQL = map(Literal, '#get #cat #has #ind #len #rep #sub #eql'.split())

var = Word(alphas+'_:$', alphanums+'_:$').setParseAction(addVar)
ival = Combine(Optional('-') + Word(nums)).setParseAction(lambda s,l,t: ['(- %s)' % t[0][1:]] if t[0][0] == '-' else t)
ivar = (ival + var).setParseAction(lambda s,l,t: ['*', t[0], t[1]])

term = ivar | ival | var | QuotedString(quoteChar='"', unquoteResults=False)

stmt = Forward()
expr = Forward()
sexpr = Forward()

sexpr << ( (GET + LPAR + expr + COMMA + expr + RPAR).setParseAction(lambda s,l,t: [['CharAt', chkString(t[1]), t[2]]])
         | (CAT + LPAR + expr + COMMA + expr + RPAR).setParseAction(lambda s,l,t: [['Concat', chkString(t[1]), chkString(t[2])]])
         | (IND + LPAR + expr + COMMA + expr + RPAR).setParseAction(lambda s,l,t: [['Indexof', chkString(t[1]), chkString(t[2])]])
         | (LEN + LPAR + expr + RPAR).setParseAction(lambda s,l,t: [['Length', chkString(t[1])]])
         | (REP + LPAR + expr + COMMA + expr + COMMA + expr + RPAR).setParseAction(lambda s,l,t: [['Replace', chkString(t[1]), chkString(t[2]), chkString(t[3])]])
         | (SUB + LPAR + expr + COMMA + expr + COMMA + expr + RPAR).setParseAction(lambda s,l,t: [['Substring', chkString(t[1]), t[2], t[3]]])
         | term
         | (LPAR + sexpr + RPAR))

expr << ( operatorPrecedence(sexpr, [
                                     (aop0, 2, opAssoc.LEFT, lambda s,l,t: [infix2prefix(t[0])]),
                                     (aop1, 2, opAssoc.LEFT, lambda s,l,t: [infix2prefix(t[0])]),
                                     (aop2, 2, opAssoc.LEFT, lambda s,l,t: [infix2prefix(t[0])])
                                    ])
        | (LPAR + expr + RPAR))

stmt << ( const
        | (HAS + LPAR + expr + COMMA + expr + RPAR).setParseAction(lambda s,l,t: [['Contains', chkString(t[1]), chkString(t[2])]])
        | (EQL + LPAR + expr + COMMA + expr + RPAR).setParseAction(lambda s,l,t: [['=', chkString(t[1]), chkString(t[2])]])
        | (expr + rop + expr).setParseAction(lambda s,l,t: [[t[1], t[0], t[2]]])
        | (LPAR + stmt + RPAR))

pred = operatorPrecedence(stmt, [
                            (NOT, 1, opAssoc.RIGHT, lambda s,l,t: [['not', t[0][1]]]),
                            (bop, 2, opAssoc.LEFT, lambda s,l,t: [infix2prefix(t[0])] )
                         ])

###

def string_from_z3_model(mod):
    model = {var: 0 for var in uvars}
    for var in mod:
        model[str(var)] = mod[var]
    return '(From Z3)\n' + '\n'.join('%s : %s' % (var, model[var]) for var in model)

def string_from_cvc4_model(cvc4_proc):
    cvc4_proc.stdin.write('(get-value (%s))\n' % (' '.join(uvars)))
    model = cvc4_proc.stdout.readline().strip()[2:-2].split(') (')
    model = {pair.partition(' ')[0]:pair.partition(' ')[2] for pair in model}
    return '(From CVC4)\n' + '\n'.join('%s : %s' % (var, model[var]) for var in model)

def string_from_z3str_model(z3str_out):
    model = {var: 0 for var in uvars}
    for line in z3str_out[4:-4]:
        line = list(line.partition(' : '))
        line[2] = line[2].partition(' -> ')[2].strip()
        model[line[0]] = line[2] if line[2][0] != '-' else '(- %s)' % line[2][1:]
    return '(From Z3Str)\n' + '\n'.join('%s : %s' % (var, model[var].replace("\\\"","#")) for var in model)

def z3str_to_cvc4(smtlib2_string):
    smtlib2_string = '\n'.join([l for l in smtlib2_string.split('\n') if ';;' not in l])
    smtlib2_string = '(%s)' % (smtlib2_string
                               .replace('CharAt', 'str.at')
                               .replace('Concat', 'str.++')
                               .replace('Contains', 'str.contains')
                               .replace('Indexof', 'str.indexof')
                               .replace('Length', 'str.len')
                               .replace('Replace', 'str.replace')
                               .replace('Substring', 'str.substr')
                               )
    smtlib2_string = flatString(fix_indexOf(nestedExpr('(', ')').parseString(smtlib2_string).asList()[0]), True)
    return smtlib2_string[1:-1]

def substitute_model(smtlib2_string, model):
    model = {line.partition(' : ')[0]:line.partition(' : ')[2] for line in model[1:].split('\n')}
    for var in model:
        smtlib2_string = re.sub(r'\b{}\b'.format(re.escape(var)), model[var], smtlib2_string)
    return smtlib2_string

def smtlib2_string_from_file(action, filename, headless, implicant=None, implicantHeadless=None):
    global uvars

    uvars = {'true', 'false'}
    with open(filename) as f:
       mcf = f.readlines()
    mcf = mcf[0].strip() if headless != "0" else mcf[2].strip()

    if implicant is not None:
        with open(implicant) as f:
            imcf = f.readlines()
        imcf = imcf[0].strip() if implicantHeadless != "0" else imcf[2].strip()
        mcf = '((! (%s)) | (%s))' % (mcf, imcf)

    smtstr = flatString(pred.parseString(mcf, parseAll = True).asList()[0])
    uvars.discard('true')
    uvars.discard('false')

    smtstr = '%s\n(%s %s)' % (
        '\n'.join('(declare-const %s %s)' % (var, 'String' if var in string_vars else 'Int') for var in uvars),
        action,
        smtstr)
    return smtstr

if __name__ == "__main__":
    print(smtlib2_string_from_file('assert', sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "1"))
