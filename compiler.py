import storage
from addressing import Access, AddressingMode
from convert import Length, Precision, Value

operations = [["PRNT","EOP"],["MOV","PUSH","POP","CALL","RET","SCAN","DEF"],["JEQ","JNE","JLT","JLE","JGT","JGE","JMP"],["MOD","ADD","SUB","MUL","DIV"]]
operationCodes = [["00","01","10","11"],["000","001","010","011","100","101","110","111"]]
class Instruction:
	@staticmethod
	def preEncode(instrxns):
              
	def encode(inst):
              
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

	def encodeProgram(program):
		