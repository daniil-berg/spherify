const dimensions = 3

"Placeholder..."
function snapshot_sphere(w, h, data, center, radius, density, snapshot_size)
    # For testing purposes we just color the first 100.000 pixels white
    for (i, a) in enumerate(eachrow(data))
        a .= 255
        if i == 100000
            break
        end
    end
    # ...
    return data
end

"""
Parse and convert command line arguments, read image data, 
perform sanity checks, and start the calculations.
Image data must be supplied via standard input.
"""
function main()
    if length(ARGS) != 5
        error(
            "5 arguments required: " * 
            "image_size, center, radius, density, snapshot_size"
        )
    end
    # Parse and convert string arguments to usable types:
    w, h = parse.(Int32, split(ARGS[1], ","))
    center = parse.(Float32, split(ARGS[2], ","))
    radius = parse(Float32, ARGS[3])
    density = parse(Int32, ARGS[4])
    snapshot_size = parse.(Int32, split(ARGS[5], ","))
    # Perform sanity checks, starting with the dimensions of the center point:
    if length(center) != dimensions
        error("Center point must be a $dimensions-tuple of numbers")
    end
    # Read the image data as a bytes sequence from standard input;
    # this assumes every pixel to be represented by exactly 4 bytes of data,
    # which correspond to its RGBA value:
    data = read(stdin, typemax(Int32))  # cap at an equivalent of 2 GB
    if sizeof(data) % 4 != 0
        error("Number of provided bytes must be a multiple of 4!")
    end
    # Make a vector of 4-byte-chunks out of the provided data:
    pixels = transpose(reshape(data, 4, :))
    # The number of 4-byte-chunks must correspond to the specified dimensions:
    num_pixels = size(pixels)[1]
    if num_pixels != w * h
        error(
            "Number of 4-byte strides $num_pixels " * 
            "does not match provided width and height of $w x $h"
        )
    end
    # Start the calculations:
    data = snapshot_sphere(w, h, pixels, center, radius, density, snapshot_size)
    write(stdout, transpose(data))
end

main()
