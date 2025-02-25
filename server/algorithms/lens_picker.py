import cv2

import ffmpeg

# Initial values for k1 and k2
k1 = -0.125
k2 = 0.02

k1=-0.225
k2=0.025
hwaccel = "auto"
done = False

# Skip frames to
# cap = cv2.VideoCapture('path/to/video/file')
# start_frame_number = 50
# For timestamps cv.CAP_PROP_POS_MSEC can be used
# cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame_number)
# done = False
# ffmpeg.input("E:\Photo\Concert 26.09.2021\VID_20210926_214140.mp4", hwaccel=hwaccel).output("test_fetch_frame.mp4", frames="260", ss="15", preset="fast", crf="27", vf=f"scale=1280:720,lenscorrection=k1=-0.3223:k2=0.55").global_args("-y").run()


while done:
    (
        ffmpeg.input(r"H:\ai\diploma_test\14-41-29 2023-01-15.mkv", hwaccel=hwaccel)
        .output(
            "test_video_frame.mp4", vf=f"scale=3840:2160,lenscorrection=k1={k1}:k2={k2}",
            frames="1200", ss="15", preset="fast", crf="27",
        )
        .global_args("-y")
        .run()
    )
    image = cv2.imread("out.png")
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

if not done:
    cap = cv2.VideoCapture("../../test_fetch_frame.mp4")
    while cap.isOpened():
        ret, frame = cap.read()

        if not ret:
            break

        cv2.imshow("Frame", frame)
        cv2.waitKey()
        cv2.destroyAllWindows()
