#!/usr/bin/python3
import re
import argparse
#instructions = []
#with open('input', 'r') as inp:
#    instructions = list(map(int, ' '.join(inp.readlines()).split()))
#
#print(instructions)
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
	def __init__(self, fh):
		self.fh = fh
		self.cfg = {
			'REGISTERS': 1,
			'BITS_PER_BYTE': 4,
			'CELLS': 16
		}
		self._regexps = {
				'number': r'(-?R?\d+)',
				'register': r'(R\d+)',
				'address': r'(<DATA>|\d+)',
		}
		self.instructions = {}
		self.registers = {}
		self.instructionPointer = 0
		self.program = []
	def _max_byte_val(self):
		return 2**int(self.cfg['BITS_PER_BYTE'])

	def _parse_num(self, num_str): # returns an int
		# input checking
		if type(num_str) != str:
			raise Exception(str(num_str) + " is not a str")
		negate = False
		if num_str.startswith('-'):
			negate = True
			num_str = num_str[1:]
		if num_str.startswith('R'):
			reg = int(num_str[1:])
			if self.cfg['REGISTERS'] <= reg:
				raise Exception(str(reg) + " is an illegal register for this chip")
			else:
				if not reg in self.registers:
					self.registers[reg] = 0
				if negate:
					return 0 - self.registers[reg]
				else:
					return self.registers[reg]
		else:
			if negate:
				return 0 - int(num_str)
			else:
				return int(num_str)

	def _parse_register(self, reg_str, explodeOnError=True):
		if not reg_str.startswith('R'):
			if explodeOnError:
				raise Exception(str(reg_str) + " is not a register")
			else:
				return None
		reg = int(reg_str[1:])
		if reg >= self.cfg['REGISTERS']:
			if explodeOnError:
				raise Exception(str(reg) + ": register out of bounds")
			else:
				return None
		if not reg in self.registers:
			self.registers[reg] = 0
		return reg

	def gen_add_func(self, arg1, to):
		temp = self._parse_register(arg1, False)
		to = self._parse_register(to)
		if temp == None:
			arg1 = self._parse_num(arg1)
		else:
			arg1 = temp
			def __add_func(): 
				self.registers[to] += self.registers[arg1]
				self.registers[to] %= self._max_byte_val()
			return __add_func
		def __add_func(): 
			self.registers[to] += arg1
			self.registers[to] %= self._max_byte_val()
		return __add_func

	def make_conditional(self, func, cond_str):
		parts = cond_str.split()
		register = self._parse_register(parts[0])
		equals = parts[1] == '=='
		print("Make condition => %s"%cond_str)
		def __condition():
			if (self.registers[register] == 0) == equals:
				# condition matches
				func()
		return __condition


	def _try_parse_add(self, action):
		match = re.match(r'ADD {number} TO {register}'.format_map(self._regexps), action.upper())
		if match:
			args = match.groups()
			print(action,args)
			return self.gen_add_func(args[0], args[1])
		return None

	def _try_parse_halt(self, action):
		if re.match('HALT', action.upper()):
			def __dummy(): raise Exception("Stopped")
			return __dummy

	def _try_parse_print(self, action):
		match = re.match(r'PRINT {register} AS (UINT|CHAR)'.format_map(self._regexps), action.upper())
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

	def _try_parse_jump(self, action):
		match = re.match(r'JUMP <DATA>', action.upper())
		if match:
			def __jump():
				self.instructionPointer = (self.instructionPointer + 1) % self._max_byte_val()
				jumpTo = self.program[self.instructionPointer]
				self.instructionPointer = (jumpTo % self._max_byte_val()) - 1
			return __jump
		return None

	def _try_parse_load(self, action):
		match = re.match(r'LOAD <DATA> TO {register}'.format_map(self._regexps), action)
		if match:
			reg = self._parse_register(match.group(1))
			def __load():
				self.instructionPointer = (self.instructionPointer + 1) % self._max_byte_val()
				self.registers[reg] = self.program[self.instructionPointer]
			return __load
		return None

	def _try_parse_write(self, action):
		match = re.match(r'WRITE {register} TO <DATA>'.format_map(self._regexps), action)
		if match:
			reg = self._parse_register(match.group(1))
			def __write():
				self.instructionPointer = (self.instructionPointer + 1) % self._max_byte_val()
				self.program[self.program[self.instructionPointer]] = self.registers[reg]
			return __write
		return None

	def _try_parse_swap(self, action):
		match = re.match(r'SWAP {register} WITH <DATA>'.format_map(self._regexps), action)
		if match:
			reg = self._parse_register(match.group(1))
			def __swap():
				self.instructionPointer = (self.instructionPointer + 1) % self._max_byte_val()
				temp = self.program[self.program[self.instructionPointer]]
				self.program[self.program[self.instructionPointer]] = self.registers[reg]
				self.registers[reg] = temp
			return __swap
		return None

	def _try_parse_bell(self, action):
		if re.match('BELL', action.upper()):
			return lambda: print("\b", end='')
		return None



	def parse(self):
		read_cfg = False
		def __pass(): print("[undefined action]")
		for i in self.fh:
			i = i.strip()
			if re.match('$', i): continue
			if not read_cfg:
				if re.match('INSTRUCTIONS:', i):
					read_cfg = True
					continue
				fields = re.split(r'\s*=\s*', i)
				print(fields)
				self.cfg[fields[0]] = int(fields[1])
			else:
				(num,action) = re.split(r'\s*:\s*', i)
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
					if res_lambda != None:
						break
				is_conditional = re.search(r'IF ({register} [=!]= 0)'.format_map(self._regexps), action)
				if is_conditional:
					res_lambda = self.make_conditional(res_lambda, is_conditional.group(1))
				if res_lambda == None:
					res_lambda = __pass
					print("!! Unknown action - " + action)
				self.instructions[num] = res_lambda

	def execute(self, instr):
		self.program = list(map(int, instr))
		self.instructionPointer = 0
		while self.instructionPointer < len(instr):
			#print(instr[self.instructionPointer])
			self.instructions[int(instr[self.instructionPointer])]()
			#print(self.registers)
			self.instructionPointer += 1
			self.instructionPointer %= self._max_byte_val()
			
			#print(self.registers)
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
		code = ' '.join(prog.readlines()).split()
		print(code)
		isr.execute(code)
	instr.close()





