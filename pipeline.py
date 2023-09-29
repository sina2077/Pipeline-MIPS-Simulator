import os
import threading
# Create a lock for synchronization
lock = threading.Lock()

# controll unit
bypass_execute_decode = ["", "", ""]
bypass_memory_decode = ["", ""]
bypass_writeback_decode = ["", ""]
stull = False

def d2b(decimal_num):
   binary_num = bin(decimal_num)[2:] # convert decimal to binary
   # pad with leading zeros to make it a 6-bit number
   padded_binary_num = "0" * (5 - len(binary_num)) + binary_num 
   return padded_binary_num

def b2d(binary_num):
   decimal_num = int(binary_num, 2) # convert binary to decimal
   return decimal_num

# program counter
pc = 32 * "0"

def add_pc():
   global pc
   bin_pc = bin(b2d(pc) + 4)[2:]
   pc = "0" * (32 - len(bin_pc)) + bin_pc
   return pc

beq_bne = False
jump = False

program_memory = []

FetchDecode_registers = []
#calculate next pc and fetch the new instaruction
def Instruction_Fetch():
   global FetchDecode_registers, stull, beq_bne, program_memory, pc, jump
   with lock:
      if stull:
         stull = False
         FetchDecode_registers = []
         return
      
      #return the instruction
      with open(os.getcwd() + '\\Computer architecture\\program_memory.txt', 'r') as Instructions:
         # Iterate over each line
         for line in Instructions:
            program_memory.append(line.strip())
      if jump:
         jump = False
         FetchDecode_registers = [program_memory[int(b2d(pc) / 4)], pc]
      if beq_bne:
         beq_bne = False
         FetchDecode_registers = [program_memory[int(b2d(pc) / 4)], pc]
         print(int(b2d(pc) / 4))
      else:
         #calculate next pc
         FetchDecode_registers = [program_memory[int(b2d(pc) / 4)], add_pc()]

# Decode stage
registers = []
for i in range(32):
   registers.append("0" * 32)
registers[17] = "0" * 31 + "1"

def Sign_Extend(immediate):
   sign_bit = immediate[0]
   if sign_bit == '1':
      # Negative immediate value
      immediate = immediate[1:]
      immediate = immediate.replace('0', 'x').replace('1', '0').replace('x', '1')
      decimal_value = -(int(immediate, 2) + 1)
   else:
      # Positive immediate value
      decimal_value = int(immediate, 2)

   return decimal_value

DecodeExec_registers = []
def Instruction_Decode():
   global DecodeExec_registers, stull, beq_bne, jump, pc
   with lock:
      if FetchDecode_registers == []:
         DecodeExec_registers = []
         return
      instruction, pc = FetchDecode_registers
   # calculate opcode
   opcode = instruction[:6]
   # calculate source register1
   rs_addr = instruction[6:11]
   # calculate source register2
   rt_addr = instruction[11:16]
   # calculate destination register
   rd_addr = instruction[16:21]
   # calculate immediate
   immediate = instruction[16:32]

   # resolving data hazard
   with lock:
      if rs_addr == bypass_execute_decode[0] and bypass_execute_decode[2] == "lw":
         stull = True
         rs = "00000"
      elif rs_addr == bypass_execute_decode[0]:
         rs = bypass_execute_decode[1]
      elif rs_addr == bypass_memory_decode[0]:
         rs = bypass_memory_decode[1]
      elif rs_addr == bypass_writeback_decode[0]:
         rs = bypass_writeback_decode[1]
      else:
         rs = registers[b2d(rs_addr)]
      if rt_addr == bypass_execute_decode[0] and bypass_execute_decode[2] == "lw":
         stull = True
         rt = "00000"
      if rt_addr == bypass_execute_decode[0]:
         rt = bypass_execute_decode[1]
      elif rt_addr == bypass_memory_decode[0]:
         rt = bypass_memory_decode[1]
      elif rt_addr == bypass_writeback_decode[0]:
         rt = bypass_writeback_decode[1]
      else:
         rt = registers[b2d(rt_addr)]

      # resolving control hazard

      # taken beq
      if b2d(opcode) == 4 and rs == rt:
         beq_bne = True
         pc = d2b(Sign_Extend(immediate) * 4 + b2d(pc) + 4)
      # taken bne
      elif b2d(opcode) == 5 and rs != rt:
         beq_bne = True
         pc = d2b(Sign_Extend(immediate) * 4 + b2d(pc) + 4)
      # jump
      elif b2d(opcode) == 2:
         jump = True
         pc = d2b(Sign_Extend(immediate) * 4)
      
   DecodeExec_registers = [opcode, rs, rt, rt_addr, rd_addr, Sign_Extend(immediate), pc, instruction]

# Execute stage
memory = []
for i in range(20):
   memory.append("0" * 32)

def I_Type(rs, rt, instruction, sign_extend_immediate, pc):
   Instruction_Table = {
      8: "addi",
      12: "andi",
      13: "ori",
      10: "slti",
      4: "beq",
      5: "bne",
      35: "lw",
      43: "sw"
   }
   # check the opcode
   opcode_mean = Instruction_Table[b2d(instruction[:6])]

   # addi
   if opcode_mean == "addi":
      result = d2b(b2d(rs) + sign_extend_immediate)
      result = "0" * (32 - len(result)) + result
   # andi
   elif opcode_mean == "andi":
      result = d2b(b2d(rs) & sign_extend_immediate)
      result = "0" * (32 - len(result)) + result 
   # ori
   elif opcode_mean == "ori":
      result = d2b(b2d(rs) | sign_extend_immediate)
      result = "0" * (32 - len(result)) + result
   # slti
   elif opcode_mean == "slti":
      if b2d(rs) < sign_extend_immediate:
         result = "0" * 31 + "1"
      else:
         result = "0" * 32
   # beq
   elif opcode_mean == "beq":
      result = ""
   # bne
   elif opcode_mean == "bne":
      if b2d(rs) != b2d(rt):
         pc = d2b(b2d(pc) + 4 * sign_extend_immediate)
   # lw
   elif opcode_mean == "lw":
      result = d2b(sign_extend_immediate + b2d(rs))
   # sw
   elif opcode_mean == "sw":
      result = d2b(sign_extend_immediate + b2d(rs))
   
   return result, opcode_mean

def J_Type(jump_addr):
   global pc
   result = bin(b2d(jump_addr) * 4 + b2d(pc))[2:]
   result = "0" * (32 - len(result)) + result
   return result, "jump"

def R_Type(rs, rt, instruction):
   global pc
   Instruction_Table = {
      32: "add",
      34: "sub",
      37: "or",
      36: "and",
      42: "slt"
   }
   # check the opcode
   opcode_mean = Instruction_Table[b2d(instruction[26:])]

   if opcode_mean == "add":
      result = d2b(b2d(rs) + b2d(rt))
   elif opcode_mean == "sub":
      result = d2b(b2d(rs) - b2d(rt))
   elif opcode_mean == "or":
      result = d2b(b2d(rs) | b2d(rt))
   elif opcode_mean == "and":
      result = d2b(b2d(rs) & b2d(rt))
   elif opcode_mean == "slt":
      if b2d(rs) < b2d(rt):
         result = "0" * 31 + "1"
      else:
         result = "0" * 32
   result = "0" * (32 - len(result)) + result
   return result, opcode_mean

ExecuteMemory_registers = []
def Execute():
   global ExecuteMemory_registers, bypass_execute_decode
   if DecodeExec_registers == []:
      ExecuteMemory_registers = []
      return
   opcode, rs, rt, rt_addr, rd_addr, Sign_Extend_immediate, pc, instraction = DecodeExec_registers
   if opcode == "000000":
      result, opcode_mean = R_Type(rs, rt, instraction)
      ExecuteMemory_registers = [result, opcode_mean, rd_addr]
      # resolving data hazard
      with lock:
         bypass_execute_decode = [rd_addr, result, ""]
   elif opcode == "000010" or opcode == "000011":
      result, opcode_mean = J_Type(instraction[6:])
      ExecuteMemory_registers = [result, opcode_mean, ""]   
   else:
      result, opcode_mean = I_Type(rs, rt, instraction, Sign_Extend_immediate, pc)
      ExecuteMemory_registers = [result, opcode_mean, rt_addr]
      with lock:
         bypass_execute_decode = [rt_addr, result, opcode_mean]

MemoryWriteBack_registers = []
# memory stage
def Memory_Access():
   global pc
   global MemoryWriteBack_registers, bypass_memory_decode
   if ExecuteMemory_registers == []:
      MemoryWriteBack_registers = []
      return
   result, opcode_mean, dest_reg = ExecuteMemory_registers
   if opcode_mean == "jump":
      pc = result
   elif opcode_mean == "lw":
      MemoryWriteBack_registers = [memory[b2d(result)], dest_reg]
      with lock:
         bypass_memory_decode = MemoryWriteBack_registers[::-1]
   elif opcode_mean == "sw":
      memory[b2d(result)] = dest_reg
   else:
      MemoryWriteBack_registers = [result, dest_reg]
   
# wirte back stage
def Write_Back():
   global bypass_writeback_decode
   if MemoryWriteBack_registers == []:
      return
   result, dest_reg = MemoryWriteBack_registers
   with lock:
      bypass_writeback_decode = MemoryWriteBack_registers[::-1]
   registers[b2d(dest_reg)] = result

# Create a list of the functions
all_simulations = [Instruction_Fetch, Instruction_Decode, Execute, Memory_Access, Write_Back]

for i in range(8):
   simulate = all_simulations
   if i < 4:
      simulate = simulate[:(i+1)]
   # Create a list to hold the threads
   threads = []

   # Create and start the threads
   for function in simulate[::-1]:
      thread = threading.Thread(target=function)
      thread.start()
      threads.append(thread)

   # Wait for all threads to complete
   for thread in threads:
      thread.join()

print("End")