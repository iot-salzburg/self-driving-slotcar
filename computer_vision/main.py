import cv2
import numpy as np
from matplotlib import pyplot as plt
from os.path import exists, join
from os import makedirs
import pickle

a = np.array([0, 0], dtype='float32')


def remove_fisheye(img):
    K = np.array([[1001.7792, 0., 962.3616],
                  [0., 1012.7232, 561.2760],
                  [0., 0., 1.]])

    # zero distortion coefficients work well for this image
    D = np.array([-0.31331 * 0.5, 0.12965, 0.00073, -0.00022])

    # use Knew to scale the output
    Knew = K.copy()
    Knew[(0, 1), (0, 1)] = 0.4 * Knew[(0, 1), (0, 1)]

    return cv2.fisheye.undistortImage(img, K, D=D, Knew=Knew)
    # return img

# noinspection PyArgumentList
def compute_transformation(video_file, debug=False):
    """ Computes the proper transformation by letting the user select appropriate points in the image """

    # noinspection PyCompatibility

    def get_coords(select_image):
        # noinspection PyCompatibility
        def getxy(event, row, col, flags, param):
            global a
            if event == cv2.EVENT_LBUTTONDOWN:
                a = np.vstack([a, np.hstack([row, col])])
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
        selected_points = a[1:, :]
        return np.float32(selected_points)

    cap = cv2.VideoCapture(1)
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
    dst = cv2.warpPerspective(img, transformation, (6000, 9000))

    if debug:
        plt.figure()
        plt.imshow(cv2.cvtColor(distorted_img, cv2.COLOR_BGR2RGB))
        plt.figure()
        plt.imshow(cv2.cvtColor(dst, cv2.COLOR_BGR2RGB))
        plt.show()

    cap.release()
    cv2.destroyAllWindows()

    return transformation


# noinspection PyArgumentList
def convert_video(video_file, debug=False):
    """ Normalises each frame in the given video files """

    makedirs('output', exist_ok=True)

    # compute transformation matrix
    transformation_file = join('output', 'transformation_' + video_file + '.pickle')
    if exists(transformation_file):
        with open(transformation_file, 'rb') as pickle_file:
            transformation = pickle.load(pickle_file)
    else:
        transformation = compute_transformation(video_file=video_file, debug=debug)
        with open(transformation_file, 'wb') as pickle_file:
            pickle.dump(transformation, pickle_file)

    # output definition
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(join('output', 'result.avi'), fourcc, 5.0, (6000, 7000))

    cap = cv2.VideoCapture(1)

    frame_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if ret:

            # remove fisheye distortion
            frame = remove_fisheye(frame)
            dst = cv2.warpPerspective(frame, transformation, (6000, 7000))

            plt.imshow(cv2.cvtColor(dst, cv2.COLOR_BGR2RGB))
            plt.show()
            # out.write(dst)

            print('writing frame ', frame_count)
            frame_count += 1
        else:
            break

    # Release everything if job is finished
    cap.release()
    out.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    convert_video(video_file='output_2.m4v', debug=True)
