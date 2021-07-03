const dimensions = 3
const screen_z = 250


function screen_image(point, screen_size)
    w, h = screen_size[1] ÷ 2, screen_size[2] ÷ 2
    # If the point is behind the screen, there can be no image
    if point[3] < screen_z
        return nothing
    end
    # Scale the vector such that it's z-coordinate matches the screen
    scaled = point ./ point[3] .* screen_z
    # Check that the scaled vector is positioned within the borders of the screen
    if -w <= scaled[1] < w && -h <= scaled[2] < h
        return floor(Int32, scaled[1]), floor(Int32, scaled[2])
    end
    return nothing
end


function is_visible(point, center, radius, screen_size)
    # Important: We assume the point is on the sphere!
    if isnothing(screen_image(point, screen_size)) return false end
    # We interpret the point as a vector that can be arbitrarily scaled
    # to make a line through the origin an that point.
    # That way it serves as the parameter to the function 
    # from R to R^3 in the form f(t) := t * point.
    # To get the quadratic equation of the intersection point of this line 
    # with the sphere in the form 0 = a*t^2 + b*t + c, we calculate:
    a = sum(point.^2)
    b = -2 * sum(point .* center)
    c = sum(center.^2) - radius^2
    # The discriminant:
    d = b^2 - 4(a*c)
    # If `d` is less than 0, there is no point of intersection, i.e. the point
    # is not on the sphere at all.
    if d < 0 return false end
    # If `d` is 0, the line is tangent to the sphere, 
    # i.e. there is exactly one point of intersection with the sphere,
    # which can only be our `point`.
    if d == 0 return true end
    # There are two solutions and thus two point of intersection, 
    # one of them must be trivially 1, i.e. the `point` we are investigating.
    # The solutions to the quadratic equation:
    s1 = (-b + sqrt(d)) / 2a
    s2 = (-b - sqrt(d)) / 2a
    # Since we cannot simply compare with 1 due to float inaccuracy 
    # we check which one of the two scalars is closer to 1:
    if abs(1 - s1) > abs(1 - s2)
        other_point = point .* s1
    else 
        other_point = point .* s2
    end
    # We know that the z-coordinate of our `point` is greater than or equal to the 
    # z-coordinate of the screen, or the function would have returned early on.
    # If the z-coordinate of the `other_point` is in between the two,
    # it means the `other_point` is on the face of the sphere closer to the screen,
    # so our `point` of interest is *not* visible.
    # Our `point` is only visible either if it is "in front" of the other,
    # or the other is behind the focus point (i.e. camera inside the sphere)
    return other_point[3] > point[3] || other_point[3] < 0
end


function samples(x, y, w, h, center, radius, density)
    theta = x * π/h
    phi = y * 2π/w
    return [(
        center[1] + radius * sin(theta) * cos(phi), 
        center[2] + radius * sin(theta) * sin(phi), 
        center[3] + radius * cos(theta)
    )]
end


function snapshot_sphere(w, h, data, center, radius, density, snapshot_size)
    # Initialize 2D array of zeros with a length of height * witdth of the snapshot 
    # in the first dimension and a length of 4 (for RGBA) in the second dimension.
    snap_w, snap_h = snapshot_size
    screen = zeros(UInt8, (snap_w * snap_h, 4))
    # Go through each row of the 2D data array, i.e. each pixel
    for (i, pixel) in enumerate(eachrow(data))
        x, y = 1 + (i - 1) % w, 1 + (i - 1) ÷ w
        points = samples(x, y, w, h, center, radius, density)
        for point in points
            if is_visible(point, center, radius, snapshot_size)
                img_x, img_y = screen_image(point, snapshot_size)
                idx = img_x + snap_w ÷ 2 + (img_y + snap_h ÷ 2) * snap_w
                screen[idx, :] = pixel
            end
        end
    end
    return screen
end


# "Placeholder..."
# function snapshot_sphere(w, h, data, center, radius, density, snapshot_size)
#     # For testing purposes we just color the first 100.000 pixels white
#     for (i, a) in enumerate(eachrow(data))
#         a .= 255
#         if i == 100000
#             break
#         end
#     end
#     # ...
#     return data
# end

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
    # Return to stdout:
    write(stdout, transpose(data))
end

main()
