import storage
from addressing import Access, AddressingMode
from convert import Length, Precision, Value

# Map of operation to (E, W, Category bits)
opcode_map = {
    "PRNT":  ("0", "0", "000"),
    "EOP":   ("0", "0", "001"),
    "MOV":   ("0", "1", "000"),
    "PUSH":  ("0", "1", "001"),
    "POP":   ("0", "1", "010"),
    "CALL":  ("0", "1", "011"),
    "RET":   ("0", "1", "100"),
    "SCAN":  ("0", "1", "101"),
    "DEF":   ("0", "1", "110"),
    "JEQ":   ("1", "0", "000"),
    "JNE":   ("1", "0", "001"),
    "JLT":   ("1", "0", "010"),
    "JLE":   ("1", "0", "011"),
    "JGT":   ("1", "0", "100"),
    "JGE":   ("1", "0", "101"),
    "JMP":   ("1", "0", "110"),
    "MOD":   ("1", "1", "000"),
    "ADD":   ("1", "1", "001"),
    "SUB":   ("1", "1", "010"),
    "MUL":   ("1", "1", "011"),
    "DIV":   ("1", "1", "100"),
}

class Instruction:
    @staticmethod
    def preEncode(instr):
        parts = instr.strip().split()
        if not parts:
            return []

        if parts[0].endswith(":"):
            # Skip label definitions like FUNC:
            return []

        op = parts[0].upper()
        if op in ["DEF", "DEV", "DEB"]:
            return []

        if op in ["JEQ", "JNE", "JLT", "JLE", "JGT", "JGE"] and len(parts) == 4:
            x, y, z = parts[1], parts[2], parts[3]
            return [f"SUB {x} {y}", f"{op} {z}"]

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
        return [" ".join(new_parts)]

    @staticmethod
    def encode(inst):
        parts = inst.strip().split()
        if not parts:
            return "0" * Length.instrxn

        op = parts[0].upper()

        if op not in opcode_map:
            raise Exception(f"Unknown operation: {op}")

        E, W, cat = opcode_map[op]
        opcode_bits = E + W + cat

        op1Mode, op2Mode = "000", "000"
        op1Addr, op2Addr = "00000000", "00000000"

        if len(parts) == 2:
            op1Mode, op1Addr = Instruction.encodeOp(parts[1], op)
        elif len(parts) == 3:
            op1Mode, op1Addr = Instruction.encodeOp(parts[1], op)
            op2Mode, op2Addr = Instruction.encodeOp(parts[2], op)

        extra_bits = "00000"

        bin_str = opcode_bits + op1Mode + op1Addr + op2Mode + op2Addr + extra_bits

        if len(bin_str) != 32:
            raise AssertionError(f"Instruction not 32 bits: {inst} → {bin_str} (length {len(bin_str)})")

        return bin_str

    @staticmethod
    def encodeOp(operand, op_context=None):
        operand = operand.strip().rstrip(',')

        if operand.upper() == "PUSH":
            return "101", format(255, '08b')
        if operand.upper() == "POP":
            return "110", format(255, '08b')

        if operand.startswith("@"):
            mode = "001"
            reg_str = operand[1:]
            if reg_str.startswith("R"):
                reg_num = int(reg_str[1:])
            else:
                reg_num = int(reg_str)
            addr = format(reg_num, '08b')
            return mode, addr

        if operand.startswith("&"):
            target = operand[1:]
            if target.startswith("R"):
                mode = "010"
                reg_num = int(target[1:])
                addr = format(reg_num, '08b')
                return mode, addr
            else:
                mode = "010"
                try:
                    addr_num = int(storage.variable.load(target))
                except Exception:
                    addr_num = 0
                addr = format(addr_num, '08b')
                return mode, addr

        if operand.startswith("#"):
            mode = "011"
            imm_val = int(operand[1:])
            addr = format(imm_val, '08b')
            return mode, addr

        if operand.startswith("INDX1"):
            parts = operand.split()
            if len(parts) != 2:
                raise Exception(f"Invalid INDX1 operand format: {operand}")
            base = parts[1]
            mode = "100"
            if base.startswith("R"):
                reg_num = int(base[1:])
            else:
                try:
                    reg_num = int(storage.variable.load(base))
                except:
                    reg_num = 0
            addr = format(reg_num, '08b')
            return mode, addr

        if operand.startswith("INDX2"):
            parts = operand.split()
            if len(parts) != 2:
                raise Exception(f"Invalid INDX2 operand format: {operand}")
            base = parts[1]
            mode = "100"
            if base.startswith("R"):
                reg_num = int(base[1:])
            else:
                try:
                    reg_num = int(storage.variable.load(base))
                except:
                    reg_num = 0
            addr = format(reg_num, '08b')
            return mode, addr

        if operand.startswith("R"):
            mode = "000"
            reg_num = int(operand[1:])
            addr = format(reg_num, '08b')
            return mode, addr

        try:
            addr_num = int(storage.variable.load(operand))
            mode = "010"
            addr = format(addr_num, '08b')
            return mode, addr
        except Exception:
            pass

        return "000", "00000000"

    @staticmethod
    def encodeProgram(program):
        if isinstance(program, str):
            program_lines = program.strip().splitlines()
        else:
            program_lines = program

        expanded_instructions = []
        for line in program_lines:
            expanded_instructions.extend(Instruction.preEncode(line))

        pc = int(storage.register.load("PC"))

        for i, inst in enumerate(expanded_instructions):
            bin_inst = Instruction.encode(inst)
            storage.memory.store(pc + i, bin_inst)

    @staticmethod
    def disassemble(bin_inst):
        if len(bin_inst) != 32:
            raise ValueError(f"Instruction length != 32 bits: {bin_inst}")

        E = bin_inst[0]
        W = bin_inst[1]
        cat = bin_inst[2:5]

        opcode_key = None
        for op_name, (e_, w_, c_) in opcode_map.items():
            if (E, W, cat) == (e_, w_, c_):
                opcode_key = op_name
                break
        if opcode_key is None:
            opcode_key = "???"

        op1Mode = bin_inst[5:8]
        op1Addr = bin_inst[8:16]
        op2Mode = bin_inst[16:19]
        op2Addr = bin_inst[19:27]

        def decode_operand(mode, addr):
            addr_val = int(addr, 2)

            if mode == "000":
                return f"R{addr_val}"
            elif mode == "001":
                return f"@R{addr_val}"
            elif mode == "010":
                return f"&{addr_val}"
            elif mode == "011":
                return f"#{addr_val}"
            elif mode == "100":
                return f"INDX R{addr_val}"
            elif mode == "101":
                return "PUSH"
            elif mode == "110":
                return "POP"
            else:
                return f"UNK_MODE{mode}({addr_val})"

        operands = []
        # Include op1 operand if mode or addr not zero or if opcode expects it
        if op1Mode != "000" or int(op1Addr, 2) != 0 or opcode_key in ["PUSH", "POP", "CALL", "RET", "SCAN", "DEF"]:
            operands.append(decode_operand(op1Mode, op1Addr))
        if op2Mode != "000" or int(op2Addr, 2) != 0:
            operands.append(decode_operand(op2Mode, op2Addr))

        return f"{opcode_key} " + " ".join(operands) if operands else opcode_key
