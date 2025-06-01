import sys
import compiler
from addressing import Access, AddressingMode
import storage
from convert import Precision, Length

class Program:
    def __init__(self, program):
        self.initialize_variables()
        self.program = self.encode(program)
        for i, instr in enumerate(self.program):
            storage.memory.store(i, instr)
        storage.register.store(self.var_load_bin('PC'), 0)
        storage.register.store(self.var_load_bin('IR'), 0)

    def initialize_variables(self):
        for i in range(8):
            reg_name = f"R{i}"
            reg_bin = f"{i+2:08b}"  # +2 offset for register binary key
            storage.variable.data[reg_name] = reg_name
            storage.register.data[reg_bin] = 0

        i1_bin = '00001000'
        pc_bin = '00000000'
        ir_bin = '00000001'

        storage.variable.data['I1'] = 'I1'
        storage.register.data[i1_bin] = 0

        storage.variable.data['PC'] = 'PC'
        storage.register.data[pc_bin] = 0

        storage.variable.data['IR'] = 'IR'
        storage.register.data[ir_bin] = 0

    def var_load_bin(self, name):
        if name == 'PC':
            return '00000000'
        elif name == 'IR':
            return '00000001'
        elif name == 'I1':
            return '00001000'
        elif name.startswith('R'):
            reg_num = int(name[1:])
            return f"{reg_num + 2:08b}"
        else:
            return name

    def encode(self, program):
        encoded_program = []
        for instruction in program:
            pre_encoded = self.pre_encode(instruction)
            if isinstance(pre_encoded, list):
                for instr in pre_encoded:
                    encoded_str = compiler.Instruction.encode(instr)
                    encoded = int(encoded_str, 2) & 0xFFFFFFFF
                    encoded_program.append(encoded)
            else:
                encoded_str = compiler.Instruction.encode(pre_encoded)
                encoded = int(encoded_str, 2) & 0xFFFFFFFF
                encoded_program.append(encoded)
        return encoded_program

    def pre_encode(self, instruction):
        if hasattr(compiler.Instruction, 'preEncode'):
            return compiler.Instruction.preEncode(instruction)
        return instruction

    def execute(self, result, opcode, op1=None, op2=None):
        try:
            if opcode == "ADD":
                return (op1 or 0) + (op2 or 0)
            elif opcode == "SUB":
                return (op1 or 0) - (op2 or 0)
            elif opcode == "MUL":
                return (op1 or 0) * (op2 or 0)
            elif opcode == "DIV":
                if op2 == 0:
                    self.exception("DivisionByZero", 0).dispMSG()
                    return 0
                return (op1 or 0) // op2
            elif opcode == "MOD":
                if op2 == 0:
                    self.exception("DivisionByZero", 0).dispMSG()
                    return 0
                return (op1 or 0) % (op2 or 1)
            elif opcode in ["JEQ", "JNE", "JLT", "JLE", "JGT", "JGE"]:
                conditions = {
                    "JEQ": op1 == op2,
                    "JNE": op1 != op2,
                    "JLT": op1 < op2,
                    "JLE": op1 <= op2,
                    "JGT": op1 > op2,
                    "JGE": op1 >= op2,
                }
                return op1 if conditions[opcode] else None
            elif opcode == "JMP":
                return op1
            elif opcode == "CALL":
                pc = int(storage.register.load(self.var_load_bin('PC'), False))
                AddressingMode.stack(pc + 1, "push")
                return op1
            elif opcode == "RET":
                return AddressingMode.stack(None, "pop")
            elif opcode == "SCAN":
                val = input("Input: ")
                return int(val) if val.isdigit() else val
            elif opcode == "PRNT":
                print(f"Output: {op1}")
            elif opcode == "EOP":
                print("End of program.")
                sys.exit(0)
            else:
                raise ValueError(f"Unsupported opcode: {opcode}")
        except Exception as e:
            print(f"Execution exception: {e}")
            return 0

    def write(self, dest, src, movcode):
        try:
            if movcode == "MOV":
                Access.store("reg", dest, src)
            elif movcode == "PUSH":
                AddressingMode.stack(src, "push")
            elif movcode == "POP":
                return AddressingMode.stack(dest, "pop")
            else:
                raise ValueError(f"Unsupported movcode: {movcode}")
        except Exception as e:
            print(f"Write exception: {e}")

    @staticmethod
    def exception(name, value):
        messages = {
            "DivisionByZero": "Division by zero exception",
            "ExecutionError": f"Execution error: {value}",
            "WriteError": f"Write error: {value}",
            "FileNotFound": f"File not found: {value}",
            "InvalidOperation": f"Invalid operation: {value}",
        }
        msg = messages.get(name, f"Unknown exception: {value}")
        # Only fatal if unknown error
        fatal = (name == "Unknown")
        return Except(msg, fatal)

    def load_register_dec(self, reg_bin):
        if isinstance(reg_bin, int):
            reg_bin = bin(reg_bin)[2:].zfill(Length.precision)
        elif isinstance(reg_bin, str) and len(reg_bin) != Length.precision:
            reg_bin = reg_bin.zfill(Length.precision)
        val = storage.register.load(reg_bin, isCode=False)
        return val

    def run(self):
        pc_addr = self.var_load_bin('PC')
        ir_addr = self.var_load_bin('IR')

        op_map = {
            "00000": "PRNT", "00001": "EOP", "01000": "MOV",
            "01001": "PUSH", "01010": "POP", "01011": "CALL",
            "01100": "RET", "01101": "SCAN", "01110": "DEF",
            "10000": "JEQ", "10001": "JNE", "10010": "JLT",
            "10011": "JLE", "10100": "JGT", "10101": "JGE",
            "10110": "JMP", "11000": "MOD", "11001": "ADD",
            "11010": "SUB", "11011": "MUL", "11100": "DIV"
        }

        while True:
            pc = int(storage.register.load(pc_addr))
            instruction = storage.memory.load(pc)

            # Ensure instruction is a 32-bit unsigned binary string
            if isinstance(instruction, int):
                instruction &= 0xFFFFFFFF
                instruction = format(instruction, '032b')
            elif isinstance(instruction, float):
                instruction = format(int(instruction) & 0xFFFFFFFF, '032b')

            if not instruction or instruction == '0' * 32:
                print("End of program (no instruction).")
                break

            print(f"[PC={pc}] {compiler.Instruction.disassemble(instruction)}")
            print(f"Binary : {instruction}")

            storage.register.store(ir_addr, pc)
            execute_bit = instruction[0]
            write_bit = instruction[1]
            cat_bits = instruction[2:5]
            opcode_bits = execute_bit + write_bit + cat_bits

            operation = op_map.get(opcode_bits, "UNKNOWN")
            if operation == "UNKNOWN":
                print(f"Unknown opcode {opcode_bits} at PC {pc}")
                break

            op1_mode = instruction[5:8]
            op1_addr = instruction[8:16]
            op2_mode = instruction[16:19]
            op2_addr = instruction[19:27]

            op1_value = self.getOp(op1_mode + op1_addr)
            op2_value = self.getOp(op2_mode + op2_addr)

            new_pc = None
            result = None

            if execute_bit == '1':
                result = self.execute(None, operation, op1_value, op2_value)
                if operation in ["JEQ", "JNE", "JLT", "JLE", "JGT", "JGE", "JMP", "CALL", "RET"] and result is not None:
                    new_pc = result

            if write_bit == '1':
                if operation == "MOV":
                    dest_reg_num = int(op1_addr, 2)
                    dest_reg_name = f"R{dest_reg_num}"
                    dest_reg_addr = self.var_load_bin(dest_reg_name)
                    self.write(dest_reg_addr, op2_value, operation)
                elif operation in ["ADD", "SUB", "MUL", "DIV", "MOD"]:
                    dest_reg_num = int(op1_addr, 2)
                    dest_reg_name = f"R{dest_reg_num}"
                    dest_reg_addr = self.var_load_bin(dest_reg_name)
                    self.write(dest_reg_addr, result, "MOV")
                else:
                    self.write(op1_value, op2_value, operation)

            if operation == "PRNT":
                print(f"Print: {op1_value}")
            elif operation == "EOP":
                print("End of program (EOP).")
                break

            storage.register.store(pc_addr, new_pc if new_pc is not None else pc + 1)

    def getOp(self, inscode):
        mode = inscode[0:3]
        addr = inscode[3:]

        MAX_MEM = len(storage.memory.data)  # Adjust if your memory is a dict or list

        def clamp_addr(address):
            if address < 0 or address >= MAX_MEM:
                print(f"Warning: Address {address} out of memory bounds, clamping to {MAX_MEM - 1}")
                return max(0, min(address, MAX_MEM - 1))
            return address

        if mode == '000':
            reg_name = f"R{int(addr, 2)}"
            reg_addr = self.var_load_bin(reg_name)
            return self.load_register_dec(reg_addr)

        elif mode == '001':
            reg_name = f"R{int(addr, 2)}"
            reg_addr = self.var_load_bin(reg_name)
            mem_addr = self.load_register_dec(reg_addr)
            mem_addr = clamp_addr(int(mem_addr))
            return storage.memory.load(mem_addr, isCode=False)

        elif mode == '010':
            mem_addr = int(addr, 2)
            mem_addr = clamp_addr(mem_addr)
            return storage.memory.load(mem_addr, isCode=False)

        elif mode == '011':
            ptr = int(addr, 2)
            ptr = clamp_addr(ptr)
            mem_addr = storage.memory.load(ptr, isCode=False)
            mem_addr = clamp_addr(int(mem_addr))
            return storage.memory.load(mem_addr, isCode=False)

        elif mode == '100':
            index_reg = self.var_load_bin('I1')
            index_val = self.load_register_dec(index_reg)
            displacement = int(addr, 2)
            mem_addr = index_val + displacement
            mem_addr = clamp_addr(mem_addr)
            return storage.memory.load(mem_addr, isCode=False)

        elif mode == '101':
            return AddressingMode.stack(None, "top")

        elif mode == '110':
            return AddressingMode.stack(None, "pop")

        elif mode == '111':
            return int(addr, 2)

        else:
            raise ValueError(f"Unknown addressing mode: {mode}")

class Except:
    def __init__(self, msg, fatal):
        self.msg = msg
        self.fatal = fatal

    def dispMSG(self):
        print(self.msg)
        if self.fatal:
            sys.exit(1)

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 run.py <program_file.txt>")
        sys.exit(1)

    filename = sys.argv[1]
    try:
        with open(filename) as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"File not found: {filename}")
        sys.exit(1)

    prog = Program(lines)
    prog.run()

if __name__ == "__main__":
    main()
