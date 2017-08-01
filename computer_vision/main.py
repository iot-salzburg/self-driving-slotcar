import cv2
import numpy as np
from matplotlib import pyplot as plt
from os.path import exists, join
from os import makedirs
import pickle

image_selection = np.array([0, 0], dtype='float32')
OUTPUT_SIZE = [6000, 9000]


def remove_fisheye(img):
    K = np.array([[1001.7792, 0., 962.3616],
                  [0., 1012.7232, 561.2760],
                  [0., 0., 1.]])

    # zero distortion coefficients work well for this image
    D = np.array([-0.31331, 0.12965, 0.00073, -0.00022])

    # use Knew to scale the output
    Knew = K.copy()
    Knew[(0, 1), (0, 1)] = 0.4 * Knew[(0, 1), (0, 1)]

    # return cv2.fisheye.undistortImage(img, K, D=D, Knew=Knew)
    return img


# noinspection PyArgumentList
def compute_transformation(video_file, debug=False):
    """ Computes the proper transformation by letting the user select appropriate points in the image """

    # noinspection PyCompatibility

    def get_coords(select_image):
        # noinspection PyCompatibility
        def getxy(event, row, col, flags, param):
            global image_selection
            if event == cv2.EVENT_LBUTTONDOWN:
                image_selection = np.vstack([image_selection, np.hstack([row, col])])
                cv2.circle(select_image, (row, col), 3, (0, 0, 255), -1)
                cv2.imshow('image', select_image)
                print("(row, col) = ", (row, col))

        # Read the image

        # Set mouse CallBack event
        cv2.namedWindow('image')
        cv2.setMouseCallback('image', getxy)

        # show the image
        print("Click to select a point OR press ANY KEY to continue...")
        cv2.imshow('image', img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

        # obtain the matrix of the selected points
        selected_points = image_selection[1:, :]
        return np.float32(selected_points)

    cap = cv2.VideoCapture(video_file)
    ret, distorted_img = cap.read()

    # remove fisheye distortion
    img = remove_fisheye(distorted_img)

    plt.figure()
    plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    # compute corner pairs
    original_corners = get_coords(img)
    print(np.array(original_corners))
    new_corners = np.float32([[0., 0.], [210., 0.], [210., 297.], [0., 297.]]) * 4. + 4200.

    # perform homography
    transformation = cv2.getPerspectiveTransform(original_corners, new_corners)
    dst = cv2.warpPerspective(img, transformation, tuple(OUTPUT_SIZE))

    if debug:
        plt.figure()
        plt.imshow(cv2.cvtColor(distorted_img, cv2.COLOR_BGR2RGB))
        plt.figure()
        plt.imshow(cv2.cvtColor(dst, cv2.COLOR_BGR2RGB))
        plt.show()

    cap.release()
    cv2.destroyAllWindows()

    return transformation


def pre_process_image(img, transformation, largest_contour):
    """ processes image for further evalution """

    # remove fisheye distortion
    frame = remove_fisheye(img)

    # apply perspective warping
    dst = cv2.warpPerspective(frame, transformation, tuple(OUTPUT_SIZE))

    # get region of interest
    cropped = dst[1050:-950, 3500:6200]
    dst = cropped.copy()

    # find largest contour
    if largest_contour is None:
        hsv = cv2.cvtColor(dst, cv2.COLOR_BGR2HSV)
        lower_range = np.array([0, 0, 0], dtype=np.uint8)
        upper_range = np.array([255, 255, 70], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower_range, upper_range)

        # close blobs
        kernel = np.ones((40, 40), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        _, contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        largest_contour = max(contours, key=cv2.contourArea)

    mask = np.zeros(dst.shape, np.uint8)
    cv2.drawContours(mask, [largest_contour], 0, 255, -1)
    mask = mask[:, :, 0]

    res = cv2.bitwise_and(dst, dst, mask=mask)

    return res, cropped, largest_contour


def detect_car(fgbg, frame):
    # substract background
    fgmask = fgbg.apply(frame)

    # close masks
    kernel = np.ones((15, 15), np.uint8)
    fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel)
    kernel = np.ones((50, 50), np.uint8)
    fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_DILATE, kernel)

    # find largest contour and compute centroid
    cx, cy = (0, 0)
    _, contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)

        # compute centroid of contour
        moment = cv2.moments(largest_contour)
        cx = int(moment['m10'] / moment['m00'])
        cy = int(moment['m01'] / moment['m00'])

    return (cx, cy), fgmask


def detect_center_coords(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_range = np.array([0, 0, 200], dtype=np.uint8)
    upper_range = np.array([255, 255, 255], dtype=np.uint8)
    mask = cv2.inRange(hsv, lower_range, upper_range)

    _, contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cx, cy = (0, 0)
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)

        # compute centroid of contour
        moment = cv2.moments(largest_contour)
        cx = int(moment['m10'] / moment['m00'])
        cy = int(moment['m01'] / moment['m00'])

    return (cx, cy), mask


# noinspection PyArgumentList
def convert_video(video, debug=False):
    """ Normalises each frame in the given video files """

    makedirs('output', exist_ok=True)

    # compute transformation matrix
    transformation_file = join('output', 'transformation_' + str(video) + '.pickle')
    if exists(transformation_file):
        with open(transformation_file, 'rb') as pickle_file:
            transformation = pickle.load(pickle_file)
    else:
        transformation = compute_transformation(video_file=video, debug=debug)
        with open(transformation_file, 'wb') as pickle_file:
            pickle.dump(transformation, pickle_file)

    # output definition
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(join('output', 'result.avi'), fourcc, 1.0, (700, 1000))

    fgbg = cv2.createBackgroundSubtractorMOG2()

    cap = cv2.VideoCapture(video)
    largest_contour = None
    center_coords = None
    frame_counter = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if ret:

            # perform pre-processing
            pre_processed_image, cropped_image, largest_contour = pre_process_image(frame,
                                                                                    transformation,
                                                                                    largest_contour)

            # detect car
            car_coords, car_mask = detect_car(fgbg, pre_processed_image)

            # detect coords of center
            if center_coords is None:
                center_coords, center_mask = detect_center_coords(pre_processed_image)

            # show results when ready
            if frame_counter > 3:
                cv2.line(cropped_image, center_coords, car_coords, (255, 0, 0), 10)
                cv2.circle(cropped_image, car_coords, 30, (0, 0, 255), -1)
                cv2.circle(cropped_image, center_coords, 30, (0, 255, 255), -1)

            to_show = np.concatenate((cropped_image,
                                      pre_processed_image,
                                      cv2.bitwise_and(pre_processed_image, pre_processed_image, mask=center_mask),
                                      cv2.bitwise_and(pre_processed_image, pre_processed_image, mask=car_mask)),
                                     axis=1)
            cv2.imshow('converted video', cv2.resize(to_show, (0, 0), fx=0.15, fy=0.15))
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            frame_counter += 1
            out.write(cv2.resize(to_show, (0, 0), fx=0.1, fy=0.1))
        else:
            break

    # Release everything if job is finished
    cap.release()
    out.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    convert_video(video=0, debug=True)
