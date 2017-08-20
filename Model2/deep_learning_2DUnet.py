from __future__ import print_function

import numpy as np
from keras.models import Model
from keras.layers import Input, merge, Convolution2D, MaxPooling2D, UpSampling2D
from keras.optimizers import Adam
from keras.optimizers import SGD
from keras.callbacks import ModelCheckpoint, LearningRateScheduler
from keras import backend as K
import os
import cv2
from keras.layers.normalization import BatchNormalization
from keras.layers.core import Dropout

output_path="D:\Shi\python\TMCI\pulmonary-nodules-segmentation-master/data/output/"

K.set_image_dim_ordering('th')  # Theano dimension ordering in this code

img_rows = 512
img_cols = 512

smooth = 0.1

def dice_coef(y_true, y_pred):
    y_true_f = K.flatten(y_true)
    y_pred_f = K.flatten(y_pred)
    intersection = K.sum(y_true_f * y_pred_f)
    return (2. * intersection + smooth) / (K.sum(y_true_f) + K.sum(y_pred_f) + smooth)


def dice_coef_np(y_true, y_pred):
    y_true_f = y_true.flatten()
    y_pred_f = y_pred.flatten()
    intersection = np.sum(y_true_f * y_pred_f)
    return (2. * intersection + smooth) / (np.sum(y_true_f) + np.sum(y_pred_f) + smooth)


def dice_coef_loss(y_true, y_pred):
    return -dice_coef(y_true, y_pred)

def dice_coef_loss2(y_true, y_pred):
    return 1-dice_coef(y_true, y_pred)

def dice_coef_loss3(y_true, y_pred):
    return -K.log(dice_coef(y_true, y_pred))

def get_unet():
    inputs = Input((1, img_rows, img_cols))
    conv1 = Convolution2D(32, 3, 3, activation='relu', border_mode='same')(inputs)
    conv1 = Dropout(0.2)(conv1)
    conv1 = Convolution2D(32, 3, 3, activation='relu', border_mode='same')(conv1)
    pool1 = MaxPooling2D(pool_size=(2, 2))(conv1)
    pool1 = BatchNormalization()(pool1)

    conv2 = Convolution2D(64, 3, 3, activation='relu', border_mode='same')(pool1)
    conv2 = Dropout(0.2)(conv2)
    conv2 = Convolution2D(64, 3, 3, activation='relu', border_mode='same')(conv2)
    pool2 = MaxPooling2D(pool_size=(2, 2))(conv2)
    pool2 = BatchNormalization()(pool2)

    conv3 = Convolution2D(128, 3, 3, activation='relu', border_mode='same')(pool2)
    conv3 = Dropout(0.2)(conv3)
    conv3 = Convolution2D(128, 3, 3, activation='relu', border_mode='same')(conv3)
    pool3 = MaxPooling2D(pool_size=(2, 2))(conv3)
    pool3 = BatchNormalization()(pool3)

    conv4 = Convolution2D(256, 3, 3, activation='relu', border_mode='same')(pool3)
    conv4 = Dropout(0.2)(conv4)
    conv4 = Convolution2D(256, 3, 3, activation='relu', border_mode='same')(conv4)
    pool4 = MaxPooling2D(pool_size=(2, 2))(conv4)
    pool4 = BatchNormalization()(pool4)

    conv5 = Convolution2D(512, 3, 3, activation='relu', border_mode='same')(pool4)
    conv5 = Dropout(0.2)(conv5)
    conv5 = Convolution2D(512, 3, 3, activation='relu', border_mode='same')(conv5)

    up6 = merge([UpSampling2D(size=(2, 2))(conv5), conv4], mode='concat', concat_axis=1)
    conv6 = Convolution2D(256, 3, 3, activation='relu', border_mode='same')(up6)
    conv6 = Dropout(0.2)(conv6)
    conv6 = Convolution2D(256, 3, 3, activation='relu', border_mode='same')(conv6)
    conv6 = BatchNormalization()(conv6)

    up7 = merge([UpSampling2D(size=(2, 2))(conv6), conv3], mode='concat', concat_axis=1)
    conv7 = Convolution2D(128, 3, 3, activation='relu', border_mode='same')(up7)
    conv7 = Dropout(0.2)(conv7)
    conv7 = Convolution2D(128, 3, 3, activation='relu', border_mode='same')(conv7)
    conv7 = BatchNormalization()(conv7)

    up8 = merge([UpSampling2D(size=(2, 2))(conv7), conv2], mode='concat', concat_axis=1)
    conv8 = Convolution2D(64, 3, 3, activation='relu', border_mode='same')(up8)
    conv8 = Dropout(0.2)(conv8)
    conv8 = Convolution2D(64, 3, 3, activation='relu', border_mode='same')(conv8)
    conv8 = BatchNormalization()(conv8)

    up9 = merge([UpSampling2D(size=(2, 2))(conv8), conv1], mode='concat', concat_axis=1)
    conv9 = Convolution2D(32, 3, 3, activation='relu', border_mode='same')(up9)
    conv9 = Dropout(0.2)(conv9)
    conv9 = Convolution2D(32, 3, 3, activation='relu', border_mode='same')(conv9)
    conv9 = BatchNormalization()(conv9)

    conv10 = Convolution2D(1, 1, 1, activation='sigmoid')(conv9)
    model = Model(input=inputs, output=conv10)

    model.compile(optimizer=Adam(lr=1.0e-4), loss=dice_coef_loss, metrics=[dice_coef])

    return model


def train_and_predict(use_existing):
    print('-' * 30)
    print('Loading and preprocessing train data...')
    print('-' * 30)
    imgs_train = np.load(os.path.join(output_path, "train/trainImages.npy")).astype(np.float32)
    imgs_mask_train = np.load(os.path.join(output_path, "train/trainMasks.npy")).astype(np.float32)

    imgs_val = np.load(os.path.join(output_path, "val/valImages.npy")).astype(np.float32)
    imgs_mask_val = np.load(os.path.join(output_path, "val/valMasks.npy")).astype(np.float32)

    imgs_mask_train /=255

    imgs_train/=255
    mean = np.mean(imgs_train)
    imgs_train -= mean

    imgs_val/=255
    mean_val = np.mean(imgs_val)
    imgs_val -= mean_val

    # mean = np.mean(imgs_mask_train)  # mean for data centering
    # std = np.std(imgs_mask_train)  # std for data normalization
    #
    # imgs_mask_train -= mean  # images should already be standardized, but just in case
    # imgs_mask_train /= 254
    print('-' * 30)
    print('Creating and compiling model...')
    print('-' * 30)
    model = get_unet()
    # Saving weights to unet.hdf5 at checkpoints
    model_checkpoint = ModelCheckpoint(os.path.join(output_path, 'preds/') + 'unet.hdf5', monitor='loss', save_best_only=True)
    #
    # Should we load existing weights?
    # Set argument for call to train_and_predict to true at end of script
    if use_existing:
        model.load_weights(os.path.join(output_path, 'preds/') + 'unet.hdf5')

    #
    # The final results for this tutorial were produced using a multi-GPU
    # machine using TitanX's.
    # For a home GPU computation benchmark, on my home set up with a GTX970
    # I was able to run 20 epochs with a training set size of 320 and
    # batch size of 2 in about an hour. I started getting reseasonable masks
    # after about 3 hours of training.
    #
    print('-' * 30)
    print('Fitting model...')
    print('-' * 30)
    model.fit(imgs_train, imgs_mask_train, batch_size=2, nb_epoch=30, verbose=1, shuffle=True, validation_split=0.2,
              callbacks=[model_checkpoint])

    # loading best weights from training session
    print('-' * 30)
    print('Loading saved weights...')
    print('-' * 30)
    model.load_weights(os.path.join(output_path, 'preds/') + 'unet.hdf5')

    print('-' * 30)
    print('Predicting masks on test data...')
    print('-' * 30)
    num_test = len(imgs_val)
    print("num_test: %d" % num_test)
    imgs_mask_test = np.ndarray([num_test, 1, 512, 512], dtype=np.float32)
    for i in range(num_test):
        imgs_mask_test[i] = model.predict([imgs_val[i:i + 1]], verbose=0)[0]
    np.save(os.path.join(output_path + "preds/", 'masksTestPredicted.npy'), imgs_mask_test)

    for i in range(num_test):
        # mean+=dice_coef_np(imgs_mask_test_true[i,0], imgs_mask_test[i,0])
        # np.save(os.path.join(working_path + "predictions/", 'imgs_mask_test_true_%04d.npy' % (i)), imgs_mask_test_true[i,0])
        np.save(os.path.join(output_path + "preds/", 'imgs_mask_test_%04d.npy' % (i)), imgs_mask_test[i,0])
        cv2.imwrite(os.path.join(output_path + "ROI/preds/", 'imgs_mask_test_%04d.jpg' % (i)), imgs_mask_test[i,0])
    K.clear_session()

if __name__ == '__main__':
    train_and_predict(False)
