import cv2

import ffmpeg

# Initial values for k1 and k2
k1 = -0.125
k2 = 0.02
hwaccel = "vulkan"
done = False

while not done:
    (
        ffmpeg.input("../../static/projects/441.jpeg", hwaccel=hwaccel)
        .output("out.png", vf=f"scale=1280:720,lenscorrection=k1={k1}:k2={k2}")
        .global_args("-y")
        .run()
    )
    image = cv2.imread("../../static/projects/out.png")
    cv2.imshow('Image', image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    print(f"Current {k1=}, {k2=}")
    try:
        k1 = float(input("change k1: "))

    except ValueError:
        pass

    try:
        k2 = float(input("change k2: "))

    except ValueError:
        pass
