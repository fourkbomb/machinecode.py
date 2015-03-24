#!/usr/bin/python3
import re
import argparse
from collections import defaultdict
# instructions = []
# with open('input', 'r') as inp:
#     instructions = list(map(int, ' '.join(inp.readlines()).split()))

# print(instructions)
# {ACTION} [IF {CONDITION}]
# ACTION ::= ADD {NUM} TO {REGISTER}
# ACTION ::= HALT
# ACTION ::= PRINT {REGISTER} AS {TYPE}
# ACTION ::= JUMP <DATA>
# ACTION ::= LOAD <DATA> TO {REGISTER}
# ACTION ::= WRITE {REGISTER} TO <DATA>
# ACTION ::= SWAP {REGISTER} WITH <DATA>
# ACTION ::= BELL

# NUM ::= [-] ({REGISTER}, [0-9]+)
# REGISTER ::= R[0-9]+
# TYPE ::= INT, CHAR
# ADDR ::= <DATA>, [0-9]+

# CONDITION ::= {REGISTER} {!=|==} 0

# TODO: Change <DATA> in WRITE, LOAD, SWAP and JUMP to {ADDR}


class InstructionSetReader:
    '''Emulates a custom microprocessor

    INSERT LONG EXPLAINATION HERE
    # Oh damn that's a lot of docstring writing :P
    Attributes:
        fh:
        cfg:
        _regexps:
        instructions:
        registers:
        instructionPointer:
        program:
    Methods:
        shit.
    '''

    def __init__(self, fh):
        self.fh = fh  # Name pending?
        self.cfg = {
            'NUM_REGISTERS': 1,
            'BITS_PER_BYTE': 4,
            'CELLS': 16
        }
        self._regexps = {
            'number': r'(-?R?\d+)',
            'register': r'(R\d+)',
            'address': r'(<DATA>|\d+)',
        }
        self.instructions = {}
        self.registers = defaultdict(int)
        self.instructionPointer = 0
        self.program = []

    def _max_byte_val(self):
        return 2**int(self.cfg['BITS_PER_BYTE'])

    def _parse_num(self, num_str):  # returns an int
        # input checking
        if type(num_str) != str:
            raise Exception(str(num_str) + " is not a str")

        is_negative = num_str.startswith('-')
        if num_str.startswith('R'):
            reg = int(num_str[1:])
            if self.cfg['NUM_REGISTERS'] <= reg:
                raise Exception(
                    str(reg) + " is an illegal register for this chip")
            else:
                if is_negative:
                    return -1 * self.registers[reg]
                else:
                    return self.registers[reg]
        else:
            return int(num_str)  # May break things

    def _parse_register(self, reg_str, explodeOnError=True):
        if not reg_str.startswith('R'):
            if explodeOnError:
                raise Exception(str(reg_str) + " is not a register")
            else:
                return None
        reg = int(reg_str[1:])
        if self.cfg['NUM_REGISTERS'] <= reg:
            if explodeOnError:
                raise Exception(str(reg) + ": register out of bounds")
            else:
                return None
        return reg

    def gen_add_func(self, arg1, to):
        temp = self._parse_register(arg1, False)
        to = self._parse_register(to)
        if not temp:
            arg1 = self._parse_num(arg1)
        else:
            arg1 = self.registers[temp]

        def __add_func():
            self.registers[to] += arg1
            self.registers[to] %= self._max_byte_val()
        return __add_func

    def make_conditional(self, func, cond_str):
        parts = cond_str.split()
        reg = self._parse_register(parts[0])
        equals = parts[1] == '=='
        print("Make condition => {}".format(cond_str))

        def __condition():
            if (self.registers[reg] == 0) == equals:  # condition matches
                func()
        return __condition

    def _try_parse_add(self, action):
        match = re.match(r'ADD {number} TO {register}'.format_map(
            self._regexps), action.upper())
        if match:
            args = match.groups()
            print(action, args)
            return self.gen_add_func(args[0], args[1])
        return None

    def _try_parse_halt(self, action):
        if re.match('HALT', action.upper()):
            def __dummy():
                raise Exception("Stopped")
            return __dummy

    def _try_parse_print(self, action):
        match = re.match(r'PRINT {register} AS (UINT|CHAR)'.format_map(
            self._regexps), action.upper())
        if match:
            args = list(match.groups())
            args[0] = self._parse_register(args[0])

            def __print_func():
                display = self.registers[args[0]]
                if args[1] == 'CHAR':
                    display = chr(display)
                print(display, end='\n')
            return __print_func
        return None

    def _increment(self, value):  # Name pending
        return (value + 1) % self._max_byte_val()

    def _try_parse_jump(self, action):
        match = re.match(r'JUMP <DATA>', action.upper())
        if match:
            def __jump():
                self.instructionPointer = self._increment(
                    self.instructionPointer)
                jumpTo = self.program[self.instructionPointer]
                self.instructionPointer = (jumpTo % self._max_byte_val()) - 1
            return __jump
        return None

    def _try_parse_load(self, action):
        match = re.match(r'LOAD <DATA> TO {register}'.format_map(
            self._regexps), action)
        if match:
            reg = self._parse_register(match.group(1))

            def __load():
                self.instructionPointer = self._increment(
                    self.instructionPointer)
                self.registers[reg] = self.program[self.instructionPointer]
            return __load
        return None

    def _try_parse_write(self, action):
        match = re.match(r'WRITE {register} TO <DATA>'.format_map(
            self._regexps), action)
        if match:
            reg = self._parse_register(match.group(1))

            def __write():
                self.instructionPointer = self._increment(
                    self.instructionPointer)

                writeTo = self.program[self.instructionPointer]
                self.program[writeTo] = self.registers[reg]
            return __write
        return None

    def _try_parse_swap(self, action):
        match = re.match(r'SWAP {register} WITH <DATA>'.format_map(
            self._regexps), action)
        if match:
            reg = self._parse_register(match.group(1))

            def __swap():
                self.instructionPointer = self._increment(
                    self.instructionPointer)

                swapIndex = self.program[self.instructionPointer]
                self.registers[reg], self.program[swapIndex] = self.program[
                    swapIndex], self.registers[reg]
            return __swap
        return None

    def _try_parse_bell(self, action):
        if re.match('BELL', action.upper()):
            return lambda: print("\b", end='')
        return None

    def parse(self):
        read_cfg = False

        def __pass():
            print("[undefined action]")
        for i in self.fh:
            i = i.strip()
            if re.match('$', i):
                continue
            if not read_cfg:
                if re.match('INSTRUCTIONS:', i):
                    read_cfg = True
                    continue
                fields = re.split(r'\s*=\s*', i)
                print(fields)
                self.cfg[fields[0]] = int(fields[1])
            else:
                num, action = re.split(r'\s*:\s*', i)
                num = int(num)
                if num in self.instructions:
                    print("!! Duplicate instruction detected - {}, last declared will take priority".format(num))
                totry = [
                    self._try_parse_add,
                    self._try_parse_halt,
                    self._try_parse_print,
                    self._try_parse_jump,
                    self._try_parse_bell,
                    self._try_parse_load,
                    self._try_parse_write,
                    self._try_parse_swap
                ]
                for func in totry:
                    res_lambda = func(action)
                    if res_lambda is not None:
                        break

                is_conditional = re.search(
                    r'IF ({register} [=!]= 0)'.format_map(
                        self._regexps), action)

                if is_conditional:
                    res_lambda = self.make_conditional(
                        res_lambda, is_conditional.group(1))

                if not res_lambda:
                    res_lambda = __pass
                    print("!! Unknown action - " + action)
                self.instructions[num] = res_lambda

    def execute(self, instr):
        self.program = [int(i) for i in instr]
        self.instructionPointer = 0
        while self.instructionPointer < len(instr):
                # print(instr[self.instructionPointer])

                # Calls the instruction
            self.instructions[int(instr[self.instructionPointer])]()
            # print(self.registers)
            self.instructionPointer += 1
            self.instructionPointer %= self._max_byte_val()
        # print(self.registers)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--instruction-set', type=str, default='8005instr.txt',
                        help='location of instruction file')
    parser.add_argument('-f', '--file', type=str, default='program.txt',
                        help='location of program file to run')
    args = parser.parse_args()

    instr = open(args.instruction_set)
    isr = InstructionSetReader(instr)
    isr.parse()
    with open(args.file) as prog:
        code = list(map(' '.join(prog.readlines()).split(), int))
        print(code)
        isr.execute(code)
