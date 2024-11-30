# Open the input file for reading
with open("output.hex", "r") as infile:
    lines = infile.readlines()

# Convert hexadecimal strings to integers
data = [int(line.strip(), 16) for line in lines[1:]]

# Pad the data list with zeros to make it 256 elements long
data += [0x0000] * (256 - len(data))

# Write the data to the output file in array format
with open("atmega_ins.hex", "w") as outfile:
    outfile.write("{")
    for i, value in enumerate(data):
        if i != 0:
            outfile.write(", ")
        outfile.write("0x{:04x}".format(value))
        if (i + 1) % 16 == 0:  # Add a newline after every 16 entries
            outfile.write("\n")
    outfile.write("}")
