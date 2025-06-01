import sys
import compiler
from addressing import Access, AddressingMode
import storage
from convert import Precision, Length

class Program:
    def __init__(self, program):

        self.program = self.encode(program)
    
    def encode(self, program):
     
        encoded_program = []
        for instruction in program:
            pre_encoded = self.pre_encode(instruction)
            if hasattr(compiler.Instruction, 'encode'):
                encoded = compiler.Instruction.encode(pre_encoded)
            else:
                encoded = pre_encoded
            encoded_program.append(encoded)
        return encoded_program
    
    def pre_encode(self, instruction):

        if hasattr(compiler.Instruction, 'preEncode'):
            return compiler.Instruction.preEncode(instruction)
        else:
            return instruction
    
    def execute(self, result, opcode):

        if opcode == "ADD":
            return result + 1  
        elif opcode == "SUB":
            return result - 1  
        elif opcode == "MUL":
            return result * 2  
        elif opcode == "DIV":
            if result == 0:
                div_exception = self.exception("DivisionByZero", 0)
                div_exception.dispMSG()
                return 0
            return result / 2  
        elif opcode == "MOD":
            if result == 0:
                div_exception = self.exception("DivisionByZero", 0)
                div_exception.dispMSG()
                return 0
            return result % 2  
        
        elif opcode in ["JEQ", "JNE", "JLT", "JLE", "JGT", "JGE", "JMP"]:
            print("Jump operation: {}".format(opcode))
            return result
        
        elif opcode == "CALL":
            print("Call operation")
            return result
        elif opcode == "RET":
            print("Return operation")
            return result
        elif opcode == "SCAN":
            print("Scan operation")
            return result
        elif opcode in ["PRNT", "EOP"]:
            print("Print/End operation")
            return result
        
        else:
            raise ValueError("Unsupported opcode: {}".format(opcode))
    
    def write(self, dest, src, movcode):

        if movcode == "MOV":
            if hasattr(Access, 'store'):
                Access.store(dest, src)
            return src
        elif movcode == "PUSH":
            if hasattr(AddressingMode, 'stack'):
                AddressingMode.stack(src, "push")
            return src
        elif movcode == "POP":
            if hasattr(AddressingMode, 'stack'):
                return AddressingMode.stack(dest, "pop")
            return src
        else:
            raise ValueError("Unsupported movcode: {}".format(movcode))
    
    @staticmethod
    def exception(name, value):

        if name == "DivisionByZero" and value == 0:
            return Except("Division by zero exception", True)
        elif name == "ExecutionError":
            return Except("Execution error: {}".format(value), True)
        elif name == "WriteError":
            return Except("Write error: {}".format(value), True)
        elif name == "FileNotFound":
            return Except("File not found: {}".format(value), True)
        elif name == "InvalidOperation":
            return Except("Invalid operation: {}".format(value), True)
        else:
            return Except("Unknown exception: {}".format(value), False)
    
    def run(self):
        # Get register addresses 
        pc_addr = storage.variable.load('PC', isCode=False)
        ir_addr = storage.variable.load('IR', isCode=False)
        
        storage.register.store(ir_addr, storage.register.load(pc_addr, isCode=False))
        while True:
            ir_val = storage.register.load(ir_addr, isCode=False)
            instruction = storage.memory.load(int(ir_val), isCode=True)
            
            
            if instruction == '0' * 32 or not instruction:
                break
            
          
            opcode = instruction[0:5]           
            op1_mode = instruction[5:8]         
            op1_addr = instruction[8:16]        
            op2_mode = instruction[16:19]       
            op2_addr = instruction[19:27]       
            extra = instruction[27:32]          
            
            op_map = {
                "00000": "PRNT", "00001": "EOP", "01000": "MOV",
                "01001": "PUSH", "01010": "POP", "01011": "CALL",
                "01100": "RET", "01101": "SCAN", "01110": "DEF",
                "10000": "JEQ", "10001": "JNE", "10010": "JLT",
                "10011": "JLE", "10100": "JGT", "10101": "JGE",
                "10110": "JMP", "11000": "MOD", "11001": "ADD",
                "11010": "SUB", "11011": "MUL", "11100": "DIV"
            }
            operation = op_map.get(opcode, "UNKNOWN")
            
            op1_value = self.getOp(op1_mode + op1_addr) if op1_mode != '000' else None
            op2_value = self.getOp(op2_mode + op2_addr) if op2_mode != '000' else None
            
            execute_bit = opcode[0]
            write_bit = opcode[1]
            
            if execute_bit == '1':
                self.execute(None, operation, op1_value, op2_value)
            elif write_bit == '1':
                self.write(op1_value, op2_value, operation)
            else:
                # Print/end operations
                if operation == "PRNT":
                    print(f"Printing: {op1_value}")
                elif operation == "EOP":
                    print("End of program")
                    break    
                
            pc_val = storage.register.load(pc_addr, isCode=False)
            storage.register.store(ir_addr, pc_val)
            storage.register.store(pc_addr, int(pc_val) + 1)
    
    def getOp(self, inscode):

        mode = inscode[0:3]    
        addr = inscode[3:]     
        
        if mode == '000':  
            return Precision.spbin2dec(addr)
        
        elif mode == '001':  
            reg_name = f"R{int(addr, 2)}"
            reg_addr = storage.variable.load(reg_name, isCode=False)
            return storage.register.load(reg_addr, isCode=False)
    
        elif mode == '010':  
            reg_name = f"R{int(addr, 2)}"
            reg_addr = storage.variable.load(reg_name, isCode=False)
            mem_addr = storage.register.load(reg_addr, isCode=False)
            return storage.memory.load(int(mem_addr), isCode=False)
        
        elif mode == '100':  
            index_reg = storage.variable.load('I1', isCode=False)
            index_val = storage.register.load(index_reg, isCode=False)
            displacement = int(addr, 2)
            return storage.memory.load(index_val + displacement, isCode=False)
        
        elif mode == '101':  
            return AddressingMode.stack("pop")
        
       
        else:
            raise ValueError(f"Unsupported addressing mode: {mode}")
        
    @staticmethod
    def exception(name, value):

        if name == "DivisionByZero" and value == 0:
            return Except("Division by zero exception", True)
        elif name == "ExecutionError":
            return Except("Execution error: {}".format(value), True)
        elif name == "WriteError":
            return Except("Write error: {}".format(value), True)
        elif name == "FileNotFound":
            return Except("File not found: {}".format(value), True)
        elif name == "InvalidOperation":
            return Except("Invalid operation: {}".format(value), True)
        else:
            return Except("Unknown exception: {}".format(value), False)

class Except:

    
    def __init__(self, msg, occur=True):

        self.message = msg 
        self.occur = occur  
        self.ret = None     
    
    def dispMSG(self):
        print(self.message)
    
    def isOccur(self):
        return self.occur
    
    def setReturn(self, val):
        self.ret = val
    
    def getReturn(self):
        return self.ret
    
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python run.py <program_file>")
        sys.exit(1)
    filename = sys.argv[1]
    with open(filename, "r") as f:
        lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("//")]
    prog = Program(lines)
    prog.run()