import storage
from convert import Precision

class Access:
    @staticmethod
    def data(addr, flow=["var"]):
        """
        Loads the value that follows the flow from the specified address.
        Flow options: "var" (variable), "reg" (register), "mem" (memory)
        """
        for flow_type in flow:
            try:
                if flow_type == "var":
                    # First try to get address from variable storage
                    actual_addr = storage.variable.load(addr)
                    return storage.register.load(int(actual_addr))
                elif flow_type == "reg":
                    return storage.register.load(int(addr))
                elif flow_type == "mem":
                    return storage.memory.load(int(addr))
            except KeyError:
                continue
        
        # If all flow types fail, raise an exception
        raise KeyError(f"Address {addr} not found in any of the specified storage types: {flow}")
    
    def store(typ, addr, value):
        """
        Store the value to the specified storage (memory or register) and address.
        typ: "reg" for register, "mem" for memory, "var" for variable
        """
        if typ == "reg":
            storage.register.store(addr, value)
        elif typ == "mem":
            storage.memory.store(addr, value)
        elif typ == "var":
            # For variable, store the mapping in variable storage
            storage.variable.store(addr, value)
        else:
            raise ValueError(f"Invalid storage type: {typ}")

class AddressingMode:
    @staticmethod
    def immediate(var):
        """
        Immediate addressing mode - returns the value directly
        """
        return var
    
    def indexed(displace):
        """
        Indexed addressing mode with displacement from index register
        """
        try:
            # Get the index register value (I1 for first operand, I2 for second)
            index_addr = storage.variable.load("I1")  # Default to I1
            index_value = storage.register.load(int(index_addr))
            
            # Calculate effective address using Precision for proper conversion
            effective_addr = int(Precision.spbin2dec(Precision.dec2spbin(displace + index_value)))
            
            # Return the value at the effective address
            return storage.memory.load(int(effective_addr))
        except KeyError:
            raise KeyError(f"Index register not found or invalid displacement")
    
    def register(reg_addr):
        """
        Register addressing mode - returns value from register at reg_addr
        """
        return storage.register.load(int(reg_addr))
    
    def register_indirect(reg_addr):
        """
        Register indirect addressing mode - register contains address of actual data
        """
        # Get address from register (already converted by storage.load)
        addr = storage.register.load(int(reg_addr))
        # Convert to integer address using Precision
        mem_addr = int(Precision.spbin2dec(Precision.dec2spbin(addr)))
        # Use that address to get the actual value from memory
        return storage.memory.load(int(mem_addr))
    
    def direct(var_addr):
        """
        Direct addressing mode - direct access to memory address var_addr
        """
        return storage.memory.load(int(var_addr))
    
    def indirect(var_addr):
        """
        Indirect addressing mode - memory location contains address of actual data
        """
        # Get address from memory (already converted by storage.load)
        addr = storage.memory.load(int(var_addr))
        # Convert to integer address using Precision
        mem_addr = int(Precision.spbin2dec(Precision.dec2spbin(addr)))
        # Use that address to get the actual value
        return storage.memory.load(int(mem_addr))
    
    def autoinc(reg_addr):
        """
        Auto-increment addressing mode - use register value then increment it
        """
        # Get current value from register (already converted by storage.load)
        addr = storage.register.load(int(reg_addr))
        # Convert to integer address for memory access
        mem_addr = int(Precision.spbin2dec(Precision.dec2spbin(addr)))
        # Get data from memory at that address
        data = storage.memory.load(int(mem_addr))
        # Increment the register value using Precision
        incremented = Precision.spbin2dec(Precision.dec2spbin(addr + 1))
        storage.register.store(reg_addr, incremented)
        return data
    
    def autodec(reg_addr):
        """
        Auto-decrement addressing mode - decrement register then use its value
        """
        # Get current value from register and decrement using Precision
        current_addr = storage.register.load(int(reg_addr))
        decremented = Precision.spbin2dec(Precision.dec2spbin(current_addr - 1))
        # Store decremented value back to register
        storage.register.store(reg_addr, decremented)
        # Convert to integer address for memory access
        mem_addr = int(Precision.spbin2dec(Precision.dec2spbin(decremented)))
        # Get data from memory at decremented address
        return storage.memory.load(int(mem_addr))
    
    @staticmethod
    def stack(value=None, action=None):
        """
        Stack addressing mode with stack option (push, pop, or top).
        Pop and top return the address of the stack top.
        Push inserts the value at the stack top while pop removes the value from the stack.
        Uses SPR (Stack Pointer Register) and TSP (Top Stack Pointer)
        """
        # Get stack pointer addresses
        spr_addr = storage.variable.load("SPR")
        tsp_addr = storage.variable.load("TSP")
        
        # Get current stack pointer and top stack pointer (already converted by storage.load)
        stack_ptr = storage.register.load(int(spr_addr))
        top_stack_ptr = storage.register.load(int(tsp_addr))
        
        if action is None:
            raise ValueError("Stack action must be specified as 'push', 'pop', or 'top'")
        
        if action.lower() == "push":
            # Push: increment TSP and store the new value on top of stack
            new_top = top_stack_ptr + 1
            storage.register.store(tsp_addr, new_top)
            if value is not None:
                # Store the pushed value in memory at the new top address
                storage.memory.store(new_top, value)
            return new_top
            
        elif action.lower() == "pop":
            # Pop: check for underflow
            if top_stack_ptr <= stack_ptr:
                raise RuntimeError("Stack underflow - cannot pop from empty stack")
            # Get the current top value before decrementing
            popped_value = storage.memory.load(top_stack_ptr)
            decremented = top_stack_ptr - 1
            storage.register.store(tsp_addr, decremented)
            return popped_value
            
        elif action.lower() == "top":
            # Top: return current top value without modification
            if top_stack_ptr <= stack_ptr:
                return None
            return storage.memory.load(top_stack_ptr)
            
        else:
            raise ValueError(f"Invalid stack action: {action}. Use 'push', 'pop', or 'top'")
