import storage
from addressing import Access, AddressingMode
from convert import Length, Precision, Value

operations = [["PRNT","EOP"],["MOV","PUSH","POP","CALL","RET","SCAN","DEF"],["JEQ","JNE","JLT","JLE","JGT","JGE","JMP"],["MOD","ADD","SUB","MUL","DIV"]]
operationCodes = [["00","01","10","11"],["000","001","010","011","100","101","110","111"]]
class Instruction:
	@staticmethod
	def preEncode(instrxns):
		output = []
		for instr in instrxns:
			parts = instr.strip().split()
			if not parts:
				continue

			op = parts[0].upper()

			# Skip compile-time-only instructions
			if op in ["DEF", "DEV", "DEB"]:
				continue

			# Conditional jump with 3 operands → convert to SUB + conditional
			if op in ["JEQ", "JNE", "JLT", "JLE", "JGT", "JGE"] and len(parts) == 4:
				x, y, z = parts[1], parts[2], parts[3]
				output.append(f"SUB {x} {y}")
				output.append(f"{op} {z}")
				continue

			# Check each operand for indexing syntax: A1[I1] or A2[I2]
			new_parts = [op]
			for operand in parts[1:]:
				if "[" in operand and "]" in operand:
					base = operand[:operand.index("[")]
					index = operand[operand.index("[") + 1 : operand.index("]")]
					if index == "I1":
						new_parts.append(f"INDX1 {base}")
					elif index == "I2":
						new_parts.append(f"INDX2 {base}")
					else:
						raise Exception(f"Unsupported index register: {index}")
				else:
					new_parts.append(operand)

			# Reconstruct the possibly modified instruction
			output.append(" ".join(new_parts))

		return output
	
	@staticmethod
	def encode(inst):
		parts = inst.strip().split()
		if not parts:
			return "0" * Length.instrxn  # empty line fallback

		op = parts[0].upper()

		# Lookup opcode bits
		opcode = ""
		found = False
		for i, group in enumerate(operations):
			if op in group:
				e_bit = operationCodes[0][i]
				w_bit = operationCodes[1][group.index(op)]
				opcode = e_bit + w_bit
				found = True
				break
		if not found:
			raise Exception(f"Unknown operation: {op}")

		# Default operand values
		op1Mode = op1Addr = "0" * Length.opMode
		op2Mode = op2Addr = "0" * Length.opMode

		# Handle operands
		if len(parts) == 2:
			# 1 operand
			op1 = parts[1]
			op1Mode, op1Addr = Instruction.resolveOperand(op1)
		elif len(parts) == 3:
			# 2 operands
			op1 = parts[1]
			op2 = parts[2]
			op1Mode, op1Addr = Instruction.resolveOperand(op1)
			op2Mode, op2Addr = Instruction.resolveOperand(op2)

		# Combine all parts into 32-bit instruction
		return opcode + op1Mode + op1Addr + op2Mode + op2Addr + "00000"

	@staticmethod
	def encodeOp(operand):
	# For immediate address)
		if Value.isNumber(operand):
			addr = int(operand)
	# For others like Registers of Variables
		else:
			try:
				addr = storage.variable.load(operand)
			except:
				raise Exception(f"Unknown operand: {operand}")
	# Convert to 8-bit binary string by getting the value from bin(addr)[2:] and adding zeroes to make it 8-bit long
		return Length.addZeros(bin(addr)[2:], Length.operand)
	
	@staticmethod
	def encodeProgram(program):
		# Step 1: Expand macros and conditionals
		program = Instruction.preEncode(program)

		# Step 2: Get the starting memory address from PC
		pc = int(storage.register.load("PC"))  # Convert to int if it's stored in float or string

		# Step 3: Encode and store each instruction
		for i, inst in enumerate(program):
			bin_inst = Instruction.encode(inst)
			storage.memory.store(pc + i, bin_inst)

	@staticmethod
    def resolveOperand(operand):
        operand = operand.strip()

        if operand.startswith("INDX1"):
            return AddressingMode.indexed(operand[6:].strip(), index=1)
        elif operand.startswith("INDX2"):
            return AddressingMode.indexed(operand[6:].strip(), index=2)
        elif operand.startswith("@"):
            return AddressingMode.indirect(operand[1:])
        elif operand.startswith("&"):
            return AddressingMode.register_indirect(operand[1:])
        elif operand.upper() in ["PUSH", "POP", "TOP"]:
            return AddressingMode.stack(operand.upper())
        elif Value.inRegister(operand):
            return AddressingMode.register(operand)
        else:
            return AddressingMode.direct(operand)
