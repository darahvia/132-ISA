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

            if op in ["DEF", "DEV", "DEB"]:
                continue

            if op in ["JEQ", "JNE", "JLT", "JLE", "JGT", "JGE"] and len(parts) == 4:
                x, y, z = parts[1], parts[2], parts[3]
                output.append(f"SUB {x} {y}")
                output.append(f"{op} {z}")
                continue

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

            output.append(" ".join(new_parts))

        return output

    @staticmethod
    def encode(inst):
        parts = inst.strip().split()
        if not parts:
            return "0" * Length.instrxn  # empty fallback

        op = parts[0].upper()

        opcode = ""
        found = False
        for i, group in enumerate(operations):
            if op in group:
                e_bit = operationCodes[0][i]  # 2 bits
                w_bit = operationCodes[1][group.index(op)]  # 3 bits
                opcode = e_bit + w_bit  # 5 bits total
                found = True
                break
        if not found:
            raise Exception(f"Unknown operation: {op}")

        op1Mode, op2Mode = "000", "000"
        op1Addr, op2Addr = "00000000", "00000000"

        if len(parts) == 2:
            op1Mode, op1Addr = Instruction.encodeOp(parts[1])
        elif len(parts) == 3:
            op1Mode, op1Addr = Instruction.encodeOp(parts[1])
            op2Mode, op2Addr = Instruction.encodeOp(parts[2])

        bin_str = opcode + op1Mode + op1Addr + op2Mode + op2Addr + "0" * 5

        if len(bin_str) != 32:
            raise AssertionError(f"Instruction not 32 bits: {inst} → {bin_str} (length {len(bin_str)})")

        return bin_str

    @staticmethod
    def encodeOp(operand):
        # Handle indirect (@), direct (&), immediate (#), indexed, register, symbolic, stack, etc.

        operand = operand.strip()

        # Stack operations PUSH or POP encoded as mode 101 or 110, address is SPR (assumed 255)
        if operand == "PUSH":
            return "101", format(255, '08b')
        if operand == "POP":
            return "110", format(255, '08b')

        if operand.startswith("@"):  # indirect register, e.g. @R3
            mode = "001"  # register indirect
            reg = operand[2:] if operand[1] == 'R' else operand[1:]  # support @R3 or @3
            if reg.startswith("R"):
                reg_num = int(reg[1:])
            else:
                reg_num = int(reg)
            addr = format(reg_num, '08b')
            return mode, addr

        if operand.startswith("&"):  # direct memory address stored in register or symbol
            # &R5 or &x (symbolic)
            target = operand[1:]
            if target.startswith("R"):
                mode = "010"  # direct addressing mode
                reg_num = int(target[1:])
                addr = format(reg_num, '08b')
            else:
                # symbolic variable or label
                mode = "010"
                try:
                    addr_num = int(storage.variable.load(target))
                except Exception:
                    addr_num = 0
                addr = format(addr_num, '08b')
            return mode, addr

        if operand.startswith("#"):  # immediate value
            mode = "011"
            imm_val = int(operand[1:])
            addr = format(imm_val, '08b')
            return mode, addr

        if operand.startswith("INDX1"):  # indexed addressing 1
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

        if operand.startswith("INDX2"):  # indexed addressing 2
            parts = operand.split()
            if len(parts) != 2:
                raise Exception(f"Invalid INDX2 operand format: {operand}")
            base = parts[1]
            mode = "101"
            if base.startswith("R"):
                reg_num = int(base[1:])
            else:
                try:
                    reg_num = int(storage.variable.load(base))
                except:
                    reg_num = 0
            addr = format(reg_num, '08b')
            return mode, addr

        if operand.startswith("R"):  # register direct
            mode = "000"
            reg_num = int(operand[1:])
            addr = format(reg_num, '08b')
            return mode, addr

        # Symbolic variable or label
        try:
            addr_num = int(storage.variable.load(operand))
            mode = "010"  # direct memory
            addr = format(addr_num, '08b')
            return mode, addr
        except Exception:
            pass

        # Default fallback
        return "000", "00000000"

    @staticmethod
    def encodeProgram(program):
        program = Instruction.preEncode(program)
        pc = int(storage.register.load("PC"))
        for i, inst in enumerate(program):
            bin_inst = Instruction.encode(inst)
            storage.memory.store(pc + i, bin_inst)
