import os
import sys

instruction_type = {
	"and": ("R", "0000"),
	"andi": ("I", "0001"),
	"beq": ("I", "0010"),
	"j": ("J", "0011"),
	"bneq": ("I", "0100"),
	"sub": ("R", "0101"),
	"subi": ("I", "0110"),
	"addi": ("I", "0111"),
	"sll": ("S", "1000"),
	"or": ("R", "1001"),
	"add": ("R", "1010"),
	"ori": ("I", "1011"),
	"lw": ("I", "1100"),
	"srl": ("S", "1101"),
	"nor": ("R", "1110"),
	"sw": ("I", "1111"),
}

register_map = {
	"$zero": "0000",
	"$t0": "0001",
	"$t1": "0010",
	"$t2": "0011",
	"$t3": "0100",
	"$t4": "0101",
	"$t5": "0110", 
	"$sp": "0111"
}


labels = dict()

def bin_to_hex(*argv):
	result = ''
	for arg in argv:
		result += hex(int(arg, 2))[2:]
	return result

def handle_IRS_type(instruction_sep, fmt, i)->str:
	instruction_name, r1 = instruction_sep[0].split(' ')
	instruction_name = instruction_name.strip()
	if instruction_name == 'lw' or instruction_name == 'sw':
		return handle_lwsw(instruction_sep)

	opcode = instruction_type.get(instruction_name)[1]
	r1 = register_map.get(r1.strip())
	r2 = register_map.get(instruction_sep[1].strip())
	r3 = instruction_sep[2].strip()

	if fmt == 'R':
		r3 = register_map.get(r3)
		return bin_to_hex(opcode, r2, r3, r1)
	if instruction_name == 'beq' or instruction_name == 'bneq':
		jmp_to = labels.get(r3)
		if i < jmp_to:
			r3 = jmp_to - i - 1
		else:
			r3 = i - jmp_to + 1
			r3 = (1 << 4) - r3 #twos complement
	r3 = int(r3)
	r3 = ((1<<4) + r3) if r3<0 else r3
	r3 = bin(r3)[2:].zfill(4)

	return bin_to_hex(opcode, r2, r1, r3)

def handle_lwsw(instruction_sep)->str:
	instruction_name, r2 = instruction_sep[0].split(' ')
	instruction_name = instruction_name.strip()

	opcode = instruction_type.get(instruction_name)[1]
	r2 = register_map.get(r2.strip())
	r1 = instruction_sep[1].strip()
	start = r1.find('(')
	end = r1.find(')')
	shmt = int(r1[:start])
	shmt = bin(shmt)[2:].zfill(4)
	r1 = register_map.get(r1[start+1:end])
	return bin_to_hex(opcode, r1, r2, shmt)

def handle_J_type(instruction_sep, i)->str:
	instruction_name, jmpaddr = instruction_sep[0].split(' ')[:2]
	instruction_name = instruction_name.strip()
	jmpaddr = labels.get(jmpaddr.strip())

	opcode = instruction_type.get(instruction_name)[1]
	# jmpaddr = bin(jumpaddr)[2:].zfill(8)
	return bin_to_hex(opcode) + hex(jmpaddr)[2:].zfill(2) + '0'

def get_src_of_push_pop(inst):
	inst = inst.split(' ')
	inst[1]=inst[1].strip()
	return inst[1]

def mips_to_machine(inst:str, i=-1)->str:
	comma_sep = inst.split(',')
	instruction_name = comma_sep[0].split(' ')[0].strip()
	if instruction_name in ['push', 'pop']:
		return get_src_of_push_pop(inst)
	if instruction_name not in instruction_type:
		print('Invalid instruction: ' + instruction_name)
		exit(1)
	fmt, opcode = instruction_type.get(instruction_name)
	if fmt=='R' or fmt=='I' or fmt=='S':
		return handle_IRS_type(comma_sep, fmt, i)
	else:
		return handle_J_type(comma_sep, i)

def main():
	# # Ensure input file is provided as command line argument
	# if len(sys.argv) != 2:
	#     print("Usage: python script_name.py input_file_name.asm")
	#     sys.exit(1)

	script_directory = os.path.dirname(os.path.abspath(__file__))
	hex_file_path = os.path.join(script_directory, "output.hex")
	intermediate_file_path = os.path.join(script_directory, "intermediate.asm")
	
	line_count = 0

	input_file_name = "input.asm"
	input_file_path = os.path.join(script_directory, input_file_name)

	try:
		with open(input_file_path, 'r') as asm_input:
			fout = open(hex_file_path, 'w')
			fout.write('v2.0 raw\n')
			# fout.write('a001\na002\na003\na004\na005\n707f\n')
			mips_code = asm_input.readlines()

			# Replace push_pop
			for i, line in enumerate(mips_code):
				if 'push' in line:
					reg = line.split()[1]  # Extract the register from the push instruction
					if '(' in reg:  # If it's in the format "push offset($reg)"
						offset, reg = reg.split('(')
						reg = reg[:-1]  # Remove the closing parenthesis
						mips_code[i:i+1] = [
							f'lw $t5, {offset}({reg})\n',
							'sw $t5, 0($sp)\n',
							'subi $sp, $sp, 1\n'
						]
					else:  # If it's just "push $reg"
						mips_code[i:i+1] = [
							f'sw {reg}, 0($sp)\n',
							'subi $sp, $sp, 1\n'
						]
				elif 'pop' in line:
					reg = line.split()[1]  # Extract the register from the pop instruction
					mips_code[i:i+1] = [
						'addi $sp, $sp, 1\n',
						f'lw {reg}, 0($sp)\n'
					]

			# Save push_pop parsed code
			intermediate = open(intermediate_file_path, 'w')
			intermediate.writelines(mips_code)
			intermediate.close()

			# Find labels
			for i, line in enumerate(mips_code):
				if line == "":
					continue
				line = line.strip()
				colon = line.find(':')
				if colon != -1:
					labels[line[:colon]] = i

			# Convert MIPS to machine code
			for i, line in enumerate(mips_code):
				cmnt = line.find(';')  # strip comments
				if cmnt != -1:
					line = line[:cmnt].strip()
				line_count += 1
				print("Line #" + str(line_count) + ":\n")
				print(line + '' if line.endswith('\n') else '\n')

				# Check if any labels
				colon_start = line.find(':')
				if colon_start != -1:
					line = line[colon_start + 1:].strip()  # strip label

				if line == "":  # if no instruction after label, then exit
					xcode = '0000'
				else:  # else convert inst to xcode
					xcode = mips_to_machine(line, i)

				print("Machine code: " + xcode + "\n\n")
				fout.write(xcode + '\n')

			fout.close()

	except FileNotFoundError:
		print("Input file not found.")
		sys.exit(1)

if __name__ == "__main__":
	main()